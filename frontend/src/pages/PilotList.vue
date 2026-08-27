<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ImagePlus, MapPinned, Search, SlidersHorizontal, Trash2 } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import LicenseBadge from '../components/LicenseBadge.vue'
import PaginationControls from '../components/PaginationControls.vue'
import UserAvatar from '../components/UserAvatar.vue'
import { countryLabel, gameLabel, gameOptions } from '../i18nLabels'
import { formatPilotNumber, formatRating, pilotName, ratingForGame, ratingRaceCountForGame, teamHref, teamShortName } from '../pilotDisplay'
import { state } from '../store'

const { t } = useI18n()
const route = useRoute()
const activeTab = ref('pilots')
const pilots = ref([])
const search = ref('')
const sort = ref('rating_desc')
const ratingGame = ref('ACC')
const error = ref('')
const page = ref(1)
const pageSize = 20
const hasNextPage = computed(() => pilots.value.length === pageSize)
const raceAssets = ref({ tracks: [], classes: [], games: {} })
const trackGame = ref('ACC')
const selectedTrack = ref('')
const trackSearch = ref('')
const trackRacesByGame = ref({})
const trackLoading = ref(false)
const trackError = ref('')
const trackImageInput = ref(null)
const trackImageUploading = ref(false)
const trackGameOptions = computed(() => gameOptions(t))
const canManageTrackImages = computed(() => state.user?.role === 'admin')

async function load() {
  try {
    const params = new URLSearchParams()
    if (search.value.trim()) params.set('search', search.value.trim())
    params.set('sort', sort.value)
    params.set('rating_game', ratingGame.value)
    params.set('limit', String(pageSize))
    params.set('offset', String((page.value - 1) * pageSize))
    pilots.value = await api(`/users/pilots?${params.toString()}`)
  } catch (err) {
    error.value = err.message
  }
}

async function loadRaceAssets() {
  try {
    raceAssets.value = await api('/race-assets')
  } catch {
    raceAssets.value = { tracks: [], classes: [], games: {} }
  }
}

async function loadTrackRaces(game) {
  if (trackRacesByGame.value[game]) return
  trackLoading.value = true
  trackError.value = ''
  try {
    const loaded = []
    for (let offset = 0; offset < 1000; offset += 100) {
      const params = new URLSearchParams({
        status_filter: 'finished',
        game_filter: game,
        include_championship: 'true',
        limit: '100',
        offset: String(offset)
      })
      const pageRows = await api(`/races?${params.toString()}`)
      loaded.push(...pageRows)
      if (pageRows.length < 100) break
    }
    trackRacesByGame.value = { ...trackRacesByGame.value, [game]: loaded }
  } catch (err) {
    trackError.value = err.message
  } finally {
    trackLoading.value = false
  }
}

function resetPageAndLoad() {
  if (page.value === 1) {
    load()
    return
  }
  page.value = 1
}

onMounted(load)
onMounted(() => {
  loadRaceAssets()
  loadTrackRaces(trackGame.value)
})
watch(page, load)
watch([search, sort, ratingGame], resetPageAndLoad)
watch(trackGame, (game) => {
  selectedTrack.value = ''
  trackSearch.value = ''
  loadTrackRaces(game)
})

function pilotGames(pilot) {
  return pilot.games?.length ? pilot.games.map((game) => gameLabel(t, game)).join(' / ') : t('common.none')
}

function pilotNumber(pilot) {
  return pilot.pilot_number !== null && pilot.pilot_number !== undefined ? `#${formatPilotNumber(pilot.pilot_number)}` : '-'
}

function pilotCountry(pilot) {
  return pilot.country ? countryLabel(t, pilot.country) : t('common.none')
}

function formatDuration(ms) {
  if (!Number.isFinite(Number(ms))) return '-'
  const totalMs = Math.max(0, Math.round(Number(ms)))
  const minutes = Math.floor(totalMs / 60000)
  const seconds = Math.floor((totalMs % 60000) / 1000)
  const millis = totalMs % 1000
  return `${minutes}:${String(seconds).padStart(2, '0')}.${String(millis).padStart(3, '0')}`
}

function resultRows(race) {
  if (Array.isArray(race?.results)) return race.results
  return Array.isArray(race?.results?.rows) ? race.results.rows : []
}

function numericValue(...values) {
  for (const value of values) {
    const number = Number(value)
    if (Number.isFinite(number) && number > 0) return number
  }
  return null
}

function registrationForRow(race, row) {
  const userId = Number(row.user_id)
  const raceNumber = Number(row.race_number ?? row.pilot_number)
  return (race.registered_pilots || []).find((pilot) => {
    if (Number.isFinite(userId) && Number(pilot.user_id) === userId) return true
    return Number.isFinite(raceNumber) && Number(pilot.pilot_number) === raceNumber
  })
}

function trackRaceEntry(race, row) {
  if (row.status === 'missing') return null
  const registered = registrationForRow(race, row)
  const laps = numericValue(row.lap_count, row.laps)
  const finishMs = numericValue(row.adjusted_finish_ms, row.finish_ms, row.driver_total_time_ms)
  const lapCandidates = [
    { value: numericValue(row.best_lap_ms), session: 'race' },
    { value: numericValue(row.qualification_best_lap_ms), session: 'qualification' }
  ].filter((candidate) => candidate.value !== null)
  const bestLap = lapCandidates.sort((left, right) => left.value - right.value)[0] || { value: null, session: null }
  const bestLapMs = bestLap.value
  if (finishMs === null && bestLapMs === null) return null
  const averageLapMs = finishMs !== null && laps && laps > 0 ? finishMs / laps : bestLapMs
  const driverName = [row.first_name, row.last_name].filter(Boolean).join(' ').trim()
  const fallbackName = row.driver_name || row.nickname || row.login || registered?.nickname || registered?.login || t('common.none')
  const pilotKey = row.user_id ? `user:${row.user_id}` : `driver:${fallbackName.toLowerCase()}`

  return {
    pilotKey,
    user_id: row.user_id,
    pilotName: driverName || fallbackName,
    pilotNumber: row.race_number ?? row.pilot_number ?? registered?.pilot_number,
    rating: row.rating ?? registered?.rating,
    game_ratings: row.game_ratings ?? registered?.game_ratings,
    carModel: row.car_model ?? registered?.car_model ?? t('common.none'),
    bestLapMs,
    bestLapSession: bestLap.session,
    finishMs,
    averageLapMs,
    laps: laps || 0,
    raceId: race.id,
    raceName: race.name,
    raceDate: race.datetime_start
  }
}

function trackIdFor(gameAssets, track) {
  const trackName = String(track || '').trim()
  const ids = gameAssets.track_ids || {}
  return ids[trackName] || Object.entries(ids).find(([key]) => key.toLowerCase() === trackName.toLowerCase())?.[1] || trackName.toLowerCase()
}

function trackNameForId(gameAssets, trackId, fallback = '') {
  if (!trackId) return fallback
  return Object.entries(gameAssets.track_ids || {}).find(([, id]) => id === trackId)?.[0] || fallback
}

function trackImageFor(gameAssets, track, trackId = '') {
  const trackName = String(track || '').trim()
  const images = gameAssets.track_images || {}
  const imageTrack = trackName || trackNameForId(gameAssets, trackId)
  return images[imageTrack] || Object.entries(images).find(([key]) => key.toLowerCase() === imageTrack.toLowerCase())?.[1] || ''
}

function expectedAverageLapFor(gameAssets, track) {
  const trackName = String(track || '').trim().toLowerCase()
  const entry = Object.entries(gameAssets.expected_average_lap_ms || {}).find(([name]) => name.toLowerCase() === trackName)
  return entry && Number(entry[1]) > 0 ? Number(entry[1]) : null
}

const trackSummaries = computed(() => {
  const gameAssets = trackGame.value === 'ACC'
    ? (raceAssets.value.games?.ACC || raceAssets.value || { tracks: [] })
    : (raceAssets.value.games?.[trackGame.value] || { tracks: [] })
  const map = new Map()

  for (const track of gameAssets.tracks || []) {
    const track_id = trackIdFor(gameAssets, track)
    map.set(track_id, { track_id, track, image_url: trackImageFor(gameAssets, track, track_id), expected_lap_ms: expectedAverageLapFor(gameAssets, track), race_count: 0, averageSamples: [], topByPilot: new Map() })
  }

  for (const race of trackRacesByGame.value[trackGame.value] || []) {
    const raceTrack = String(race.track || race.results?.track || '').trim()
    const raceTrackId = race.track_id || trackIdFor(gameAssets, raceTrack)
    let summary = map.get(raceTrackId)
    if (!summary && raceTrack) {
      summary = [...map.values()].find((item) => item.track.toLowerCase() === raceTrack.toLowerCase())
    }
    if (!summary && raceTrack) {
      summary = { track_id: raceTrackId, track: raceTrack, image_url: trackImageFor(gameAssets, raceTrack, raceTrackId), expected_lap_ms: expectedAverageLapFor(gameAssets, raceTrack), race_count: 0, averageSamples: [], topByPilot: new Map() }
      map.set(raceTrackId, summary)
    }
    if (!summary) continue
    const entries = resultRows(race).map((row) => trackRaceEntry(race, row)).filter(Boolean)
    if (!entries.length) continue
    summary.race_count += 1
    for (const entry of entries) {
      if (entry.averageLapMs !== null) summary.averageSamples.push(entry.averageLapMs)
      if (entry.bestLapMs === null) continue
      const current = summary.topByPilot.get(entry.pilotKey)
      if (!current || entry.bestLapMs < current.bestLapMs) {
        summary.topByPilot.set(entry.pilotKey, entry)
      }
    }
  }

  return Array.from(map.values())
    .map((summary) => {
      const average_lap_ms = summary.averageSamples.length
        ? summary.averageSamples.reduce((sum, value) => sum + value, 0) / summary.averageSamples.length
        : null
      return {
        track: summary.track,
        track_id: summary.track_id,
        image_url: summary.image_url,
        expected_lap_ms: summary.expected_lap_ms,
        race_count: summary.race_count,
        average_lap_ms,
        topRows: Array.from(summary.topByPilot.values()).sort((left, right) => left.bestLapMs - right.bestLapMs).slice(0, 15)
      }
    })
    .sort((left, right) => left.track.localeCompare(right.track, undefined, { sensitivity: 'base' }))
})

const filteredTrackSummaries = computed(() => {
  const query = trackSearch.value.trim().toLowerCase()
  if (!query) return trackSummaries.value
  return trackSummaries.value.filter((summary) => summary.track.toLowerCase().includes(query))
})

watch(filteredTrackSummaries, (summaries) => {
  if (summaries.some((summary) => summary.track === selectedTrack.value)) return
  selectedTrack.value = summaries[0]?.track || ''
})

watch(() => route.query.track, (track) => {
  if (track) {
    activeTab.value = 'tracks'
    selectedTrack.value = String(track)
  }
}, { immediate: true })

const selectedTrackSummary = computed(() => trackSummaries.value.find((summary) => summary.track === selectedTrack.value))
const selectedTrackRows = computed(() => selectedTrackSummary.value?.topRows || [])

function trackRaceTime(row) {
  if (row.finishMs === null) return '-'
  const laps = row.laps ? `${row.laps} ${t('tracks.lapsShort')}` : t('tracks.noLaps')
  return `${formatDuration(row.finishMs)} · ${laps}`
}

function carModelLabel(value) {
  if (value === null || value === undefined || value === '') return t('common.none')
  if (trackGame.value !== 'ACC') return String(value)
  const numericId = Number(value)
  if (!Number.isInteger(numericId)) return String(value)
  const mapping = raceAssets.value.car_model_ids || {}
  return Object.entries(mapping).find(([, id]) => Number(id) === numericId)?.[0] || String(value)
}
async function chooseTrackImage(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || !selectedTrack.value) return

  trackError.value = ''
  trackImageUploading.value = true
  try {
    const body = new FormData()
    body.append('game', trackGame.value)
    body.append('track', selectedTrack.value)
    body.append('file', file, file.name)
    raceAssets.value = await api('/race-assets/track-image', { method: 'POST', body })
  } catch (err) {
    trackError.value = err.message || t('tracks.cropError')
  } finally {
    trackImageUploading.value = false
  }
}

async function deleteTrackImage() {
  if (!selectedTrack.value || !selectedTrackSummary.value?.image_url || !window.confirm(t('tracks.deleteImageConfirm'))) return
  trackError.value = ''
  trackImageUploading.value = true
  try {
    const params = new URLSearchParams({ game: trackGame.value, track: selectedTrack.value })
    raceAssets.value = await api(`/race-assets/track-image?${params.toString()}`, { method: 'DELETE' })
  } catch (err) {
    trackError.value = err.message
  } finally {
    trackImageUploading.value = false
  }
}
</script>

<template>
  <section class="section pilot-list-page">
    <div class="section-header pilot-list-header">
      <h1>{{ t('nav.pilots') }}</h1>
      <div class="pilot-page-tabs">
        <button class="role-segment-option" type="button" :class="{ 'is-selected': activeTab === 'pilots' }" @click="activeTab = 'pilots'">
          {{ t('pilotTabs.pilots') }}
        </button>
        <button class="role-segment-option" type="button" :class="{ 'is-selected': activeTab === 'tracks' }" @click="activeTab = 'tracks'">
          {{ t('pilotTabs.tracks') }}
        </button>
      </div>
      <div v-if="activeTab === 'pilots'" class="pilot-list-controls">
        <label class="pilot-control-field">
          <Search :size="16" />
          <input v-model="search" class="pilot-list-search" :placeholder="t('common.search')" />
        </label>
        <label class="pilot-control-field pilot-control-select">
          <SlidersHorizontal :size="16" />
          <select v-model="sort" class="pilot-list-sort" :aria-label="t('common.sort')">
            <option value="rating_desc">{{ t('sort.ratingDesc') }}</option>
            <option value="rating_asc">{{ t('sort.ratingAsc') }}</option>
            <option value="sr_desc">{{ t('sort.srDesc') }}</option>
            <option value="sr_asc">{{ t('sort.srAsc') }}</option>
            <option value="alpha_asc">{{ t('sort.alphaAsc') }}</option>
            <option value="alpha_desc">{{ t('sort.alphaDesc') }}</option>
          </select>
        </label>
        <label class="pilot-control-field pilot-control-select">
          <select v-model="ratingGame" class="pilot-list-sort" :aria-label="t('fields.game')">
            <option v-for="option in trackGameOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
      </div>
    </div>
    <p v-if="activeTab === 'pilots' && error" class="error">{{ error }}</p>
    <div v-if="activeTab === 'pilots'" class="pilot-roster card" role="table" :aria-label="t('pilotTabs.pilots')">
      <div class="pilot-roster-head" role="row">
        <span role="columnheader">#</span>
        <span role="columnheader">{{ t('roles.pilot') }}</span>
        <span role="columnheader">{{ t('fields.team') }}</span>
        <span role="columnheader">{{ t('fields.country') }}</span>
        <span role="columnheader">RER</span>
        <span role="columnheader">SR</span>
        <span role="columnheader">{{ t('fields.ratingRaces') }}</span>
      </div>

      <article v-for="pilot in pilots" :key="pilot.id" class="pilot-roster-row" role="row">
        <span class="pilot-roster-number" role="cell" data-label="#">{{ pilotNumber(pilot) }}</span>

        <div class="pilot-roster-driver" role="cell" :data-label="t('roles.pilot')">
          <UserAvatar mini :src="pilot.avatar_url" :color="pilot.avatar_color" :label="pilot.nickname || pilot.login" />
          <RouterLink class="user-list-main" :to="`/pilots/${pilot.id}`">
            <span class="user-name-line">
              <strong>{{ pilotName(pilot, pilot.login) }}</strong>
              <LicenseBadge :user="pilot" :game="ratingGame" />
            </span>
            <span>{{ pilot.nickname || pilot.login }} - {{ pilotGames(pilot) }}</span>
          </RouterLink>
        </div>

        <span class="pilot-roster-team" role="cell" :data-label="t('fields.team')">
          <RouterLink v-if="pilot.team_id" class="team-mini-chip team-link-chip" :to="teamHref(pilot.team_id)" :title="pilot.team_name || t('common.none')">
            {{ teamShortName(pilot.team_name, pilot.team_abbreviation) }}
          </RouterLink>
          <span v-else class="team-mini-chip" :title="pilot.team_name || t('common.none')">{{ teamShortName(pilot.team_name, pilot.team_abbreviation) }}</span>
        </span>
        <span class="pilot-roster-country" role="cell" :data-label="t('fields.country')">{{ pilotCountry(pilot) }}</span>
        <span class="pilot-roster-metric" role="cell" data-label="RER"><strong>{{ formatRating(ratingForGame(pilot, ratingGame)) }}</strong><small>RER {{ ratingGame }}</small></span>
        <span class="pilot-roster-metric" role="cell" data-label="SR"><strong>{{ pilot.sr }}</strong><small>SR</small></span>
        <span class="pilot-roster-metric" role="cell" :data-label="t('fields.ratingRaces')"><strong>{{ ratingRaceCountForGame(pilot, ratingGame) }}</strong><small>{{ t('fields.ratingRaces') }}</small></span>
      </article>

      <div v-if="!pilots.length" class="pilot-roster-empty">{{ t('common.noMatches') }}</div>
    </div>
    <PaginationControls v-if="activeTab === 'pilots'" v-model:page="page" :page-size="pageSize" :loaded-count="pilots.length" :has-next="hasNextPage" />

    <div v-else class="tracks-board">
      <div class="track-toolbar card">
        <label class="pilot-control-field pilot-control-select">
          <MapPinned :size="16" />
          <select v-model="trackGame" :aria-label="t('fields.game')">
            <option v-for="option in trackGameOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
        <label class="pilot-control-field track-search-field">
          <Search :size="16" />
          <input v-model="trackSearch" type="search" :placeholder="t('fields.track')" :aria-label="t('fields.track')" />
        </label>
        <span class="track-toolbar-count">{{ trackLoading ? t('common.loading') : t('tracks.trackCount', { count: filteredTrackSummaries.length }) }}</span>
      </div>

      <p v-if="trackError" class="error">{{ trackError }}</p>

      <div v-if="filteredTrackSummaries.length" class="track-card-grid">
        <button
          v-for="track in filteredTrackSummaries"
          :key="track.track_id"
          class="track-summary-card"
          type="button"
          :class="{ active: selectedTrack === track.track }"
          @click="selectedTrack = track.track"
        >
          <img v-if="track.image_url" class="track-summary-image" :src="track.image_url" alt="" />
          <span>{{ track.track }}</span>
          <strong>{{ formatDuration(track.average_lap_ms) }}</strong>
          <small>{{ t('tracks.averageLap') }} · {{ t('tracks.racesCount', { count: track.race_count }) }}</small>
          <small v-if="track.expected_lap_ms" class="track-expected-lap">{{ t('tracks.expectedAverageLap') }}: {{ formatDuration(track.expected_lap_ms) }}</small>
        </button>
      </div>
      <div v-else class="pilot-roster-empty">{{ t('common.noMatches') }}</div>

      <section class="card track-record-card">
        <div class="section-header compact">
          <div>
            <h2>{{ selectedTrack || t('tracks.title') }}</h2>
            <p class="muted">{{ t('tracks.subtitle') }}</p>
          </div>
          <div class="track-record-actions">
            <label v-if="canManageTrackImages" class="button small track-image-button">
              <ImagePlus :size="15" />
              {{ t('tracks.addImage') }}
              <input ref="trackImageInput" type="file" accept="image/png,image/jpeg,image/webp" @change="chooseTrackImage" />
            </label>
            <button
              v-if="canManageTrackImages && selectedTrackSummary?.image_url"
              class="button danger small"
              type="button"
              :disabled="trackImageUploading"
              @click="deleteTrackImage"
            >
              <Trash2 :size="15" />
              {{ t('tracks.deleteImage') }}
            </button>
            <span class="pill">{{ t('tracks.topLimit') }}</span>
          </div>
        </div>

        <img v-if="selectedTrackSummary?.image_url" class="track-record-hero-image" :src="selectedTrackSummary.image_url" alt="" />

        <div v-if="selectedTrackRows.length" class="track-record-table-wrap">
          <table class="track-record-table">
            <thead>
              <tr>
                <th>#</th>
                <th>{{ t('roles.pilot') }}</th>
                <th>{{ t('tracks.bestLap') }}</th>
                <th>{{ t('common.car') }}</th>
                <th>{{ t('tracks.raceTime') }}</th>
                <th>{{ t('fields.race') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in selectedTrackRows" :key="`${row.raceId}-${row.pilotKey}`">
                <td>{{ index + 1 }}</td>
                <td>
                  <RouterLink v-if="row.user_id" class="track-pilot-link" :to="`/pilots/${row.user_id}`">
                    <span class="user-name-line">
                      <strong>{{ row.pilotName }}</strong>
                      <LicenseBadge :user="row" :game="trackGame" />
                    </span>
                    <small>#{{ formatPilotNumber(row.pilotNumber) }}</small>
                  </RouterLink>
                  <span v-else class="track-pilot-link">
                    <span class="user-name-line">
                      <strong>{{ row.pilotName }}</strong>
                      <LicenseBadge :user="row" :game="trackGame" />
                    </span>
                    <small>#{{ formatPilotNumber(row.pilotNumber) }}</small>
                  </span>
                </td>
                <td class="track-best-lap-cell">
                  <strong>{{ formatDuration(row.bestLapMs) }}</strong>
                  <span v-if="row.bestLapSession" class="track-lap-source">{{ row.bestLapSession === 'qualification' ? t('tracks.lapSourceQualification') : t('tracks.lapSourceRace') }}</span>
                </td>
                <td>{{ carModelLabel(row.carModel) }}</td>
                <td>{{ trackRaceTime(row) }}</td>
                <td><RouterLink class="track-race-link" :to="`/races/${row.raceId}`">{{ row.raceName }}</RouterLink></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="pilot-roster-empty">{{ t('tracks.noResults') }}</div>
      </section>
    </div>

  </section>
</template>
