<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ChevronDown, ChevronUp, Scale } from 'lucide-vue-next'
import { api } from '../api'
import PaginationControls from '../components/PaginationControls.vue'
import RacePenaltyListModal from '../components/RacePenaltyListModal.vue'
import UserAvatar from '../components/UserAvatar.vue'
import { countryLabel, gameLabel, statusLabel } from '../i18nLabels'
import { filterPilots, formatRating, sortPilots, teamShortName } from '../pilotDisplay'
import { state } from '../store'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const race = ref(null)
const penalties = ref([])
const appeals = ref([])
const car = ref('')
const error = ref('')
const actionPending = ref(false)
const accQualificationFile = ref(null)
const accRaceFile = ref(null)
const manualRows = ref([])
const participantsExpanded = ref(false)
const penaltiesOpen = ref(false)
const resultsTab = ref('race')
const participantSearch = ref('')
const participantSort = ref('rating_desc')
const participantPage = ref(1)
const participantPageSize = 12

const participants = computed(() => race.value?.registered_pilots || [])
const visibleParticipants = computed(() => sortPilots(filterPilots(participants.value, participantSearch.value), participantSort.value))
const participantTotalPages = computed(() => Math.max(1, Math.ceil(visibleParticipants.value.length / participantPageSize)))
const pagedParticipants = computed(() => visibleParticipants.value.slice((participantPage.value - 1) * participantPageSize, participantPage.value * participantPageSize))
const registered = computed(() => participants.value.some((item) => item.user_id === state.user?.id))
const canManageRace = computed(() => ['admin', 'moder'].includes(state.user?.role))
const resultRows = computed(() => {
  if (Array.isArray(race.value?.results)) return race.value.results
  return race.value?.results?.rows || []
})
const raceRowsByPlayer = computed(() => {
  const rows = new Map()
  resultRows.value.forEach((row) => {
    const key = normalizeAccPlayerId(row.player_id)
    if (key) rows.set(key, row)
  })
  return rows
})
const participantsBySteam = computed(() => {
  const rows = new Map()
  participants.value.forEach((item) => {
    const key = normalizeAccPlayerId(item.steam_id)
    if (key) rows.set(key, item)
  })
  return rows
})
const qualificationRows = computed(() => {
  const lines = race.value?.results?.qualification?.raw?.sessionResult?.leaderBoardLines
  if (!Array.isArray(lines)) return []
  const mapped = lines.map((line, index) => {
    const driver = accLineDriver(line)
    const playerId = accPlayerId(driver.playerId || driver.playerID)
    const normalized = normalizeAccPlayerId(playerId)
    const participant = participantsBySteam.value.get(normalized)
    const raceRow = raceRowsByPlayer.value.get(normalized)
    const timing = line.timing || {}
    return {
      position: index + 1,
      user_id: participant?.user_id || raceRow?.user_id || null,
      login: participant?.login || raceRow?.login || null,
      nickname: participant?.nickname || raceRow?.nickname || null,
      driver_name: accDriverName(driver),
      player_id: playerId,
      race_number: line.car?.raceNumber ?? raceRow?.race_number ?? null,
      car_model: line.car?.carModel ?? raceRow?.car_model ?? null,
      lap_count: timing.lapCount ?? null,
      best_lap_ms: timing.bestLap,
      source: 'qualification'
    }
  })
  const leaderLap = mapped.find((row) => Number.isFinite(Number(row.best_lap_ms)))?.best_lap_ms
  return mapped.map((row) => ({
    ...row,
    gap_ms: Number.isFinite(Number(row.best_lap_ms)) && Number.isFinite(Number(leaderLap)) ? Number(row.best_lap_ms) - Number(leaderLap) : null
  }))
})
const activeResultRows = computed(() => (resultsTab.value === 'qualification' ? qualificationRows.value : resultRows.value))
const resultTabItems = computed(() => [
  { id: 'race', label: t('raceDetails.raceResultsTab'), count: resultRows.value.length },
  ...(qualificationRows.value.length ? [{ id: 'qualification', label: t('raceDetails.qualificationResultsTab'), count: qualificationRows.value.length }] : [])
])

function normalizeAccPlayerId(value) {
  const raw = String(value || '').trim()
  return raw.toUpperCase().startsWith('S') ? raw.slice(1) : raw
}

function accPlayerId(value) {
  const raw = String(value || '').trim()
  if (!raw) return ''
  return raw.toUpperCase().startsWith('S') ? raw : `S${raw}`
}

function accLineDriver(line) {
  if (line.currentDriver && Object.keys(line.currentDriver).length) return line.currentDriver
  return Array.isArray(line.car?.drivers) ? line.car.drivers[0] || {} : {}
}

function accDriverName(driver) {
  const name = [driver.firstName, driver.lastName].filter(Boolean).join(' ').trim()
  return name || driver.shortName || ''
}

function formatDate(value) {
  return new Date(value).toLocaleString(state.locale, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatDuration(ms) {
  if (!Number.isFinite(Number(ms))) return '-'
  const totalMs = Math.max(0, Math.round(Number(ms)))
  const minutes = Math.floor(totalMs / 60000)
  const seconds = Math.floor((totalMs % 60000) / 1000)
  const millis = totalMs % 1000
  return `${minutes}:${String(seconds).padStart(2, '0')}.${String(millis).padStart(3, '0')}`
}

function parseDuration(value, required = true) {
  const raw = String(value || '').trim()
  if (!raw) {
    if (required) throw new Error(t('raceDetails.invalidTime'))
    return null
  }
  const parts = raw.split(':').map((part) => Number(part.replace(',', '.')))
  if (parts.some((part) => !Number.isFinite(part))) throw new Error(t('raceDetails.invalidTime'))
  let seconds = 0
  if (parts.length === 1) seconds = parts[0]
  else if (parts.length === 2) seconds = parts[0] * 60 + parts[1]
  else if (parts.length === 3) seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
  else throw new Error(t('raceDetails.invalidTime'))
  return Math.round(seconds * 1000)
}

function participantName(item) {
  const fullName = [item.first_name, item.last_name].filter(Boolean).join(' ')
  return fullName || item.nickname || item.login || `${t('roles.pilot')} ${item.user_id}`
}

function participantSubtitle(item) {
  const number = item.pilot_number ? `#${item.pilot_number}` : `ID ${item.user_id}`
  return item.nickname ? `${number} - ${item.nickname}` : number
}

function participantById(userId) {
  return participants.value.find((item) => item.user_id === userId)
}

function resultPilotName(row) {
  const participant = participantById(row.user_id)
  if (participant) return participantName(participant)
  return row.driver_name || row.nickname || row.login || `${t('roles.pilot')} ${row.user_id || ''}`.trim()
}

function resultPilotSubtitle(row) {
  const participant = participantById(row.user_id)
  if (participant) return participantSubtitle(participant)
  if (row.race_number) return `#${row.race_number}`
  return row.player_id || '-'
}

function resultPilotColor(row) {
  return participantById(row.user_id)?.avatar_color || '#2563eb'
}

function resultPilotTeam(row) {
  return teamShortName(participantById(row.user_id)?.team_name)
}

function resultPilotRating(row) {
  return formatRating(row.rating_new ?? participantById(row.user_id)?.rating)
}

function resultPenalty(row) {
  const penalty = Number(row.time_penalty_ms || 0)
  return penalty > 0 ? `+${formatDuration(penalty)}` : '-'
}

function resultSrPenalty(row) {
  const penalty = Number(row.sr_penalty || 0)
  return penalty > 0 ? `-${penalty.toFixed(1)} SR` : '-'
}

function resultRatingDelta(row) {
  const delta = Number(row.rating_delta ?? 0)
  if (!Number.isFinite(delta)) return '-'
  const rounded = Math.round(delta)
  return `${rounded > 0 ? '+' : ''}${rounded}`
}

function resultRatingDeltaClass(row) {
  const delta = Number(row.rating_delta ?? 0)
  return {
    positive: delta > 0,
    negative: delta < 0
  }
}

function resultGap(row) {
  if (row.gap_ms === 0) return t('raceDetails.leaderGap')
  return Number.isFinite(Number(row.gap_ms)) ? `+${formatDuration(row.gap_ms)}` : '-'
}

function pilotTeamChip(item) {
  return teamShortName(item?.team_name)
}

function fillManualRows() {
  const existingRows = new Map(resultRows.value.filter((item) => item.user_id).map((item) => [item.user_id, item]))
  manualRows.value = participants.value.map((item) => {
    const existing = existingRows.get(item.user_id) || {}
    return {
      user_id: item.user_id,
      label: participantName(item),
      finish_time: existing.finish_ms ? formatDuration(existing.finish_ms) : '',
      lap_count: existing.lap_count || 0,
      best_lap_time: existing.best_lap_ms ? formatDuration(existing.best_lap_ms) : ''
    }
  })
}

async function load() {
  try {
    race.value = await api(`/races/${route.params.id}`)
    if (state.user) {
      penalties.value = await api(`/penalties?race_id=${route.params.id}`)
      appeals.value = await api('/appeals')
    }
    car.value = race.value.allowed_cars?.[0] || ''
    fillManualRows()
  } catch (err) {
    error.value = err.message
  }
}

async function register() {
  race.value = await api(`/races/${race.value.id}/register`, { method: 'POST', body: { car_model: car.value } })
}

async function unregister() {
  race.value = await api(`/races/${race.value.id}/register`, { method: 'DELETE' })
}

async function closeRace() {
  if (!race.value || !window.confirm(t('raceDetails.confirmClose'))) return
  error.value = ''
  actionPending.value = true
  try {
    race.value = await api(`/races/${race.value.id}/close`, { method: 'POST' })
  } catch (err) {
    error.value = err.message
  } finally {
    actionPending.value = false
  }
}

async function readJsonFile(file) {
  if (!file) throw new Error(t('raceDetails.resultsFileRequired'))
  const buffer = await file.arrayBuffer()
  const bytes = new Uint8Array(buffer)
  const isUtf16 = (bytes[0] === 0xff && bytes[1] === 0xfe) || bytes.slice(0, 40).some((byte, index) => index % 2 === 1 && byte === 0)
  const decoder = new TextDecoder(isUtf16 ? 'utf-16le' : 'utf-8')
  return JSON.parse(decoder.decode(buffer).replace(/^\uFEFF/, ''))
}

function setAccFile(kind, event) {
  const file = event.target.files?.[0] || null
  if (kind === 'qualification') accQualificationFile.value = file
  else accRaceFile.value = file
}

async function uploadAccResults() {
  if (!race.value) return
  error.value = ''
  actionPending.value = true
  try {
    const qualification_results = race.value.has_qualification ? await readJsonFile(accQualificationFile.value) : null
    const race_results = await readJsonFile(accRaceFile.value)
    race.value = await api(`/races/${race.value.id}/results/acc`, {
      method: 'POST',
      body: { qualification_results, race_results }
    })
    fillManualRows()
  } catch (err) {
    error.value = err.message
  } finally {
    actionPending.value = false
  }
}

async function uploadManualResults() {
  if (!race.value) return
  error.value = ''
  actionPending.value = true
  try {
    const rows = manualRows.value
      .filter((row) => String(row.finish_time || '').trim())
      .map((row) => ({
        user_id: row.user_id,
        finish_ms: parseDuration(row.finish_time, true),
        lap_count: Number(row.lap_count || 0),
        best_lap_ms: parseDuration(row.best_lap_time, false)
      }))
    race.value = await api(`/races/${race.value.id}/results/manual`, { method: 'POST', body: { rows } })
    fillManualRows()
  } catch (err) {
    error.value = err.message
  } finally {
    actionPending.value = false
  }
}

async function deleteRace() {
  if (!race.value || !window.confirm(t('raceDetails.confirmDelete'))) return
  error.value = ''
  actionPending.value = true
  try {
    await api(`/races/${race.value.id}`, { method: 'DELETE' })
    router.push('/calendar')
  } catch (err) {
    error.value = err.message
    actionPending.value = false
  }
}

async function createAppeal(penalty, form) {
  await api('/appeals', { method: 'POST', body: { ...form, penalty_id: penalty.id, race_id: race.value.id } })
  await load()
}

onMounted(load)
watch([participantSearch, participantSort], () => {
  participantPage.value = 1
})
watch(visibleParticipants, () => {
  if (participantPage.value > participantTotalPages.value) {
    participantPage.value = participantTotalPages.value
  }
})
</script>

<template>
  <section class="section race-details-page">
    <p v-if="error" class="error">{{ error }}</p>

    <template v-if="race">
      <section class="card race-details-hero">
        <div class="section-header">
          <div class="race-details-title">
            <h1>{{ race.name }}</h1>
            <p class="muted">{{ gameLabel(t, race.game) }} - {{ race.track }} - {{ race.car_class }}</p>
          </div>
          <div class="toolbar race-details-actions">
            <button class="button primary" type="button" @click="penaltiesOpen = true">
              <Scale :size="16" />
              {{ t('raceDetails.openPenalties') }}
              <span class="button-count">{{ penalties.length }}</span>
            </button>
            <template v-if="canManageRace">
              <RouterLink class="button" :to="`/races/${race.id}/edit`">{{ t('common.edit') }}</RouterLink>
              <button v-if="race.status !== 'finished' && race.results" class="button primary" type="button" :disabled="actionPending" @click="closeRace">{{ t('raceDetails.closeRace') }}</button>
              <button class="button danger" type="button" :disabled="actionPending" @click="deleteRace">{{ t('common.delete') }}</button>
            </template>
          </div>
        </div>

        <p>{{ race.description }}</p>
        <div class="race-details-meta">
          <span class="status-badge race-status-badge" :class="`race-status-${race.status}`">{{ statusLabel(t, race.status) }}</span>
          <span>{{ formatDate(race.datetime_start) }}</span>
          <span>{{ formatDate(race.datetime_end) }}</span>
          <span>{{ participants.length }} / {{ race.max_pilots }}</span>
          <span>{{ race.has_qualification ? t('raceDetails.withQualification') : t('raceDetails.withoutQualification') }}</span>
        </div>
        <p>{{ t('fields.server') }}: <a :href="race.server_link">{{ race.server_link }}</a></p>
        <p>{{ t('fields.mods') }}: {{ race.mods_pack?.join(', ') || t('common.none') }}</p>
      </section>

      <section v-if="race.status === 'registration_open' && state.user" class="card race-registration-panel">
        <div v-if="registered" class="section-header">
          <strong>{{ t('raceDetails.alreadyRegistered') }}</strong>
          <button class="button danger" @click="unregister">{{ t('common.unregister') }}</button>
        </div>
        <form v-else class="form" @submit.prevent="register">
          <label class="field">
            <span>{{ t('common.car') }}</span>
            <select v-model="car">
              <option v-for="item in race.allowed_cars" :key="item">{{ item }}</option>
            </select>
          </label>
          <button class="button primary" type="submit">{{ t('common.register') }}</button>
        </form>
      </section>

      <section class="card race-participants-panel">
        <div class="section-header">
          <div>
            <h2>{{ t('raceDetails.participants') }}</h2>
            <p class="muted">{{ t('raceDetails.registeredPilots', { count: participants.length }) }}</p>
          </div>
          <div class="toolbar">
            <span class="pill">{{ visibleParticipants.length }} / {{ participants.length }}</span>
            <button class="icon-button" type="button" :title="participantsExpanded ? t('raceDetails.collapseParticipants') : t('raceDetails.expandParticipants')" :aria-label="participantsExpanded ? t('raceDetails.collapseParticipants') : t('raceDetails.expandParticipants')" @click="participantsExpanded = !participantsExpanded">
              <ChevronUp v-if="participantsExpanded" :size="18" />
              <ChevronDown v-else :size="18" />
            </button>
          </div>
        </div>

        <div v-if="participantsExpanded" class="pilot-inline-controls">
          <input v-model="participantSearch" type="search" :placeholder="t('raceDetails.participantSearch')" />
          <select v-model="participantSort" :aria-label="t('common.sort')">
            <option value="rating_desc">{{ t('sort.ratingDesc') }}</option>
            <option value="rating_asc">{{ t('sort.ratingAsc') }}</option>
            <option value="sr_desc">{{ t('sort.srDesc') }}</option>
            <option value="sr_asc">{{ t('sort.srAsc') }}</option>
            <option value="alpha_asc">{{ t('sort.alphaAsc') }}</option>
            <option value="alpha_desc">{{ t('sort.alphaDesc') }}</option>
          </select>
        </div>

        <div v-if="participantsExpanded && visibleParticipants.length" class="race-participant-list">
          <article v-for="item in pagedParticipants" :key="item.user_id" class="race-participant-row">
            <UserAvatar class="pilot-avatar-slot" :color="item.avatar_color" :label="participantName(item)" />
            <div class="race-participant-main">
              <strong>{{ participantName(item) }}</strong>
              <span>{{ participantSubtitle(item) }} · RER {{ formatRating(item.rating) }} · {{ pilotTeamChip(item) }}</span>
            </div>
            <div class="race-participant-stat">
              <span>SR</span>
              <strong>{{ item.sr ?? '-' }}</strong>
            </div>
            <div class="race-participant-stat">
              <span>RER</span>
              <strong>{{ formatRating(item.rating) }}</strong>
            </div>
            <div class="race-participant-country">
              <span>{{ t('fields.country') }}</span>
              <strong>{{ countryLabel(t, item.country) }}</strong>
            </div>
            <div class="race-participant-car">
              <span>{{ t('common.car') }}</span>
              <strong>{{ item.car_model }}</strong>
            </div>
          </article>
        </div>

        <PaginationControls v-if="participantsExpanded && visibleParticipants.length" v-model:page="participantPage" :page-size="participantPageSize" :total-items="visibleParticipants.length" />

        <div v-if="participantsExpanded && !visibleParticipants.length" class="empty-row">{{ participants.length ? t('common.noMatches') : t('raceDetails.noRegisteredPilots') }}</div>
      </section>

      <section class="card race-results-panel">
        <div class="section-header">
          <div>
            <h2>{{ t('raceDetails.results') }}</h2>
            <p class="muted">{{ race.game === 'ACC' ? t('raceDetails.accResultsHint') : t('raceDetails.manualResultsHint') }}</p>
          </div>
          <span class="pill">{{ resultRows.length }}</span>
        </div>

        <form v-if="canManageRace && race.status !== 'finished' && race.game === 'ACC'" class="form race-results-upload" @submit.prevent="uploadAccResults">
          <div class="form-row">
            <label v-if="race.has_qualification" class="field">
              <span>{{ t('raceDetails.qualificationResultsJson') }}</span>
              <input type="file" accept=".json,application/json" required @change="setAccFile('qualification', $event)" />
            </label>
            <label class="field">
              <span>{{ t('raceDetails.raceResultsJson') }}</span>
              <input type="file" accept=".json,application/json" required @change="setAccFile('race', $event)" />
            </label>
          </div>
          <button class="button primary" type="submit" :disabled="actionPending">{{ t('raceDetails.uploadAccResults') }}</button>
        </form>

        <form v-else-if="canManageRace && race.status !== 'finished'" class="form race-results-upload" @submit.prevent="uploadManualResults">
          <div class="manual-results-table">
            <div class="manual-results-head">
              <span>{{ t('roles.pilot') }}</span>
              <span>{{ t('raceDetails.resultTime') }}</span>
              <span>{{ t('raceDetails.laps') }}</span>
              <span>{{ t('raceDetails.bestLap') }}</span>
            </div>
            <div v-for="row in manualRows" :key="row.user_id" class="manual-results-row">
              <strong>{{ row.label }}</strong>
              <input v-model="row.finish_time" required placeholder="45:12.345" />
              <input v-model.number="row.lap_count" type="number" min="0" />
              <input v-model="row.best_lap_time" placeholder="1:48.250" />
            </div>
          </div>
          <button class="button primary" type="submit" :disabled="actionPending || !manualRows.length">{{ t('raceDetails.saveManualResults') }}</button>
        </form>

        <div v-if="resultRows.length || qualificationRows.length" class="race-results-shell">
          <div class="race-results-tabs">
            <button v-for="tab in resultTabItems" :key="tab.id" class="tab-button" type="button" :class="{ active: resultsTab === tab.id }" @click="resultsTab = tab.id">
              <span>{{ tab.label }}</span>
              <strong>{{ tab.count }}</strong>
            </button>
          </div>

          <div class="race-results-podium">
            <article v-for="row in activeResultRows.slice(0, 3)" :key="`podium-${resultsTab}-${row.user_id || row.player_id || row.position}`" class="result-podium-card">
              <span class="result-position-badge" :class="{ 'is-top': Number(row.position) <= 3 }">{{ row.position || '-' }}</span>
              <div>
                <strong>{{ resultPilotName(row) }}</strong>
                <span>{{ resultPilotSubtitle(row) }}</span>
              </div>
              <strong class="result-podium-time">{{ resultsTab === 'qualification' ? formatDuration(row.best_lap_ms) : formatDuration(row.adjusted_finish_ms ?? row.finish_ms) }}</strong>
            </article>
          </div>

          <div v-if="activeResultRows.length" class="race-results-table-wrap">
            <table class="race-results-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>{{ t('roles.pilot') }}</th>
                  <th v-if="resultsTab === 'race'">{{ t('raceDetails.laps') }}</th>
                  <th v-else>{{ t('common.car') }}</th>
                  <th>{{ t('raceDetails.bestLap') }}</th>
                  <th v-if="resultsTab === 'race'">{{ t('raceDetails.resultTime') }}</th>
                  <th v-if="resultsTab === 'race'">{{ t('raceDetails.timePenalty') }}</th>
                  <th v-if="resultsTab === 'race'">{{ t('raceDetails.srPenalty') }}</th>
                  <th v-if="resultsTab === 'race'">{{ t('raceDetails.adjustedTime') }}</th>
                  <th v-if="resultsTab === 'race'">{{ t('raceDetails.ratingDelta') }}</th>
                  <th>{{ t('raceDetails.gap') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in activeResultRows" :key="`${resultsTab}-${row.user_id || row.player_id || row.raw_position}-${row.position}`">
                  <td><span class="result-position-badge" :class="{ 'is-top': Number(row.position) <= 3 }">{{ row.position || '-' }}</span></td>
                  <td>
                    <div class="result-driver-cell">
                      <UserAvatar mini :color="resultPilotColor(row)" :label="resultPilotName(row)" />
                      <div>
                        <strong>{{ resultPilotName(row) }}</strong>
                        <span>{{ resultPilotSubtitle(row) }} · RER {{ resultPilotRating(row) }} · {{ resultPilotTeam(row) }}</span>
                      </div>
                    </div>
                  </td>
                  <td v-if="resultsTab === 'race'">{{ row.lap_count ?? '-' }}</td>
                  <td v-else>{{ row.race_number ? `#${row.race_number}` : '-' }}</td>
                  <td>{{ formatDuration(row.best_lap_ms) }}</td>
                  <td v-if="resultsTab === 'race'">{{ formatDuration(row.finish_ms) }}</td>
                  <td v-if="resultsTab === 'race'">{{ resultPenalty(row) }}</td>
                  <td v-if="resultsTab === 'race'">{{ resultSrPenalty(row) }}</td>
                  <td v-if="resultsTab === 'race'">{{ formatDuration(row.adjusted_finish_ms ?? row.finish_ms) }}</td>
                  <td v-if="resultsTab === 'race'"><span class="rating-delta" :class="resultRatingDeltaClass(row)">{{ resultRatingDelta(row) }}</span></td>
                  <td>{{ resultGap(row) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div v-else-if="race.status === 'finished'" class="empty-row">{{ t('raceDetails.noResults') }}</div>
      </section>

      <RacePenaltyListModal
        :open="penaltiesOpen"
        :penalties="penalties"
        :appeals="appeals"
        :participants="participants"
        @close="penaltiesOpen = false"
        @create-appeal="createAppeal"
      />
    </template>
  </section>
</template>
