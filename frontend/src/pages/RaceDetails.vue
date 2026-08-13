<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ChevronDown, ChevronUp, Film, Heart, Scale, Trash2, Upload } from 'lucide-vue-next'
import { api } from '../api'
import PaginationControls from '../components/PaginationControls.vue'
import RacePenaltyListModal from '../components/RacePenaltyListModal.vue'
import UserAvatar from '../components/UserAvatar.vue'
import { countryLabel, gameLabel, isExternalRace, statusLabel } from '../i18nLabels'
import { filterPilots, formatPilotNumber, formatRating, sortPilots, teamHref, teamShortName } from '../pilotDisplay'
import { state } from '../store'
import { formatDateTime } from '../timezone'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const race = ref(null)
const penalties = ref([])
const appeals = ref([])
const car = ref('')
const pilotNumber = ref(pilotNumberDraft(state.user?.pilot_number))
const error = ref('')
const actionPending = ref(false)
const accQualificationFile = ref(null)
const accRaceFile = ref(null)
const raceVideoFile = ref(null)
const raceVideoInput = ref(null)
const manualRows = ref([])
const participantsExpanded = ref(false)
const penaltiesOpen = ref(false)
const penaltyCreateOpen = ref(false)
const resultsTab = ref('race')
const participantSearch = ref('')
const participantSort = ref('rating_desc')
const participantPage = ref(1)
const participantPageSize = 12
const fanVote = ref(null)
const fanVoteSelection = ref([])
const fanVoteSaving = ref(false)
const fanVoteVoting = ref(false)
const manualPilotSearch = ref('')
const manualPilotResults = ref([])
const manualPilotLoading = ref(false)

const participants = computed(() => race.value?.registered_pilots || [])
const visibleParticipants = computed(() => sortPilots(filterPilots(participants.value, participantSearch.value), participantSort.value))
const participantTotalPages = computed(() => Math.max(1, Math.ceil(visibleParticipants.value.length / participantPageSize)))
const pagedParticipants = computed(() => visibleParticipants.value.slice((participantPage.value - 1) * participantPageSize, participantPage.value * participantPageSize))
const registered = computed(() => participants.value.some((item) => item.user_id === state.user?.id))
const canManageRace = computed(() => ['admin', 'moder'].includes(state.user?.role))
const canIssuePenalty = computed(() => ['admin', 'moder', 'marshall'].includes(state.user?.role) && ['ongoing', 'finished'].includes(race.value?.status))
const isChampionshipStage = computed(() => Boolean(race.value?.championship_id))
const isLmuRace = computed(() => race.value?.game === 'LMU')
const lmuResultsOpen = computed(() => !isLmuRace.value || race.value?.status === 'finished' || Boolean(race.value?.results) || !race.value?.lmu_results_at || new Date(race.value.lmu_results_at).getTime() <= Date.now())
const usesSimulatorJsonResults = computed(() => race.value?.game === 'ACC')
const canEditManualResults = computed(() => canManageRace.value && !usesSimulatorJsonResults.value && (race.value?.status !== 'finished' || isLmuRace.value))
const canShowRegistrationPanel = computed(() => Boolean(state.user) && (race.value?.status === 'registration_open' || (isChampionshipStage.value && race.value?.status === 'not_started')))
const resultRows = computed(() => {
  if (Array.isArray(race.value?.results)) return race.value.results
  return race.value?.results?.rows || []
})
const resultParticipants = computed(() => {
  const seen = new Set()
  return resultRows.value
    .filter((row) => row.user_id && !seen.has(row.user_id) && seen.add(row.user_id))
    .map((row) => {
      const participant = participants.value.find((item) => item.user_id === row.user_id)
      return {
        user_id: row.user_id,
        login: row.login || participant?.login,
        nickname: row.nickname || participant?.nickname,
        first_name: row.first_name || participant?.first_name || '',
        last_name: row.last_name || participant?.last_name || '',
        pilot_number: row.pilot_number ?? row.race_number ?? participant?.pilot_number,
        avatar_color: row.avatar_color || participant?.avatar_color || '#2563eb',
        avatar_url: row.avatar_url || participant?.avatar_url || '',
        rating: row.rating ?? participant?.rating,
        sr: row.sr ?? participant?.sr,
        car_model: row.car_model || participant?.car_model,
        team_id: row.team_id || participant?.team_id,
        team_name: row.team_name || participant?.team_name,
        team_abbreviation: row.team_abbreviation || participant?.team_abbreviation,
        country: row.country || participant?.country
      }
    })
})
const penaltyParticipants = computed(() => resultParticipants.value.length ? resultParticipants.value : participants.value)
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
      avatar_color: participant?.avatar_color || raceRow?.avatar_color || '#2563eb',
      avatar_url: participant?.avatar_url || raceRow?.avatar_url || '',
      rating: participant?.rating ?? raceRow?.rating,
      sr: participant?.sr ?? raceRow?.sr,
      team_id: participant?.team_id || raceRow?.team_id,
      team_name: participant?.team_name || raceRow?.team_name,
      team_abbreviation: participant?.team_abbreviation || raceRow?.team_abbreviation,
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
const fanVoteOptions = computed(() => fanVote.value?.options || [])
const fanVoteCandidates = computed(() => resultParticipants.value.length ? resultParticipants.value : participants.value)
const fanVoteCanSetup = computed(() => canManageRace.value && race.value?.status === 'finished' && fanVoteCandidates.value.length >= 3)
const fanVoteCanSaveSetup = computed(() => fanVoteCanSetup.value && fanVoteSelection.value.length === 3 && !fanVoteSaving.value)
const fanVoteResultVisible = computed(() => Boolean(fanVote.value?.show_results))

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
  return formatDateTime(value)
}

function formatFanVoteDate(value) {
  return value ? formatDate(value) : '-'
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
  const number = item.pilot_number !== null && item.pilot_number !== undefined ? `#${formatPilotNumber(item.pilot_number)}` : `ID ${item.user_id}`
  return item.nickname ? `${number} - ${item.nickname}` : number
}

function fanVotePilotName(item) {
  const fullName = [item.first_name, item.last_name].filter(Boolean).join(' ')
  return fullName || item.nickname || item.login || `${t('roles.pilot')} ${item.user_id}`
}

function fanVotePilotSubtitle(item) {
  const team = teamShortName(item.team_name, item.team_abbreviation)
  const number = item.pilot_number !== null && item.pilot_number !== undefined ? `#${formatPilotNumber(item.pilot_number)}` : `ID ${item.user_id}`
  return [number, `RER ${formatRating(item.rating)}`, `SR ${item.sr ?? '-'}`, team].filter(Boolean).join(' - ')
}

function pilotNumberDraft(value) {
  const number = Number(value)
  return Number.isInteger(number) && number >= 0 ? formatPilotNumber(number) : ''
}

function parsePilotNumber(value) {
  const raw = String(value ?? '').trim()
  if (!/^\d{3}$/.test(raw)) throw new Error(t('championships.invalidPilotNumber'))
  return Number(raw)
}

function fanVotePercent(option) {
  const value = Number(option.percentage || 0)
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

function isFanVoteCandidate(userId) {
  return fanVoteSelection.value.includes(Number(userId))
}

function toggleFanVoteCandidate(userId) {
  const id = Number(userId)
  if (isFanVoteCandidate(id)) {
    fanVoteSelection.value = fanVoteSelection.value.filter((item) => item !== id)
  } else if (fanVoteSelection.value.length < 3) {
    fanVoteSelection.value = [...fanVoteSelection.value, id]
  }
}

function syncFanVoteSelection() {
  if (fanVote.value?.options?.length) {
    fanVoteSelection.value = fanVote.value.options.map((option) => option.user_id).slice(0, 3)
    return
  }
  const participantIds = new Set(fanVoteCandidates.value.map((item) => item.user_id))
  fanVoteSelection.value = fanVoteSelection.value.filter((item) => participantIds.has(item)).slice(0, 3)
}

function participantById(userId) {
  return fanVoteCandidates.value.find((item) => item.user_id === userId)
}

function resultPilotName(row) {
  const participant = participantById(row.user_id)
  if (participant) return participantName(participant)
  return row.driver_name || row.nickname || row.login || `${t('roles.pilot')} ${row.user_id || ''}`.trim()
}

function resultPilotSubtitle(row) {
  const participant = participantById(row.user_id)
  if (participant) return participantSubtitle(participant)
  const number = row.race_number ?? row.pilot_number
  if (number !== null && number !== undefined) return `#${formatPilotNumber(number)}`
  return row.player_id || '-'
}

function resultPilotColor(row) {
  return participantById(row.user_id)?.avatar_color || row.avatar_color || '#2563eb'
}

function resultPilotAvatar(row) {
  return participantById(row.user_id)?.avatar_url || row.avatar_url || ''
}

function resultPilotTeam(row) {
  const participant = participantById(row.user_id)
  return teamShortName(participant?.team_name || row.team_name, participant?.team_abbreviation || row.team_abbreviation)
}

function resultPilotTeamId(row) {
  return participantById(row.user_id)?.team_id || row.team_id || null
}

function resultPilotRating(row) {
  return formatRating(row.rating_new ?? participantById(row.user_id)?.rating ?? row.rating)
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

function resultPodiumClass(row) {
  const position = Number(row.position)
  return {
    'is-gold': position === 1,
    'is-silver': position === 2,
    'is-bronze': position === 3
  }
}

function resultGap(row) {
  if (row.gap_ms === 0) return t('raceDetails.leaderGap')
  return Number.isFinite(Number(row.gap_ms)) ? `+${formatDuration(row.gap_ms)}` : '-'
}

function pilotTeamChip(item) {
  return teamShortName(item?.team_name, item?.team_abbreviation)
}

function openPenaltyCreator() {
  penaltiesOpen.value = true
  penaltyCreateOpen.value = true
}

function closePenaltiesModal() {
  penaltiesOpen.value = false
  penaltyCreateOpen.value = false
}

function manualRowFromPilot(item, existing = {}) {
  const userId = item.user_id ?? item.id
  const pilot = { ...item, user_id: userId }
  return {
    user_id: userId,
    label: participantName(pilot),
    finish_time: existing.finish_ms ? formatDuration(existing.finish_ms) : '',
    lap_count: existing.lap_count || 0,
    best_lap_time: existing.best_lap_ms ? formatDuration(existing.best_lap_ms) : ''
  }
}

function fillManualRows() {
  const existingRows = new Map(resultRows.value.filter((item) => item.user_id).map((item) => [item.user_id, item]))
  const source = isLmuRace.value ? resultParticipants.value : participants.value
  manualRows.value = source.map((item) => manualRowFromPilot(item, existingRows.get(item.user_id) || {}))
}

async function searchManualPilots() {
  if (!manualPilotSearch.value.trim()) {
    manualPilotResults.value = []
    return
  }
  manualPilotLoading.value = true
  try {
    const params = new URLSearchParams({ search: manualPilotSearch.value, limit: '12' })
    manualPilotResults.value = await api(`/users/pilots?${params.toString()}`)
  } catch (err) {
    error.value = err.message
  } finally {
    manualPilotLoading.value = false
  }
}

function addManualPilot(pilot) {
  const userId = pilot.user_id ?? pilot.id
  if (!userId || manualRows.value.some((row) => row.user_id === userId)) return
  manualRows.value.push(manualRowFromPilot({ ...pilot, user_id: userId }))
}

function removeManualRow(userId) {
  manualRows.value = manualRows.value.filter((row) => row.user_id !== userId)
}

async function load() {
  try {
    const loadedRace = await api(`/races/${route.params.id}`)
    if (isExternalRace(loadedRace) && !['admin', 'moder'].includes(state.user?.role)) {
      window.location.href = loadedRace.server_link
      return
    }
    const loadedFanVote = await api(`/races/${route.params.id}/fan-vote`)
    race.value = loadedRace
    fanVote.value = loadedFanVote
    syncFanVoteSelection()
    if (state.user) {
      penalties.value = await api(`/penalties?race_id=${route.params.id}`)
      appeals.value = await api('/appeals')
    }
    car.value = race.value.allowed_cars?.[0] || ''
    pilotNumber.value = pilotNumberDraft(state.user?.pilot_number)
    fillManualRows()
  } catch (err) {
    error.value = err.message
  }
}

async function refreshFanVote() {
  if (!race.value) return
  fanVote.value = await api(`/races/${race.value.id}/fan-vote`)
  syncFanVoteSelection()
}

async function register() {
  const body = { car_model: car.value || 'TBD' }
  if (!isChampionshipStage.value) {
    body.pilot_number = parsePilotNumber(pilotNumber.value)
  }
  race.value = await api(`/races/${race.value.id}/register`, { method: 'POST', body })
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
    await refreshFanVote()
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
    await refreshFanVote()
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
    await refreshFanVote()
  } catch (err) {
    error.value = err.message
  } finally {
    actionPending.value = false
  }
}

async function setupFanVote() {
  if (!race.value || fanVoteSelection.value.length !== 3) return
  error.value = ''
  fanVoteSaving.value = true
  try {
    fanVote.value = await api(`/races/${race.value.id}/fan-vote`, {
      method: 'PATCH',
      body: { option_user_ids: fanVoteSelection.value }
    })
    syncFanVoteSelection()
  } catch (err) {
    error.value = err.message
  } finally {
    fanVoteSaving.value = false
  }
}

async function castFanVote(targetUserId) {
  if (!race.value || !fanVote.value?.is_open) return
  error.value = ''
  fanVoteVoting.value = true
  try {
    fanVote.value = await api(`/races/${race.value.id}/fan-vote`, {
      method: 'POST',
      body: { target_user_id: targetUserId }
    })
    syncFanVoteSelection()
  } catch (err) {
    error.value = err.message
  } finally {
    fanVoteVoting.value = false
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

function setRaceVideo(event) {
  raceVideoFile.value = event.target.files?.[0] || null
}

async function uploadRaceVideo() {
  if (!race.value || !raceVideoFile.value) return
  error.value = ''
  actionPending.value = true
  try {
    const body = new FormData()
    body.append('file', raceVideoFile.value)
    race.value = await api(`/races/${race.value.id}/video`, { method: 'POST', body })
    raceVideoFile.value = null
    if (raceVideoInput.value) raceVideoInput.value.value = ''
  } catch (err) {
    error.value = err.message
  } finally {
    actionPending.value = false
  }
}

async function deleteRaceVideo() {
  if (!race.value?.video_url || !window.confirm(t('raceDetails.confirmDeleteVideo'))) return
  error.value = ''
  actionPending.value = true
  try {
    race.value = await api(`/races/${race.value.id}/video`, { method: 'DELETE' })
    raceVideoFile.value = null
    if (raceVideoInput.value) raceVideoInput.value.value = ''
  } catch (err) {
    error.value = err.message
  } finally {
    actionPending.value = false
  }
}

async function createAppeal(penalty, form) {
  await api('/appeals', { method: 'POST', body: { ...form, penalty_id: penalty.id, race_id: race.value.id } })
  await load()
}

async function createPenalty(form) {
  if (!race.value) return
  error.value = ''
  actionPending.value = true
  try {
    await api('/penalties', {
      method: 'POST',
      body: {
        ...form,
        race_id: race.value.id,
        penalty_type: 'combined',
        penalty_value: form.time_penalty_ms
      }
    })
    penaltyCreateOpen.value = false
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    actionPending.value = false
  }
}

onMounted(load)
watch([participantSearch, participantSort], () => {
  participantPage.value = 1
})
watch(manualPilotSearch, () => {
  if (manualPilotSearch.value.trim().length >= 1) searchManualPilots()
  else manualPilotResults.value = []
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
            <button v-if="canIssuePenalty" class="button" type="button" @click="openPenaltyCreator">
              {{ t('raceDetails.issuePenalty') }}
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
          <span v-if="!isLmuRace">{{ participants.length }} / {{ race.max_pilots }}</span>
          <span>{{ race.has_qualification ? t('raceDetails.withQualification') : t('raceDetails.withoutQualification') }}</span>
        </div>
        <p>{{ t('fields.server') }}: <a :href="race.server_link">{{ race.server_link }}</a></p>
        <p>{{ t('fields.mods') }}: {{ race.mods_pack?.join(', ') || t('common.none') }}</p>
      </section>

      <section v-if="canShowRegistrationPanel" class="card race-registration-panel">
        <div v-if="registered" class="section-header">
          <strong>{{ isChampionshipStage ? t('raceDetails.championshipStageRegistered') : t('raceDetails.alreadyRegistered') }}</strong>
          <button class="button danger" @click="unregister">{{ t('common.unregister') }}</button>
        </div>
        <form v-else class="form" @submit.prevent="register">
          <label class="field">
            <span>{{ t('common.car') }}</span>
            <select v-model="car">
              <option v-if="!race.allowed_cars?.length" value="">TBD</option>
              <option v-for="item in race.allowed_cars" :key="item">{{ item }}</option>
            </select>
          </label>
          <label v-if="!isChampionshipStage" class="field">
            <span>{{ t('fields.pilotNumber') }}</span>
            <input v-model="pilotNumber" inputmode="numeric" pattern="[0-9]{3}" minlength="3" maxlength="3" placeholder="000" required />
          </label>
          <p v-if="isChampionshipStage" class="muted">{{ t('raceDetails.championshipStageRegistrationHint') }}</p>
          <button class="button primary" type="submit">{{ isChampionshipStage ? t('raceDetails.championshipStageRegister') : t('common.register') }}</button>
        </form>
      </section>

      <div v-if="race.status === 'finished'" class="race-main-layout">
        <div class="race-main-column">
          <section v-if="race.status === 'finished'" class="card race-video-panel">
            <div class="section-header">
              <div>
                <h2>{{ t('raceDetails.videoTitle') }}</h2>
                <p v-if="canManageRace" class="muted">{{ t('raceDetails.videoHint') }}</p>
              </div>
              <span v-if="canManageRace && race.video_filename" class="pill">
                <Film :size="14" />
                {{ race.video_filename }}
              </span>
            </div>

            <div v-if="race.video_url" class="race-video-frame">
              <video controls preload="metadata" :src="race.video_url"></video>
            </div>
            <div v-else class="empty-row">{{ t('raceDetails.noVideo') }}</div>

            <form v-if="canManageRace" class="form race-video-upload" @submit.prevent="uploadRaceVideo">
              <label class="field">
                <span>{{ t('raceDetails.videoFile') }}</span>
                <input ref="raceVideoInput" type="file" accept="video/mp4,video/webm,video/quicktime,video/x-matroska,.mp4,.webm,.mov,.mkv" @change="setRaceVideo" />
              </label>
              <button class="button primary" type="submit" :disabled="actionPending || !raceVideoFile">
                <Upload :size="16" />
                {{ race.video_url ? t('raceDetails.replaceVideo') : t('raceDetails.uploadVideo') }}
              </button>
              <button v-if="race.video_url" class="button danger" type="button" :disabled="actionPending" @click="deleteRaceVideo">
                <Trash2 :size="16" />
                {{ t('raceDetails.deleteVideo') }}
              </button>
            </form>
          </section>
        </div>

        <aside class="race-vote-column">
          <section class="card race-fan-vote-panel">
            <div class="section-header race-fan-vote-header">
              <div>
                <h2>
                  <Heart :size="18" />
                  {{ t('raceDetails.fanVoteTitle') }}
                </h2>
                <p class="muted">{{ t('raceDetails.fanVoteHint') }}</p>
              </div>
              <span v-if="fanVote?.enabled" class="pill">
                {{ fanVote.is_open ? t('common.open') : t('raceDetails.fanVoteResults') }}
              </span>
            </div>

            <div v-if="race.status !== 'finished'" class="empty-row">{{ t('raceDetails.fanVoteNotReady') }}</div>

            <template v-else>
              <div v-if="fanVote?.enabled" class="fan-vote-status">
                <strong>
                  {{ fanVote.is_open ? t('raceDetails.fanVoteOpenUntil', { date: formatFanVoteDate(fanVote.ends_at) }) : t('raceDetails.fanVoteClosed') }}
                </strong>
                <span>{{ t('raceDetails.fanVoteTotal', { count: fanVote.total_votes || 0 }) }}</span>
              </div>

              <div v-if="fanVoteOptions.length" class="fan-vote-options">
                <article v-for="option in fanVoteOptions" :key="option.user_id" class="fan-vote-option" :class="{ selected: fanVote?.my_vote_user_id === option.user_id }">
                  <UserAvatar mini :src="option.avatar_url" :color="option.avatar_color" :label="fanVotePilotName(option)" />
                  <div class="fan-vote-option-main">
                    <strong>{{ fanVotePilotName(option) }}</strong>
                    <span>{{ fanVotePilotSubtitle(option) }}</span>
                  </div>

                  <div v-if="fanVoteResultVisible" class="fan-vote-result">
                    <div>
                      <strong>{{ t('raceDetails.fanVotePercent', { value: fanVotePercent(option) }) }}</strong>
                      <span>{{ option.votes }}</span>
                    </div>
                    <div class="fan-vote-bar"><span :style="{ width: `${Math.min(100, Number(option.percentage || 0))}%` }"></span></div>
                  </div>

                  <button
                    v-if="fanVote?.is_open"
                    class="button fan-vote-button"
                    type="button"
                    :class="{ primary: fanVote?.my_vote_user_id === option.user_id }"
                    :disabled="fanVoteVoting"
                    @click="castFanVote(option.user_id)"
                  >
                    {{ fanVote?.my_vote_user_id === option.user_id ? t('raceDetails.fanVoteSelected') : t('raceDetails.fanVoteVote') }}
                  </button>
                </article>
              </div>
              <div v-else class="empty-row">{{ t('raceDetails.fanVoteEmpty') }}</div>

              <form v-if="fanVoteCanSetup" class="fan-vote-setup" @submit.prevent="setupFanVote">
                <div class="fan-vote-setup-head">
                  <strong>{{ t('raceDetails.fanVoteSetupHint') }}</strong>
                  <span class="pill">{{ t('raceDetails.fanVoteChooseThree', { count: fanVoteSelection.length }) }}</span>
                </div>

                <div class="fan-vote-candidates">
                  <button
                    v-for="item in fanVoteCandidates"
                    :key="`fan-vote-${item.user_id}`"
                    class="fan-vote-candidate"
                    type="button"
                    :class="{ selected: isFanVoteCandidate(item.user_id) }"
                    :disabled="!isFanVoteCandidate(item.user_id) && fanVoteSelection.length >= 3"
                    @click="toggleFanVoteCandidate(item.user_id)"
                  >
                    <UserAvatar mini :src="item.avatar_url" :color="item.avatar_color" :label="participantName(item)" />
                    <span>{{ participantName(item) }}</span>
                    <small>{{ fanVotePilotSubtitle(item) }}</small>
                  </button>
                </div>

                <button class="button primary" type="submit" :disabled="!fanVoteCanSaveSetup">
                  {{ fanVote?.enabled ? t('raceDetails.fanVoteRestart') : t('raceDetails.fanVoteStart') }}
                </button>
              </form>
            </template>
          </section>
        </aside>
      </div>

      <section v-if="!isLmuRace" class="card race-participants-panel">
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
            <UserAvatar class="pilot-avatar-slot" :src="item.avatar_url" :color="item.avatar_color" :label="participantName(item)" />
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
            <p v-if="!usesSimulatorJsonResults" class="muted">{{ t('raceDetails.manualResultsHint') }}</p>
          </div>
          <span class="pill">{{ resultRows.length }}</span>
        </div>

        <form v-if="canManageRace && race.status !== 'finished' && usesSimulatorJsonResults" class="form race-results-upload" @submit.prevent="uploadAccResults">
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
          <button class="button primary" type="submit" :disabled="actionPending">{{ race.game === 'LMU' ? t('raceDetails.uploadSimulatorResults') : t('raceDetails.uploadAccResults') }}</button>
        </form>

        <form v-else-if="canEditManualResults" class="form race-results-upload" @submit.prevent="uploadManualResults">
          <div v-if="isLmuRace" class="pilot-inline-controls">
            <input v-model="manualPilotSearch" type="search" :placeholder="t('championships.pilotSearchPlaceholder')" />
            <span class="pill">{{ manualPilotLoading ? t('common.loading') : manualPilotResults.length }}</span>
          </div>
          <div v-if="isLmuRace && manualPilotResults.length" class="fan-vote-candidates manual-pilot-results">
            <button
              v-for="pilot in manualPilotResults"
              :key="`manual-pilot-${pilot.id}`"
              class="fan-vote-candidate"
              type="button"
              :disabled="manualRows.some((row) => row.user_id === pilot.id)"
              @click="addManualPilot(pilot)"
            >
              <UserAvatar mini :src="pilot.avatar_url" :color="pilot.avatar_color" :label="participantName({ ...pilot, user_id: pilot.id })" />
              <span>{{ participantName({ ...pilot, user_id: pilot.id }) }}</span>
              <small>#{{ formatPilotNumber(pilot.pilot_number) }} - RER {{ formatRating(pilot.rating) }}</small>
            </button>
          </div>
          <div class="manual-results-table">
            <div class="manual-results-head" :class="{ 'has-actions': isLmuRace }">
              <span>{{ t('roles.pilot') }}</span>
              <span>{{ t('raceDetails.resultTime') }}</span>
              <span>{{ t('raceDetails.laps') }}</span>
              <span>{{ t('raceDetails.bestLap') }}</span>
              <span v-if="isLmuRace"></span>
            </div>
            <div v-for="row in manualRows" :key="row.user_id" class="manual-results-row" :class="{ 'has-actions': isLmuRace }">
              <strong>{{ row.label }}</strong>
              <input v-model="row.finish_time" required placeholder="45:12.345" />
              <input v-model.number="row.lap_count" type="number" min="0" />
              <input v-model="row.best_lap_time" placeholder="1:48.250" />
              <button v-if="isLmuRace" class="icon-button danger" type="button" :title="t('common.delete')" @click="removeManualRow(row.user_id)">
                <Trash2 :size="16" />
              </button>
            </div>
          </div>
          <button class="button primary" type="submit" :disabled="actionPending || !manualRows.length">{{ t('raceDetails.saveManualResults') }}</button>
        </form>

        <div v-if="resultRows.length || qualificationRows.length" class="race-results-shell">
          <div v-if="resultTabItems.length > 1 && !isLmuRace" class="race-results-tabs">
            <button v-for="tab in resultTabItems" :key="tab.id" class="tab-button" type="button" :class="{ active: resultsTab === tab.id }" @click="resultsTab = tab.id">
              <span>{{ tab.label }}</span>
              <strong>{{ tab.count }}</strong>
            </button>
          </div>

          <div class="race-results-podium">
            <article v-for="row in activeResultRows.slice(0, 3)" :key="`podium-${resultsTab}-${row.user_id || row.player_id || row.position}`" class="result-podium-card" :class="resultPodiumClass(row)">
              <span class="result-position-badge" :class="resultPodiumClass(row)">{{ row.position || '-' }}</span>
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
                <tr v-for="row in activeResultRows" :key="`${resultsTab}-${row.user_id || row.player_id || row.raw_position}-${row.position}`" :class="resultPodiumClass(row)">
                  <td><span class="result-position-badge" :class="resultPodiumClass(row)">{{ row.position || '-' }}</span></td>
                  <td>
                    <div class="result-driver-cell">
                      <UserAvatar mini :src="resultPilotAvatar(row)" :color="resultPilotColor(row)" :label="resultPilotName(row)" />
                      <div>
                        <strong>{{ resultPilotName(row) }}</strong>
                        <span class="result-driver-meta">
                          <span>{{ resultPilotSubtitle(row) }}</span>
                          <span>RER {{ resultPilotRating(row) }}</span>
                          <RouterLink v-if="resultPilotTeamId(row)" class="team-mini-chip team-link-chip" :to="teamHref(resultPilotTeamId(row))">
                            {{ resultPilotTeam(row) }}
                          </RouterLink>
                          <span v-else class="team-mini-chip">{{ resultPilotTeam(row) }}</span>
                        </span>
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
        :participants="penaltyParticipants"
        :can-create="canIssuePenalty"
        v-model:create-open="penaltyCreateOpen"
        :busy="actionPending"
        @close="closePenaltiesModal"
        @create-penalty="createPenalty"
        @create-appeal="createAppeal"
      />
    </template>
  </section>
</template>
