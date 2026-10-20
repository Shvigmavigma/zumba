<script>
// Finished races per game outlive the component, so switching between the
// Pilots and Tracks tabs does not refetch up to ten pages each time.
const TRACK_RACES_TTL_MS = 5 * 60000
const trackRacesCache = new Map()
</script>

<script setup>
// Tracks tab: per-game track cards with average laps, and the top-15 best laps
// on the selected track. Logic moved unchanged from PilotList.
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { Box, MapPinned, Search, Timer } from 'lucide-vue-next'
import { api } from '../../api'
import LicenseBadge from '../../components/LicenseBadge.vue'
import PilotRoles from '../../components/PilotRoles.vue'
import EmptyState from '../../ui/EmptyState.vue'
import SegmentedControl from '../../ui/SegmentedControl.vue'
import { gameOptions } from '../../i18nLabels'
import { formatPilotNumber } from '../../pilotDisplay'
import { updateRaceAssetsCache } from '../../raceDisplay'
import { state } from '../../store'
import { findTrackLayout } from '../../ui/track/trackLayouts'
import { lapsAnnulled } from '../race/raceClassification'
import TrackRecordsHero from './TrackRecordsHero.vue'

const { t } = useI18n()
const route = useRoute()
const raceAssets = ref({ tracks: [], classes: [], games: {} })
const trackGame = ref('ACC')
const selectedTrack = ref('')
const trackSearch = ref('')
const trackRacesByGame = ref({})
const trackLoading = ref(false)
const trackError = ref('')
const trackImageUploading = ref(false)
const trackGrid = ref(null)
const ACC_MAX_TIME_MS = 2147483647
const ACC_MAX_TIME_ALIASES = new Set([ACC_MAX_TIME_MS, 4294967295])
const trackGameOptions = computed(() => gameOptions(t))
const canManageTrackImages = computed(() => state.user?.role === 'admin')

async function loadRaceAssets() {
  try {
    raceAssets.value = await api('/race-assets')
  } catch {
    raceAssets.value = { tracks: [], classes: [], games: {} }
  }
}

async function loadTrackRaces(game) {
  if (trackRacesByGame.value[game]) return
  const cached = trackRacesCache.get(game)
  if (cached && Date.now() - cached.at < TRACK_RACES_TTL_MS) {
    trackRacesByGame.value = { ...trackRacesByGame.value, [game]: cached.rows }
    return
  }
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
    trackRacesCache.set(game, { at: Date.now(), rows: loaded })
    trackRacesByGame.value = { ...trackRacesByGame.value, [game]: loaded }
  } catch (err) {
    trackError.value = err.message
  } finally {
    trackLoading.value = false
  }
}

onMounted(() => {
  loadRaceAssets()
  loadTrackRaces(trackGame.value)
})

watch(trackGame, (game) => {
  selectedTrack.value = ''
  trackSearch.value = ''
  loadTrackRaces(game)
})

function formatDuration(ms) {
  if (ms === null || ms === undefined || !Number.isFinite(Number(ms))) return '—'
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

function isAccMaxTime(value) {
  const number = Number(value)
  return Number.isFinite(number) && (ACC_MAX_TIME_ALIASES.has(number) || number >= ACC_MAX_TIME_MS)
}

function raceTimeValue(value, game) {
  const number = Number(value)
  if (!Number.isFinite(number) || number <= 0) return null
  return game === 'ACC' && isAccMaxTime(number) ? null : number
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
  const rawFinishMs = row.adjusted_finish_ms ?? row.finish_ms ?? row.driver_total_time_ms
  const finishMs = raceTimeValue(rawFinishMs, race.game)
  // Laps the stewards annulled are not records; the race result still counts for the average lap.
  const lapCandidates = lapsAnnulled(row) ? [] : [
    { value: raceTimeValue(row.best_lap_ms, race.game), session: 'race' },
    { value: raceTimeValue(row.qualification_best_lap_ms, race.game), session: 'qualification' }
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
    pilot_roles: row.pilot_roles ?? registered?.pilot_roles ?? [],
    carModel: row.car_model ?? registered?.car_model ?? t('common.none'),
    bestLapMs,
    bestLapSession: bestLap.session,
    finishMs,
    averageLapMs,
    laps: laps || 0,
    didNotFinish: race.game === 'ACC' && (isAccMaxTime(rawFinishMs) || row.status === 'dnf'),
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
    map.set(track_id, { track_id, track, image_url: trackImageFor(gameAssets, track, track_id), expected_lap_ms: expectedAverageLapFor(gameAssets, track), race_count: 0, averageSamples: [], topByPilot: new Map(), races: [] })
  }

  for (const race of trackRacesByGame.value[trackGame.value] || []) {
    const raceTrack = String(race.track || race.results?.track || '').trim()
    const raceTrackId = race.track_id || trackIdFor(gameAssets, raceTrack)
    let summary = map.get(raceTrackId)
    if (!summary && raceTrack) {
      summary = [...map.values()].find((item) => item.track.toLowerCase() === raceTrack.toLowerCase())
    }
    if (!summary && raceTrack) {
      summary = { track_id: raceTrackId, track: raceTrack, image_url: trackImageFor(gameAssets, raceTrack, raceTrackId), expected_lap_ms: expectedAverageLapFor(gameAssets, raceTrack), race_count: 0, averageSamples: [], topByPilot: new Map(), races: [] }
      map.set(raceTrackId, summary)
    }
    if (!summary) continue
    const entries = resultRows(race).map((row) => trackRaceEntry(race, row)).filter(Boolean)
    if (!entries.length) continue
    summary.race_count += 1
    summary.races.push(race)
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
        races: summary.races,
        hasLayout: Boolean(findTrackLayout({ track: summary.track, trackId: summary.track_id })),
        topRows: Array.from(summary.topByPilot.values()).sort((left, right) => left.bestLapMs - right.bestLapMs).slice(0, 15)
      }
    })
    // Tracks with a 3D layout lead the row, then the rest; each group in name order.
    .sort((left, right) => Number(right.hasLayout) - Number(left.hasLayout)
      || left.track.localeCompare(right.track, undefined, { sensitivity: 'base' }))
})

const filteredTrackSummaries = computed(() => {
  const query = trackSearch.value.trim().toLowerCase()
  if (!query) return trackSummaries.value
  return trackSummaries.value.filter((summary) => summary.track.toLowerCase().includes(query))
})

watch(filteredTrackSummaries, (summaries) => {
  if (summaries.some((summary) => summary.track === selectedTrack.value)) return
  // With nothing chosen, open on a track that has a 3D layout: it has the most to show.
  const withLayout = summaries.find((summary) => summary.hasLayout)
  selectedTrack.value = (withLayout || summaries[0])?.track || ''
})

watch(() => route.query.track, (track) => {
  if (track) selectedTrack.value = String(track)
}, { immediate: true })

// Keep the chosen card visible in the horizontal track row.
watch(selectedTrack, async () => {
  await nextTick()
  trackGrid.value?.querySelector('.track.is-active')?.scrollIntoView({ inline: 'center', block: 'nearest', behavior: 'smooth' })
})

const selectedTrackSummary = computed(() => trackSummaries.value.find((summary) => summary.track === selectedTrack.value))
const selectedTrackRows = computed(() => selectedTrackSummary.value?.topRows || [])
// A track with a 3D layout shows its records on it (who holds each sector, the lap record);
// the header works them out from the track's races, and only for such a track.
const selectedLayout = computed(() => {
  const summary = selectedTrackSummary.value
  return summary ? findTrackLayout({ track: summary.track, trackId: summary.track_id }) : null
})

function trackRaceTime(row) {
  if (row.didNotFinish) return t('raceDetails.didNotFinish')
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
    updateRaceAssetsCache(raceAssets.value)
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
    updateRaceAssetsCache(raceAssets.value)
  } catch (err) {
    trackError.value = err.message
  } finally {
    trackImageUploading.value = false
  }
}
</script>

<template>
  <div class="tracks">
    <div class="tracks__toolbar">
      <SegmentedControl v-model="trackGame" :options="trackGameOptions" :aria-label="t('fields.game')" />
      <label class="tracks__search">
        <Search :size="16" />
        <input v-model="trackSearch" type="search" :placeholder="t('pilotsPage.tracks.searchPlaceholder')" :aria-label="t('fields.track')" />
      </label>
      <span class="ui-chip">
        <MapPinned :size="13" />
        <span :class="{ 'ui-shiny': trackLoading }">{{ trackLoading ? t('common.loading') : t('tracks.trackCount', { count: filteredTrackSummaries.length }) }}</span>
      </span>
    </div>

    <p v-if="trackError" class="ui-alert">{{ trackError }}</p>

    <div v-if="filteredTrackSummaries.length" ref="trackGrid" class="tracks__grid">
      <button
        v-for="(track, index) in filteredTrackSummaries"
        :key="track.track_id"
        v-reveal="{ delay: Math.min(index, 12) * 40, y: 12, blur: 0 }"
        class="track"
        type="button"
        :class="{ 'is-active': selectedTrack === track.track }"
        :aria-pressed="selectedTrack === track.track"
        @click="selectedTrack = track.track"
      >
        <span class="track__media">
          <img v-if="track.image_url" v-track-art :src="track.image_url" alt="" loading="lazy" />
          <span v-else class="track__fallback"><MapPinned :size="22" /></span>
          <span v-if="track.hasLayout" class="track__3d ui-chip ui-chip--solid" :title="t('pilotsPage.tracks.layout.badge')"><Box :size="12" />3D</span>
        </span>
        <span class="track__body">
          <strong class="track__name">{{ track.track }}</strong>
          <span class="track__avg ui-num">{{ formatDuration(track.average_lap_ms) }}</span>
          <small>{{ t('tracks.averageLap') }} · {{ t('tracks.racesCount', { count: track.race_count }) }}</small>
          <small v-if="track.expected_lap_ms" class="track__expected">{{ t('tracks.expectedAverageLap') }}: <b class="ui-num">{{ formatDuration(track.expected_lap_ms) }}</b></small>
        </span>
      </button>
    </div>
    <EmptyState v-else :loading="trackLoading" :icon="MapPinned" :title="trackLoading ? t('ui.common.loading') : t('common.noMatches')" compact />

    <section class="records ui-card ui-card--flush">
      <TrackRecordsHero
        :track="selectedTrack"
        :image="selectedTrackSummary?.image_url || ''"
        :can-manage="canManageTrackImages"
        :busy="trackImageUploading"
        :layout="selectedLayout"
        :races="selectedTrackSummary?.races || []"
        :top-row="selectedTrackRows[0] || null"
        @choose-image="chooseTrackImage"
        @delete-image="deleteTrackImage"
      />

      <div v-if="selectedTrackRows.length" class="ui-table-wrap records__table">
        <table class="ui-table">
          <thead>
            <tr>
              <th>#</th>
              <th>{{ t('roles.pilot') }}</th>
              <th class="is-num">{{ t('tracks.bestLap') }}</th>
              <th>{{ t('common.car') }}</th>
              <th class="is-num">{{ t('tracks.raceTime') }}</th>
              <th>{{ t('fields.race') }}</th>
            </tr>
          </thead>
          <tbody :key="selectedTrack" class="records__body">
            <tr v-for="(row, index) in selectedTrackRows" :key="`${row.raceId}-${row.pilotKey}`" :style="{ '--i': index }">
              <td data-label="#"><span class="ui-pos" :class="index < 3 ? `ui-pos--${index + 1}` : ''">{{ index + 1 }}</span></td>
              <td :data-label="t('roles.pilot')">
                <component :is="row.user_id ? 'RouterLink' : 'span'" class="records__pilot" :to="row.user_id ? `/pilots/${row.user_id}` : undefined">
                  <span class="records__name">
                    <strong>{{ row.pilotName }}</strong>
                    <PilotRoles :roles="row.pilot_roles" />
                    <LicenseBadge :user="row" :game="trackGame" />
                  </span>
                  <small class="ui-num">#{{ formatPilotNumber(row.pilotNumber) }}</small>
                </component>
              </td>
              <td class="is-num" :data-label="t('tracks.bestLap')">
                <span class="records__lap" :class="{ 'is-best': index === 0 }"><Timer v-if="index === 0" :size="13" />{{ formatDuration(row.bestLapMs) }}</span>
                <small v-if="row.bestLapSession" class="records__source">{{ row.bestLapSession === 'qualification' ? t('tracks.lapSourceQualification') : t('tracks.lapSourceRace') }}</small>
              </td>
              <td :data-label="t('common.car')">{{ carModelLabel(row.carModel) }}</td>
              <td class="is-num" :data-label="t('tracks.raceTime')">{{ trackRaceTime(row) }}</td>
              <td :data-label="t('fields.race')"><RouterLink class="ui-link" :to="`/races/${row.raceId}`">{{ row.raceName }}</RouterLink></td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else class="records__empty" :icon="Timer" :title="selectedTrack ? t('tracks.noResults') : t('pilotsPage.tracks.pickTrack')" compact />
    </section>
  </div>
</template>

<style scoped>
.tracks {
  display: grid;
  gap: 18px;
}

.tracks__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
}

.tracks__search {
  display: flex;
  flex: 1 1 220px;
  align-items: center;
  gap: 10px;
  max-width: 360px;
  min-height: 44px;
  padding: 0 14px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-pill);
  background: var(--c-sunken);
  color: var(--c-text-3);
}

.tracks__search input {
  flex: 1 1 auto;
  min-width: 0;
  height: 40px;
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
  color: var(--c-text);
  outline: none;
}

.tracks__search input:focus {
  box-shadow: none;
}

/* One swipeable row keeps the records table in view. */
.tracks__grid {
  display: grid;
  grid-auto-columns: minmax(210px, 230px);
  grid-auto-flow: column;
  gap: 10px;
  padding: 4px 2px 12px;
  overflow-x: auto;
  scroll-snap-type: x proximity;
  scrollbar-width: thin;
}

.tracks__grid > .track {
  scroll-snap-align: start;
}

.track {
  display: grid;
  overflow: hidden;
  padding: 0;
  border: 1px solid var(--c-line);
  border-radius: var(--r-lg);
  background: var(--c-surface);
  color: var(--c-text);
  cursor: pointer;
  text-align: left;
  transition: border-color var(--dur-2), transform var(--dur-3) var(--ease-ios), box-shadow var(--dur-3);
}

.track:hover {
  border-color: var(--c-blue-line);
  transform: translateY(-3px);
}

.track.is-active {
  border-color: var(--bm-blue);
  box-shadow: 0 0 0 1px var(--bm-blue), var(--shadow-blue);
}

.track__media {
  position: relative;
  display: grid;
  height: 96px;
  overflow: hidden;
  background: linear-gradient(135deg, color-mix(in srgb, var(--bm-blue) 35%, var(--c-elevated)), var(--c-elevated));
}

.track__media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 900ms var(--ease-out);
}

.track:hover .track__media img {
  transform: scale(1.07);
}

/* This track has a 3D layout with its records on it. */
.track__3d {
  position: absolute;
  top: 8px;
  right: 8px;
  gap: 4px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
}

.track__fallback {
  display: grid;
  place-items: center;
  color: rgba(255, 255, 255, 0.6);
}

.track__body {
  display: grid;
  gap: 4px;
  padding: 12px 14px 14px;
}

.track__name {
  overflow: hidden;
  font-size: 14px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.track__avg {
  color: var(--c-text);
  font-size: 20px;
  font-weight: 600;
}

.track__body small {
  color: var(--c-text-3);
  font-size: 12px;
}

.track__expected b {
  color: var(--c-text-2);
  font-weight: 500;
}

.records__table {
  border: 0;
  border-top: 1px solid var(--c-line);
  border-radius: 0;
}

/* Only opacity, and nothing left on the row afterwards: a table row holding an animated transform
   becomes a layer of its own, and Chrome could leave it unpainted after the table changed. */
.records__body tr {
  animation: records-row 520ms var(--ease-out) backwards;
  animation-delay: calc(var(--i) * 35ms);
}

@keyframes records-row {
  from {
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .records__body tr {
    animation: none;
  }
}

.records__pilot {
  display: grid;
  gap: 2px;
  color: var(--c-text);
  text-decoration: none;
}

.records__name {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.records__pilot small {
  color: var(--c-text-3);
  font-size: 11.5px;
}

.records__lap {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 15px;
  font-weight: 600;
}

.records__lap.is-best {
  color: #c79bff;
}

.records__source {
  display: block;
  color: var(--c-text-3);
  font-family: var(--font-body);
  font-size: 11px;
}

.records__empty {
  margin: 16px;
}

@media (max-width: 760px) {
  .records__table .ui-table thead {
    display: none;
  }

  .records__table .ui-table,
  .records__table .ui-table tbody,
  .records__table .ui-table tr,
  .records__table .ui-table td {
    display: block;
  }

  .records__table .ui-table tr {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 4px 12px;
    padding: 12px 14px;
    border-bottom: 1px solid var(--c-line);
  }

  .records__table .ui-table td {
    padding: 0;
    border: 0;
    text-align: left;
  }

  .records__table .ui-table td:first-child {
    grid-row: span 5;
  }

  .records__table .ui-table td:not(:first-child):not(:nth-child(2))::before {
    margin-right: 6px;
    color: var(--c-text-3);
    content: attr(data-label) ':';
    font-family: var(--font-mono);
    font-size: 10.5px;
    text-transform: uppercase;
  }
}
</style>
