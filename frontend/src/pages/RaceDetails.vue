<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ChevronDown, ChevronUp, Cloud, CloudDrizzle, CloudLightning, CloudRain, CloudSun, Crop, Film, Heart, ImageUp, Info, MapPin, Scale, Sun, Thermometer, Trash2, Upload, UserMinus, X } from 'lucide-vue-next'
import { api } from '../api'
import ImageCropper from '../components/ImageCropper.vue'
import LicenseBadge from '../components/LicenseBadge.vue'
import PaginationControls from '../components/PaginationControls.vue'
import PilotRoles from '../components/PilotRoles.vue'
import RacePenaltyListModal from '../components/RacePenaltyListModal.vue'
import UserAvatar from '../components/UserAvatar.vue'
import { countryLabel, gameLabel, isExternalRace, statusLabel } from '../i18nLabels'
import { filterPilots, formatPilotNumber, formatRating, ratingForGame, sortPilots, teamHref, teamShortName } from '../pilotDisplay'
import { state } from '../store'
import { formatDateTime, formatTimeRangeInTimeZone } from '../timezone'

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
const raceAssets = ref({ tracks: [], classes: [], games: {} })
const trackImageFile = ref(null)
const trackImageInput = ref(null)
const trackImageDisplay = ref(null)
const trackImageOpen = ref(false)
const trackImageCropOpen = ref(false)
const trackImageCropError = ref('')
const trackImageCropTarget = ref({ width: 1200, height: 700 })
const trackAverageLapMs = ref(null)
const weatherDetailsOpen = ref(false)
const collapsedRaceFacts = ref({})
const manualRows = ref([])
const participantsExpanded = ref(false)
const penaltiesOpen = ref(false)
const focusedPenaltyId = ref(null)
const penaltyCreateOpen = ref(false)
const resultsTab = ref('race')
const raceOperationalTab = ref('information')
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
const ACC_MAX_TIME_MS = 2147483647
const ACC_MAX_TIME_ALIASES = new Set([ACC_MAX_TIME_MS, 4294967295])
const myTeam = ref(null)
const teamRaceNumber = ref(pilotNumberDraft(state.user?.pilot_number))
const teamDriverIds = ref([])
const forcePilotId = ref('')
const forcePilotNumber = ref('')
const forcePilotCar = ref('')
const forcePilotCandidates = ref([])
const forcePilotLoading = ref(false)
const forcePilotSearch = ref('')
let forcePilotSearchTimer = null
let forcePilotSearchRequest = 0
const raceAssetConfig = computed(() => {
  const game = race.value?.game
  if (!game) return { track_images: {} }
  if (game === 'ACC') return raceAssets.value.games?.ACC || raceAssets.value || { track_images: {} }
  return raceAssets.value.games?.[game] || { track_images: {} }
})
const trackExpectedAverageLapMs = computed(() => {
  const track = String(race.value?.track || '').trim().toLowerCase()
  if (!track) return null
  const entry = Object.entries(raceAssetConfig.value.expected_average_lap_ms || {})
    .find(([name]) => name.toLowerCase() === track)
  return entry && Number(entry[1]) > 0 ? Number(entry[1]) : null
})
const raceTrackImage = computed(() => trackImageFromConfig(raceAssetConfig.value, race.value?.track, race.value?.track_id))
const raceTrackImageCrop = computed(() => trackImageCropFromConfig(raceAssetConfig.value, race.value?.track, race.value?.track_id))
const raceTrackImageStyle = computed(() => ({
  objectPosition: `${raceTrackImageCrop.value.x}% ${raceTrackImageCrop.value.y}%`,
  transformOrigin: `${raceTrackImageCrop.value.x}% ${raceTrackImageCrop.value.y}%`,
  transform: `scale(${raceTrackImageCrop.value.zoom})`
}))

const raceRatingGame = computed(() => race.value?.game || 'ACC')
const participants = computed(() => race.value?.registered_pilots || [])
const teamRegistrations = computed(() => race.value?.team_registrations || [])
const visibleParticipants = computed(() => sortPilots(filterPilots(participants.value, participantSearch.value), participantSort.value, raceRatingGame.value))
const participantTotalPages = computed(() => Math.max(1, Math.ceil(visibleParticipants.value.length / participantPageSize)))
const pagedParticipants = computed(() => visibleParticipants.value.slice((participantPage.value - 1) * participantPageSize, participantPage.value * participantPageSize))
const registered = computed(() => participants.value.some((item) => item.user_id === state.user?.id))
const myTeamRegistration = computed(() => teamRegistrations.value.find((item) => item.team_id === state.user?.team_id) || null)
const teamRegistered = computed(() => Boolean(myTeamRegistration.value))
const teamRegistrationDrivers = computed(() => myTeamRegistration.value?.drivers || [])
const canManageTeamRegistration = computed(() => Boolean(race.value?.is_team_event && myTeam.value?.is_owner))
const canManageRace = computed(() => ['admin', 'moder'].includes(state.user?.role))
const canForcePilotRegistration = computed(() => canManageRace.value && state.user?.role === 'admin' && Boolean(race.value) && !race.value.is_team_event && !['ongoing', 'finished'].includes(race.value.status))
const canRemovePilotRegistration = computed(() => canManageRace.value && Boolean(race.value) && !race.value.is_team_event && !['ongoing', 'finished'].includes(race.value.status))
const canIssuePenalty = computed(() => ['admin', 'moder', 'marshall'].includes(state.user?.role) && ['ongoing', 'finished'].includes(race.value?.status))
const isChampionshipStage = computed(() => Boolean(race.value?.championship_id))
const isLmuRace = computed(() => race.value?.game === 'LMU')
const lmuResultsOpen = computed(() => !isLmuRace.value || race.value?.status === 'finished' || Boolean(race.value?.results) || !race.value?.lmu_results_at || new Date(race.value.lmu_results_at).getTime() <= Date.now())
const usesSimulatorJsonResults = computed(() => race.value?.game === 'ACC')
// Staff can replace a saved result set as well as enter the first one. The
// backend restores the previous rating/SR bonus before recalculating it.
const canEditManualResults = computed(() => canManageRace.value && Boolean(race.value))
const canShowRegistrationPanel = computed(() => Boolean(state.user) && (race.value?.status === 'registration_open' || (isChampionshipStage.value && race.value?.status === 'not_started')))
const rawResultRows = computed(() => {
  if (Array.isArray(race.value?.results)) return race.value.results
  return race.value?.results?.rows || []
})
function resultRowIsExcluded(row) {
  if (row?.exclude_from_rer === true) return true
  const userId = Number(row?.user_id)
  if (!Number.isInteger(userId) || userId <= 0) return false
  return participants.value.find((item) => Number(item.user_id) === userId)?.exclude_from_rer === true
}

function visibleResultRows(rows) {
  return rows
    .filter((row) => !resultRowIsExcluded(row))
    .map((row, index) => ({ ...row, position: index + 1 }))
}

const resultRows = computed(() => visibleResultRows(rawResultRows.value))
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
        game_ratings: row.game_ratings || participant?.game_ratings,
        exclude_from_rer: participant?.exclude_from_rer ?? row.exclude_from_rer ?? false,
        sr: row.sr ?? participant?.sr,
        car_model: row.car_model ?? participant?.car_model,
        team_id: row.team_id || participant?.team_id,
        team_name: row.team_name || participant?.team_name,
        team_abbreviation: row.team_abbreviation || participant?.team_abbreviation,
        country: row.country || participant?.country,
        pilot_roles: row.pilot_roles || participant?.pilot_roles || []
      }
    })
})
const penaltyParticipants = computed(() => resultParticipants.value.length ? resultParticipants.value : participants.value)
const raceRowsByPlayer = computed(() => {
  const rows = new Map()
  rawResultRows.value.forEach((row) => {
    const key = normalizeAccPlayerId(row.player_id)
    if (key) rows.set(key, row)
  })
  return rows
})
const raceRowsByNumber = computed(() => {
  const rows = new Map()
  rawResultRows.value.forEach((row) => {
    const key = Number(row.race_number)
    if (Number.isFinite(key)) rows.set(key, row)
  })
  return rows
})
const qualificationRows = computed(() => {
  const lines = race.value?.results?.qualification?.raw?.sessionResult?.leaderBoardLines
  if (!Array.isArray(lines)) {
    const manualRows = resultRows.value
      .filter((row) => Number.isFinite(Number(row.qualification_best_lap_ms)))
      .sort((left, right) => Number(left.qualification_position || 9999) - Number(right.qualification_position || 9999))
      .map((row, index) => ({ ...row, position: row.qualification_position || index + 1, best_lap_ms: row.qualification_best_lap_ms, source: 'qualification' }))
    return manualRows
  }
  const mapped = lines.map((line, index) => {
    const driver = accLineDriver(line)
    const playerId = accPlayerId(driver.playerId || driver.playerID)
    const normalized = normalizeAccPlayerId(playerId)
    // Steam/player IDs are intentionally redacted from the browser response.
    // ACC race numbers provide the safe fallback link to the stored result.
    const raceNumber = Number(line.car?.raceNumber)
    const raceRow = raceRowsByPlayer.value.get(normalized) || raceRowsByNumber.value.get(raceNumber)
    const participant = raceRow?.user_id
      ? participants.value.find((item) => item.user_id === raceRow.user_id)
      : participants.value.find((item) => Number(item.pilot_number) === raceNumber)
    const timing = line.timing || {}
    return {
      position: index + 1,
      user_id: participant?.user_id || raceRow?.user_id || null,
      login: participant?.login || raceRow?.login || null,
      nickname: participant?.nickname || raceRow?.nickname || null,
      avatar_color: participant?.avatar_color || raceRow?.avatar_color || '#2563eb',
      avatar_url: participant?.avatar_url || raceRow?.avatar_url || '',
      rating: participant?.rating ?? raceRow?.rating,
      exclude_from_rer: participant?.exclude_from_rer ?? raceRow?.exclude_from_rer ?? false,
      sr: participant?.sr ?? raceRow?.sr,
      team_id: participant?.team_id || raceRow?.team_id,
      team_name: participant?.team_name || raceRow?.team_name,
      team_abbreviation: participant?.team_abbreviation || raceRow?.team_abbreviation,
      driver_name: accDriverName(driver),
      player_id: null,
      race_number: line.car?.raceNumber ?? raceRow?.race_number ?? null,
      car_model: line.car?.carModel ?? line.carModel ?? line.forcedCarModel ?? raceRow?.car_model ?? null,
      lap_count: timing.lapCount ?? null,
      best_lap_ms: timing.bestLap,
      source: 'qualification'
    }
  })
  return visibleResultRows(mapped)
})
const raceOverviewFacts = computed(() => {
  const currentRace = race.value
  if (!currentRace) return []
  const count = currentRace.is_team_event ? teamRegistrations.value.length : participants.value.length
  const capacity = Number(currentRace.max_pilots)
  return [
    { key: 'registrationStart', label: t('fields.registrationStart'), value: formatDate(currentRace.registration_start) },
    { key: 'registrationEnd', label: t('fields.registrationEnd'), value: formatDate(currentRace.datetime_end) },
    ...(!isLmuRace.value ? [{
      key: 'participants',
      label: currentRace.is_team_event ? t('raceDetails.teams') : t('raceDetails.participants'),
      value: `${count} / ${Number.isFinite(capacity) ? capacity : '—'}`
    }] : []),
    {
      key: 'sessionTimes',
      label: t('raceDetails.sessionDistribution'),
      sessions: [
        { key: 'practice', label: t('raceDetails.practice'), value: formatSessionTime(currentRace.practice_start_time, currentRace.practice_end_time) },
        { key: 'qualification', label: t('fields.qualification'), value: formatSessionTime(currentRace.qualification_start_time, currentRace.qualification_end_time) },
        { key: 'race', label: t('raceDetails.raceSession'), value: formatSessionTime(currentRace.race_session_start_time, currentRace.race_session_end_time) }
      ]
    }
  ]
})
const activeResultRows = computed(() => (resultsTab.value === 'qualification' ? qualificationRows.value : resultRows.value))
const podiumRows = computed(() => {
  if (resultsTab.value === 'qualification' && qualificationRows.value.length) return qualificationRows.value
  return resultRows.value.length ? resultRows.value : qualificationRows.value
})
const podiumUsesQualification = computed(() => resultsTab.value === 'qualification' || resultRows.value.length === 0)
const resultTabItems = computed(() => [
  { id: 'race', label: t('raceDetails.raceResultsTab'), count: resultRows.value.length },
  ...(qualificationRows.value.length && !isLmuRace.value ? [{ id: 'qualification', label: t('raceDetails.qualificationResultsTab'), count: qualificationRows.value.length }] : []),
  { id: 'information', label: t('raceDetails.informationTab'), count: null }
])
const raceOperationalTabItems = computed(() => {
  if (!race.value || race.value.status !== 'ongoing') return []
  if (race.value.status === 'ongoing') {
    return [
      { id: 'session', label: t('raceDetails.sessionTab'), count: null },
      { id: 'information', label: t('raceDetails.eventInfoTab'), count: null }
    ]
  }
  return []
})
const showRaceParticipants = computed(() => !isLmuRace.value)
const fanVoteOptions = computed(() => fanVote.value?.options || [])
const fanVoteCandidates = computed(() => {
  const candidates = new Map()
  for (const item of participants.value) {
    const id = Number(item.user_id)
    if (Number.isInteger(id) && id > 0) candidates.set(id, item)
  }
  for (const item of resultParticipants.value) {
    const id = Number(item.user_id)
    if (Number.isInteger(id) && id > 0 && !candidates.has(id)) candidates.set(id, item)
  }
  return [...candidates.values()]
})
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

function raceFactPanelId(key) {
  return `race-overview-${race.value?.id || 'race'}-${key}`
}

function formatSessionTime(start, end) {
  return formatTimeRangeInTimeZone(start, end, race.value?.datetime_start)
}

function toggleRaceFact(key) {
  collapsedRaceFacts.value[key] = !collapsedRaceFacts.value[key]
}

const weatherKeys = ['clear', 'partly_cloudy', 'overcast', 'light_rain', 'heavy_rain', 'storm']
const weatherIcons = {
  clear: Sun,
  partly_cloudy: CloudSun,
  overcast: Cloud,
  light_rain: CloudDrizzle,
  heavy_rain: CloudRain,
  storm: CloudLightning
}
const forecastWeatherKey = computed(() => weatherKeys
  .map((key) => ({ key, chance: Number(race.value?.weather_chances?.[key]) }))
  .filter((item) => Number.isFinite(item.chance) && item.chance > 0)
  .sort((left, right) => right.chance - left.chance)[0]?.key || null)
const forecastWeatherIcon = computed(() => weatherIcons[forecastWeatherKey.value] || Cloud)

function weatherLabel(key) {
  return t(`weather.${key === 'partly_cloudy' ? 'partlyCloudy' : key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())}`)
}

function weatherChance(currentRace, key) {
  const chance = Number(currentRace?.weather_chances?.[key])
  return Number.isFinite(chance) ? `${Math.round(chance)}%` : '0%'
}

function weatherSummary(currentRace) {
  return weatherKeys
    .map((key) => `${weatherLabel(key)} ${Math.round(Number(currentRace?.weather_chances?.[key] || 0))}%`)
    .join(' · ')
}

function weatherTemperature(currentRace) {
  const temperature = Number(currentRace?.track_temperature)
  return Number.isFinite(temperature) ? `${temperature.toFixed(1)} °C` : t('common.none')
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

function resultBestLapMs(row) {
  return row?.best_lap_ms ?? row?.bestLap ?? row?.timing?.bestLap ?? null
}

function resultFinishMs(row) {
  return row?.adjusted_finish_ms ?? row?.finish_ms ?? row?.totalTime ?? row?.timing?.totalTime ?? null
}

function isAccMaxTime(value) {
  const number = Number(value)
  return Number.isFinite(number) && (ACC_MAX_TIME_ALIASES.has(number) || number >= ACC_MAX_TIME_MS)
}

function resultIsDidNotFinish(row, value) {
  return Boolean(
    race.value?.game === 'ACC'
    && (isAccMaxTime(value) || row?.status === 'missing' || row?.status === 'dnf')
  )
}

function resultTimeLabel(row, value) {
  if (resultIsDidNotFinish(row, value)) return t('raceDetails.didNotFinish')
  return formatDuration(value)
}

function resultBestLapLabel(row) {
  return resultTimeLabel(row, resultBestLapMs(row))
}

function resultQualificationBestLapMs(row) {
  return row?.qualification_best_lap_ms ?? row?.qualificationBestLapMs ?? null
}

function resultQualificationBestLapLabel(row) {
  return resultTimeLabel(row, resultQualificationBestLapMs(row))
}

function resultFinishLabel(row) {
  return resultTimeLabel(row, resultFinishMs(row))
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

function participantHref(item) {
  const userId = Number(item?.user_id || item?.id)
  return Number.isInteger(userId) && userId > 0 ? `/pilots/${userId}` : ''
}

function isCurrentUser(userId) {
  return Number(userId) === Number(state.user?.id)
}

function teamIncludesCurrentUser(team) {
  return (team?.drivers || []).some((driver) => isCurrentUser(driver.user_id))
}

function modHref(value) {
  const raw = String(value || '').trim()
  if (!raw) return '#'
  if (/^https?:\/\//i.test(raw)) return raw
  if (/^\/\//.test(raw)) return `https:${raw}`
  return `https://${raw}`
}

function fanVotePilotName(item) {
  const fullName = [item.first_name, item.last_name].filter(Boolean).join(' ')
  return fullName || item.nickname || item.login || `${t('roles.pilot')} ${item.user_id}`
}

function fanVotePilotSubtitle(item) {
  const team = teamShortName(item.team_name, item.team_abbreviation)
  const number = item.pilot_number !== null && item.pilot_number !== undefined ? `#${formatPilotNumber(item.pilot_number)}` : `ID ${item.user_id}`
  const rer = formatRating(ratingForGame(item, raceRatingGame.value))
  return [number, `RER ${rer}`, `SR ${item.sr ?? '-'}`, team].filter(Boolean).join(' - ')
}

function pilotNumberDraft(value) {
  const number = Number(value)
  return Number.isInteger(number) && number > 0 ? formatPilotNumber(number) : ''
}

function trackAssetValue(config, key, track, trackId = '') {
  const trackName = String(track || '').trim()
  const currentTrackName = (trackId && Object.entries(config?.track_ids || {}).find(([, id]) => String(id) === String(trackId))?.[0]) || trackName
  const assets = config?.[key] || {}
  const assetKey = Object.keys(assets).find((name) => name.toLowerCase() === currentTrackName.toLowerCase())
  return assetKey ? assets[assetKey] : null
}

function trackImageFromConfig(config, track, trackId = '') {
  return trackAssetValue(config, 'track_images', track, trackId) || ''
}

function trackImageCropFromConfig(config, track, trackId = '') {
  return trackAssetValue(config, 'track_image_crops', track, trackId) || { zoom: 1, x: 50, y: 50 }
}

function carModelLabel(value) {
  if (value === null || value === undefined || value === '') return t('common.none')
  if (race.value?.game !== 'ACC') return String(value)
  const numericId = Number(value)
  if (!Number.isInteger(numericId)) return String(value)
  const mapping = raceAssets.value.car_model_ids || {}
  return Object.entries(mapping).find(([, id]) => Number(id) === numericId)?.[0] || String(value)
}

function openTrackImage() {
  if (raceTrackImage.value) trackImageOpen.value = true
}

function closeTrackImage() {
  trackImageOpen.value = false
}

function openTrackImageCropper() {
  if (!raceTrackImage.value) return
  const rect = trackImageDisplay.value?.getBoundingClientRect()
  if (rect?.width && rect?.height) {
    trackImageCropTarget.value = { width: Math.round(rect.width), height: Math.round(rect.height) }
  }
  trackImageCropError.value = ''
  trackImageCropOpen.value = true
}

function closeTrackImageCropper() {
  trackImageCropOpen.value = false
  trackImageCropError.value = ''
}

async function saveTrackImageCrop(crop) {
  if (!race.value) return
  actionPending.value = true
  trackImageCropError.value = ''
  try {
    raceAssets.value = await api('/race-assets/track-image/crop', {
      method: 'PATCH',
      body: { game: race.value.game, track: race.value.track, ...crop }
    })
    closeTrackImageCropper()
  } catch (err) {
    trackImageCropError.value = err.message
  } finally {
    actionPending.value = false
  }
}

function handleKeydown(event) {
  if (event.key === 'Escape') closeTrackImage()
}

function parsePilotNumber(value) {
  const raw = String(value ?? '').trim()
  if (!/^[0-9]{3}$/.test(raw) || raw === '000') throw new Error(t('raceDetails.invalidRacePilotNumber'))
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

function resultPilotRoles(row) {
  return participantById(row.user_id)?.pilot_roles || row.pilot_roles || participants.value.find((item) => item.user_id === row.user_id)?.pilot_roles || []
}

function resultPilotUser(row) {
  const participant = participantById(row.user_id) || participants.value.find((item) => item.user_id === row.user_id)
  return {
    ...(participant || {}),
    ...row,
    exclude_from_rer: participant?.exclude_from_rer ?? row.exclude_from_rer ?? false
  }
}

function resultPilotId(row) {
  const userId = Number(row?.user_id)
  return Number.isInteger(userId) && userId > 0 ? userId : null
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

function resultPilotRatingValue(row) {
  const pilot = resultPilotUser(row)
  return row.rating_new ?? ratingForGame(pilot, raceRatingGame.value)
}

function resultPilotRating(row) {
  return formatRating(resultPilotRatingValue(row))
}

function resultPenalty(row) {
  const penalty = Number(row.time_penalty_ms || 0)
  return penalty > 0 ? `+${formatDuration(penalty)}` : '-'
}

function resultSrPenalty(row) {
  const penalty = Number(row.sr_penalty || 0)
  return penalty > 0 ? `-${penalty.toFixed(1)} SR` : '-'
}

function resultPenaltyId(row) {
  const targetId = Number(row.user_id)
  if (!Number.isFinite(targetId)) return null
  return penalties.value.find((penalty) => Number(penalty.target_id) === targetId && penalty.status !== 'canceled')?.id || null
}

async function openResultPenalty(row) {
  if (!state.user || !race.value) return
  if (!penalties.value.length) {
    try {
      penalties.value = await api(`/penalties?race_id=${race.value.id}`)
    } catch (err) {
      error.value = err.message
      return
    }
  }
  focusedPenaltyId.value = resultPenaltyId(row)
  penaltiesOpen.value = true
  penaltyCreateOpen.value = false
}

function resultRatingDelta(row) {
  if (resultPilotUser(row).exclude_from_rer) return '-'
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

function pilotTeamChip(item) {
  return teamShortName(item?.team_name, item?.team_abbreviation)
}

function openPenaltyCreator() {
  penaltiesOpen.value = true
  penaltyCreateOpen.value = true
}

function closePenaltiesModal() {
  penaltiesOpen.value = false
  focusedPenaltyId.value = null
  penaltyCreateOpen.value = false
}

function manualRowFromPilot(item, existing = {}) {
  const userId = item.user_id ?? item.id
  const pilot = { ...item, user_id: userId }
  return {
    user_id: userId,
    label: participantName(pilot),
    rating: pilot.rating,
    game_ratings: pilot.game_ratings,
    qualification_best_lap_time: existing.qualification_best_lap_ms ? formatDuration(existing.qualification_best_lap_ms) : '',
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
    const params = new URLSearchParams({ search: manualPilotSearch.value, limit: '12', rating_game: raceRatingGame.value })
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

async function loadTrackAverageLap(currentRace) {
  trackAverageLapMs.value = null
  if (!currentRace?.track) return
  try {
    const params = new URLSearchParams({ game: currentRace.game || 'ACC', track: currentRace.track })
    if (currentRace.track_id) params.set('track_id', currentRace.track_id)
    const stats = await api(`/races/track-stats?${params.toString()}`)
    trackAverageLapMs.value = stats.average_lap_ms
  } catch {
    trackAverageLapMs.value = null
  }
}

function teamMemberName(member) {
  return participantName({ ...member, user_id: member.id })
}

function isTeamDriverSelected(userId) {
  return teamDriverIds.value.includes(Number(userId))
}

function toggleTeamDriver(userId) {
  const id = Number(userId)
  if (isTeamDriverSelected(id)) {
    teamDriverIds.value = teamDriverIds.value.filter((item) => item !== id)
  } else {
    teamDriverIds.value = [...teamDriverIds.value, id]
  }
}

function moveTeamDriver(userId, direction) {
  const id = Number(userId)
  const index = teamDriverIds.value.indexOf(id)
  const nextIndex = index + direction
  if (index < 0 || nextIndex < 0 || nextIndex >= teamDriverIds.value.length) return
  const next = [...teamDriverIds.value]
  ;[next[index], next[nextIndex]] = [next[nextIndex], next[index]]
  teamDriverIds.value = next
}

function selectedTeamDriverMembers() {
  const members = new Map((myTeam.value?.members || []).map((member) => [member.id, member]))
  return teamDriverIds.value.map((id) => members.get(id)).filter(Boolean)
}

function selectedForcePilot() {
  return forcePilotCandidates.value.find((pilot) => Number(pilot.id) === Number(forcePilotId.value)) || null
}

function updateForcePilotDefaults() {
  const pilot = selectedForcePilot()
  forcePilotNumber.value = pilot ? pilotNumberDraft(pilot.pilot_number) : ''
  forcePilotCar.value = race.value?.allowed_cars?.[0] || ''
}

async function loadForcePilotCandidates(currentRace, search = forcePilotSearch.value) {
  const requestId = ++forcePilotSearchRequest
  forcePilotCandidates.value = []
  forcePilotId.value = ''
  forcePilotNumber.value = ''
  forcePilotCar.value = currentRace?.allowed_cars?.[0] || ''
  if (state.user?.role !== 'admin' || currentRace?.is_team_event || ['ongoing', 'finished'].includes(currentRace?.status)) return
  forcePilotLoading.value = true
  try {
    const params = new URLSearchParams({ limit: '100', rating_game: currentRace.game || 'ACC' })
    if (String(search || '').trim()) params.set('search', String(search).trim())
    const candidates = await api(`/users/pilots?${params.toString()}`)
    if (requestId === forcePilotSearchRequest) forcePilotCandidates.value = candidates
  } catch {
    if (requestId === forcePilotSearchRequest) forcePilotCandidates.value = []
  } finally {
    if (requestId === forcePilotSearchRequest) forcePilotLoading.value = false
  }
}

async function forceRegisterPilot() {
  if (!race.value || !canForcePilotRegistration.value) return
  error.value = ''
  actionPending.value = true
  try {
    if (!forcePilotId.value) throw new Error(t('raceDetails.forceRegistrationPilotRequired'))
    const raceId = race.value.id
    await api(`/races/${raceId}/registrations/${Number(forcePilotId.value)}`, {
      method: 'POST',
      body: {
        car_model: forcePilotCar.value || race.value.allowed_cars?.[0] || 'TBD',
        pilot_number: parsePilotNumber(forcePilotNumber.value)
      }
    })
    // Refresh the race payload so the participant list updates immediately,
    // even when a proxy serves a response without the expanded registrations.
    race.value = await api(`/races/${raceId}`)
    forcePilotId.value = ''
    forcePilotNumber.value = ''
  } catch (err) {
    error.value = err.message
  } finally {
    actionPending.value = false
  }
}

async function load() {
  try {
    const loadedRace = await api(`/races/${route.params.id}`)
    if (isExternalRace(loadedRace) && !['admin', 'moder'].includes(state.user?.role)) {
      window.location.href = loadedRace.server_link
      return
    }
    const [loadedFanVote, loadedRaceAssets] = await Promise.all([
      api(`/races/${route.params.id}/fan-vote`),
      api('/race-assets')
    ])
    race.value = loadedRace
    collapsedRaceFacts.value = {}
    weatherDetailsOpen.value = false
    raceOperationalTab.value = loadedRace.status === 'ongoing' ? 'session' : 'information'
    participantsExpanded.value = loadedRace.status !== 'finished'
    fanVote.value = loadedFanVote
    raceAssets.value = loadedRaceAssets
    await loadForcePilotCandidates(loadedRace)
    await loadTrackAverageLap(loadedRace)
    if (state.user?.team_id && loadedRace.is_team_event) {
      try {
        myTeam.value = await api(`/teams/${state.user.team_id}`)
      } catch {
        myTeam.value = null
      }
    } else {
      myTeam.value = null
    }
    syncFanVoteSelection()
    if (state.user) {
      penalties.value = await api(`/penalties?race_id=${route.params.id}`)
      appeals.value = await api('/appeals')
    }
    car.value = race.value.allowed_cars?.[0] || ''
    pilotNumber.value = pilotNumberDraft(state.user?.pilot_number)
    const existingTeamRegistration = race.value.team_registrations?.find((item) => item.team_id === state.user?.team_id)
    teamRaceNumber.value = pilotNumberDraft(existingTeamRegistration?.race_number ?? state.user?.pilot_number)
    teamDriverIds.value = existingTeamRegistration?.drivers?.map((driver) => driver.user_id) || myTeam.value?.members?.map((member) => member.id).slice(0, 2) || []
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
  error.value = ''
  try {
    if (race.value?.is_team_event) {
      await registerTeam()
      return
    }
    const body = { car_model: car.value || 'TBD' }
    if (!isChampionshipStage.value) {
      body.pilot_number = parsePilotNumber(pilotNumber.value)
    }
    race.value = await api(`/races/${race.value.id}/register`, { method: 'POST', body })
  } catch (err) {
    error.value = err.message
  }
}

async function unregister() {
  error.value = ''
  try {
    if (race.value?.is_team_event) {
      await unregisterTeam()
      return
    }
    race.value = await api(`/races/${race.value.id}/register`, { method: 'DELETE' })
  } catch (err) {
    error.value = err.message
  }
}

async function registerTeam() {
  if (!canManageTeamRegistration.value) {
    throw new Error('Зарегистрировать команду может только владелец команды')
  }
  const selectedDrivers = teamDriverIds.value.map(Number).filter(Boolean)
  if (!selectedDrivers.length) throw new Error('Выберите пилотов команды')
  race.value = await api(`/races/${race.value.id}/team-register`, {
    method: 'POST',
    body: {
      car_model: car.value || 'TBD',
      race_number: parsePilotNumber(teamRaceNumber.value),
      drivers: selectedDrivers.map((user_id) => ({ user_id }))
    }
  })
}

async function unregisterTeam() {
  race.value = await api(`/races/${race.value.id}/team-register`, { method: 'DELETE' })
}

async function removePilotRegistration(item) {
  if (!race.value || !canRemovePilotRegistration.value) return
  const name = participantName(item)
  if (!window.confirm(t('raceDetails.removePilotConfirm', { name }))) return
  error.value = ''
  actionPending.value = true
  try {
    race.value = await api(`/races/${race.value.id}/registrations/${item.user_id}`, { method: 'DELETE' })
    participantPage.value = Math.min(participantPage.value, participantTotalPages.value)
  } catch (err) {
    error.value = err.message
  } finally {
    actionPending.value = false
  }
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
        qualification_best_lap_ms: usesSimulatorJsonResults.value && race.value.has_qualification ? parseDuration(row.qualification_best_lap_time, false) : null,
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

function setTrackImage(event) {
  trackImageFile.value = event.target.files?.[0] || null
}

async function uploadTrackImage() {
  if (!race.value || !trackImageFile.value) return
  error.value = ''
  actionPending.value = true
  try {
    const body = new FormData()
    body.append('game', race.value.game)
    body.append('track', race.value.track)
    body.append('file', trackImageFile.value)
    raceAssets.value = await api('/race-assets/track-image', { method: 'POST', body })
    trackImageFile.value = null
    if (trackImageInput.value) trackImageInput.value.value = ''
  } catch (err) {
    error.value = err.message
  } finally {
    actionPending.value = false
  }
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

async function deletePenalty(penalty) {
  if (!window.confirm(t('raceDetails.confirmDeletePenalty'))) return
  error.value = ''
  actionPending.value = true
  try {
    await api(`/penalties/${penalty.id}/permanent`, { method: 'DELETE' })
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    actionPending.value = false
  }
}

function selectRaceOperationalTab(tabId) {
  raceOperationalTab.value = tabId
  if (tabId === 'participants') participantsExpanded.value = true
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  load()
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
  if (forcePilotSearchTimer) clearTimeout(forcePilotSearchTimer)
})
watch([participantSearch, participantSort], () => {
  participantPage.value = 1
})
watch(resultTabItems, (items) => {
  if (!items.some((item) => item.id === resultsTab.value)) resultsTab.value = 'race'
})
watch(raceOperationalTabItems, (items) => {
  if (!items.some((item) => item.id === raceOperationalTab.value)) raceOperationalTab.value = items[0]?.id || 'information'
})
watch(manualPilotSearch, () => {
  if (manualPilotSearch.value.trim().length >= 1) searchManualPilots()
  else manualPilotResults.value = []
})
watch(forcePilotSearch, () => {
  if (forcePilotSearchTimer) clearTimeout(forcePilotSearchTimer)
  if (!race.value || !canForcePilotRegistration.value) return
  forcePilotSearchTimer = setTimeout(() => {
    loadForcePilotCandidates(race.value, forcePilotSearch.value)
  }, 240)
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
      <nav class="race-details-breadcrumb" :aria-label="t('nav.calendar')">
        <RouterLink to="/calendar">{{ t('nav.calendar') }}</RouterLink>
        <span aria-hidden="true">/</span>
        <span>{{ race.name }}</span>
      </nav>

      <section class="card race-details-hero" :data-status="race.status">
        <div class="race-hero-main" :data-track-name="race.track">
          <div class="race-details-title">
            <span class="race-hero-kicker">{{ gameLabel(t, race.game) }} <span aria-hidden="true">·</span> {{ race.car_class }}</span>
            <div class="race-title-heading-row">
              <h1>{{ race.name }}</h1>
              <a v-if="race.status === 'registration_open'" class="button race-more-info-button" href="#race-operational-details">
                <Info :size="16" />
                {{ t('raceDetails.additionalInformation') }}
              </a>
              <button class="button primary race-penalties-button" type="button" @click="penaltiesOpen = true">
                <Scale :size="16" />
                {{ t('raceDetails.openPenalties') }}
                <span class="button-count">{{ penalties.length }}</span>
              </button>
            </div>
            <p class="race-hero-track-line">
              <RouterLink class="race-track-link" :to="{ path: '/pilots', query: { tab: 'tracks', track: race.track } }">{{ race.track }}</RouterLink>
              <span v-if="trackAverageLapMs"> · {{ t('tracks.averageLap') }}: {{ formatDuration(trackAverageLapMs) }}</span>
              <span v-if="trackExpectedAverageLapMs"> · {{ t('tracks.expectedAverageLap') }}: {{ formatDuration(trackExpectedAverageLapMs) }}</span>
            </p>
            <div class="race-hero-badges">
              <span class="status-badge race-status-badge" :class="`race-status-${race.status}`">{{ statusLabel(t, race.status) }}</span>
              <span v-if="race.is_team_event" class="status-badge race-team-badge">{{ t('raceFilters.teamBadge') }}</span>
              <span class="race-hero-chip">{{ race.has_qualification ? t('raceDetails.withQualification') : t('raceDetails.withoutQualification') }}</span>
              <span class="race-hero-chip">{{ race.is_official ? t('raceDetails.ratingCounted') : t('raceDetails.ratingNotCounted') }}</span>
            </div>
          </div>

          <aside class="race-hero-status">
            <span>{{ t('common.status') }}</span>
            <strong>{{ statusLabel(t, race.status) }}</strong>
          </aside>
        </div>

        <div v-if="canIssuePenalty || canManageRace" class="toolbar race-details-actions">
          <button v-if="canIssuePenalty" class="button" type="button" @click="openPenaltyCreator">
            {{ t('raceDetails.issuePenalty') }}
          </button>
          <template v-if="canManageRace">
            <RouterLink class="button" :to="`/races/${race.id}/edit`">{{ t('common.edit') }}</RouterLink>
            <button v-if="race.status !== 'finished' && race.results" class="button primary" type="button" :disabled="actionPending" @click="closeRace">{{ t('raceDetails.closeRace') }}</button>
            <button class="button danger" type="button" :disabled="actionPending" @click="deleteRace">{{ t('common.delete') }}</button>
          </template>
        </div>

        <div class="race-hero-overview" :class="{ 'weather-details-expanded': weatherDetailsOpen, 'has-two-facts': raceOverviewFacts.length === 2, 'has-four-facts': raceOverviewFacts.length === 4 }">
          <section class="race-hero-weather" :class="{ 'is-collapsed': collapsedRaceFacts.weather }">
            <button
              class="race-overview-toggle race-weather-card-toggle"
              type="button"
              :aria-expanded="!collapsedRaceFacts.weather"
              :aria-controls="raceFactPanelId('weather')"
              :aria-label="t(collapsedRaceFacts.weather ? 'raceDetails.expandRaceFact' : 'raceDetails.collapseRaceFact', { label: t('weather.title') })"
              @click="toggleRaceFact('weather')"
            >
              <component :is="forecastWeatherIcon" class="race-weather-icon" :class="`weather-${forecastWeatherKey || 'unknown'}`" :size="21" aria-hidden="true" />
              <span>{{ t('weather.title') }}</span>
              <small v-if="collapsedRaceFacts.weather" class="race-weather-collapsed-summary">
                {{ forecastWeatherKey ? weatherLabel(forecastWeatherKey) : t('common.none') }} · {{ weatherTemperature(race) }}
              </small>
              <ChevronUp v-if="!collapsedRaceFacts.weather" :size="16" />
              <ChevronDown v-else :size="16" />
            </button>
            <div :id="raceFactPanelId('weather')" v-show="!collapsedRaceFacts.weather" class="race-hero-weather-body">
              <div class="race-hero-weather-summary">
                <div class="race-weather-condition">
                  <span>{{ t('raceDetails.infoWeather') }}</span>
                  <strong>{{ forecastWeatherKey ? weatherLabel(forecastWeatherKey) : t('common.none') }}</strong>
                </div>
                <div class="race-weather-temperature">
                  <Thermometer :size="18" aria-hidden="true" />
                  <strong>{{ weatherTemperature(race) }}</strong>
                </div>
                <button
                  class="race-weather-toggle"
                  type="button"
                  :aria-expanded="weatherDetailsOpen"
                  :aria-controls="`race-weather-details-${race.id}`"
                  @click="weatherDetailsOpen = !weatherDetailsOpen"
                >
                  <span>{{ weatherDetailsOpen ? t('raceDetails.hideWeatherDetails') : t('raceDetails.weatherDetails') }}</span>
                  <ChevronUp v-if="weatherDetailsOpen" :size="16" />
                  <ChevronDown v-else :size="16" />
                </button>
              </div>
              <div :id="`race-weather-details-${race.id}`" v-show="weatherDetailsOpen" class="race-weather-details">
                <div v-for="key in weatherKeys" :key="key" class="race-weather-probability">
                  <span>{{ weatherLabel(key) }}</span>
                  <strong>{{ weatherChance(race, key) }}</strong>
                </div>
              </div>
            </div>
          </section>

          <div class="race-overview-facts">
            <article v-for="fact in raceOverviewFacts" :key="fact.key" class="race-overview-fact" :data-fact-key="fact.key" :class="{ 'is-collapsed': collapsedRaceFacts[fact.key] }">
              <button
                class="race-overview-toggle"
                type="button"
                :aria-expanded="!collapsedRaceFacts[fact.key]"
                :aria-controls="raceFactPanelId(fact.key)"
                :aria-label="t(collapsedRaceFacts[fact.key] ? 'raceDetails.expandRaceFact' : 'raceDetails.collapseRaceFact', { label: fact.label })"
                @click="toggleRaceFact(fact.key)"
              >
                <span>{{ fact.label }}</span>
                <ChevronUp v-if="!collapsedRaceFacts[fact.key]" :size="16" />
                <ChevronDown v-else :size="16" />
              </button>
              <div :id="raceFactPanelId(fact.key)" v-show="!collapsedRaceFacts[fact.key]" class="race-overview-fact-value">
                <div v-if="fact.sessions" class="race-session-fact-list">
                  <div v-for="session in fact.sessions" :key="session.key">
                    <span>{{ session.label }}</span>
                    <strong>{{ session.value }}</strong>
                  </div>
                </div>
                <strong v-else>{{ fact.value }}</strong>
              </div>
            </article>
          </div>
        </div>
      </section>

      <div
        class="race-details-layout"
        :class="{
          'has-registration': canShowRegistrationPanel,
          'has-tabs': resultRows.length || qualificationRows.length || race.status === 'finished' || race.status === 'ongoing',
          'is-lmu': isLmuRace
        }"
        :data-status="race.status"
      >
      <section class="card race-track-media" :class="{ 'has-race-video': race.status === 'finished' }">
        <div ref="trackImageDisplay" class="race-track-image-display">
          <button v-if="raceTrackImage" class="race-track-image-trigger" type="button" :aria-label="race.track" @click="openTrackImage">
            <img class="race-track-image" :src="raceTrackImage" :alt="race.track" :style="raceTrackImageStyle" />
          </button>
          <div v-else class="race-track-image-empty">
            <MapPin :size="22" />
            <span>{{ t('raceDetails.trackImageMissing') }}</span>
          </div>
        </div>
        <div class="race-track-media-copy">
          <span class="race-track-media-kicker">{{ gameLabel(t, race.game) }} · {{ race.car_class }}</span>
          <h2>{{ race.track }}</h2>
          <div class="race-track-media-stats">
            <div v-if="trackAverageLapMs">
              <span>{{ t('tracks.averageLap') }}</span>
              <strong>{{ formatDuration(trackAverageLapMs) }}</strong>
            </div>
            <div v-if="trackExpectedAverageLapMs">
              <span>{{ t('tracks.expectedAverageLap') }}</span>
              <strong>{{ formatDuration(trackExpectedAverageLapMs) }}</strong>
            </div>
            <div>
              <span>{{ t('weather.trackTemperature') }}</span>
              <strong>{{ weatherTemperature(race) }}</strong>
            </div>
          </div>
        </div>
        <section v-if="race.status === 'finished'" class="race-video-panel race-track-video-panel">
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
        <form v-if="canManageRace && race.track" class="race-track-image-control" @submit.prevent="uploadTrackImage">
          <div class="race-track-image-copy">
            <strong>{{ t('adminUsers.trackImages') }}</strong>
            <span>{{ race.track }}</span>
          </div>
          <label class="button small race-track-image-picker">
            <ImageUp :size="15" />
            {{ t('common.upload') }}
            <input ref="trackImageInput" type="file" accept="image/png,image/jpeg,image/webp,image/gif" @change="setTrackImage" />
          </label>
          <button class="button primary small" type="submit" :disabled="actionPending || !trackImageFile">
            {{ t('common.save') }}
          </button>
          <button class="button small" type="button" :disabled="actionPending || !raceTrackImage" @click="openTrackImageCropper">
            <Crop :size="15" />
            {{ t('raceDetails.adjustTrackImage') }}
          </button>
        </form>
      </section>

      <div v-if="trackImageOpen && raceTrackImage" class="banner-image-lightbox" @click.self="closeTrackImage">
        <section class="banner-image-dialog" role="dialog" aria-modal="true" :aria-label="race.track">
          <div class="banner-image-head">
            <div>
              <span class="banner-position-badge">{{ gameLabel(t, race.game) }}</span>
              <h2>{{ race.track }}</h2>
            </div>
            <button class="icon-button" type="button" :title="t('common.close')" :aria-label="t('common.close')" @click="closeTrackImage">
              <X :size="18" />
            </button>
          </div>
          <div class="banner-image-view race-track-image-viewer">
            <img :src="raceTrackImage" :alt="race.track" :style="raceTrackImageStyle" />
          </div>
        </section>
      </div>

      <ImageCropper
        v-if="trackImageCropOpen && raceTrackImage"
        :source-url="raceTrackImage"
        :title="t('raceDetails.trackImageCropTitle')"
        :hint="t('raceDetails.trackImageCropHint')"
        :target-width="trackImageCropTarget.width"
        :target-height="trackImageCropTarget.height"
        :view-mode="true"
        :initial-view="raceTrackImageCrop"
        :saving="actionPending"
        :error="trackImageCropError"
        @close="closeTrackImageCropper"
        @view="saveTrackImageCrop"
      />

      <div v-if="resultRows.length || qualificationRows.length || race.status === 'finished' || race.status === 'ongoing'" class="race-details-tabs">
      <div
        v-if="resultRows.length || qualificationRows.length || race.status === 'finished'"
        class="race-results-tabs race-results-tabs-top"
        role="tablist"
        :aria-label="t('raceDetails.results')"
      >
        <button
          v-for="tab in resultTabItems"
          :key="tab.id"
          class="tab-button"
          type="button"
          role="tab"
          :aria-selected="resultsTab === tab.id"
          :class="{ active: resultsTab === tab.id }"
          @click="resultsTab = tab.id"
        >
          <span>{{ tab.label }}</span>
          <strong v-if="tab.count !== null">{{ tab.count }}</strong>
        </button>
      </div>

      <div
        v-if="race.status === 'ongoing'"
        class="race-results-tabs race-results-tabs-top race-operational-tabs"
        role="tablist"
        :aria-label="t('raceDetails.eventInfoTab')"
      >
        <button
          v-for="tab in raceOperationalTabItems"
          :key="tab.id"
          class="tab-button"
          type="button"
          role="tab"
          :aria-selected="raceOperationalTab === tab.id"
          :class="{ active: raceOperationalTab === tab.id }"
          @click="selectRaceOperationalTab(tab.id)"
        >
          <span>{{ tab.label }}</span>
          <strong v-if="tab.count !== null">{{ tab.count }}</strong>
        </button>
      </div>
      </div>

      <div
        class="race-details-content-grid"
        :class="{
          'has-registration': canShowRegistrationPanel,
          'is-lmu': isLmuRace
        }"
        :data-status="race.status"
      >
      <section v-if="canShowRegistrationPanel" class="card race-registration-panel">
        <div v-if="race.is_team_event && teamRegistered" class="section-header">
          <div>
            <strong>Команда зарегистрирована</strong>
            <p class="muted">
              #{{ formatPilotNumber(myTeamRegistration.race_number) }} · {{ myTeamRegistration.car_model }} ·
              {{ teamRegistrationDrivers.map((driver) => participantName(driver)).join(' → ') }}
            </p>
          </div>
          <button v-if="canManageTeamRegistration" class="button danger" @click="unregister">{{ t('common.unregister') }}</button>
        </div>
        <form v-else-if="race.is_team_event" class="form" @submit.prevent="register">
          <div v-if="canManageTeamRegistration">
            <p class="muted">Заявку на командную гонку отправляет только владелец команды. Порядок ниже попадёт в ACC entrylist.</p>
          </div>
          <div v-else class="empty-row">Зарегистрировать команду может только владелец команды.</div>
          <template v-if="canManageTeamRegistration">
            <label class="field">
              <span>{{ t('common.car') }}</span>
              <select v-model="car">
                <option v-if="!race.allowed_cars?.length" value="">TBD</option>
                <option v-for="item in race.allowed_cars" :key="item">{{ item }}</option>
              </select>
            </label>
            <label class="field">
              <span>Номер машины</span>
              <input v-model="teamRaceNumber" inputmode="numeric" pattern="[0-9]{3}" minlength="3" maxlength="3" placeholder="001" required />
            </label>
            <div class="manual-results-table">
              <div class="manual-results-head">
                <span>Пилоты команды</span>
                <span>В заявке</span>
                <span>Порядок</span>
                <span></span>
              </div>
              <div v-for="member in myTeam.members" :key="member.id" class="manual-results-row">
                <span class="user-name-line"><span>{{ teamMemberName(member) }}</span><PilotRoles :roles="member.pilot_roles" /></span>
                <label class="toggle-field">
                  <input :checked="isTeamDriverSelected(member.id)" type="checkbox" @change="toggleTeamDriver(member.id)" />
                  <span>{{ isTeamDriverSelected(member.id) ? 'Да' : 'Нет' }}</span>
                </label>
                <span>{{ teamDriverIds.indexOf(member.id) + 1 || '-' }}</span>
                <span>
                  <button class="button small" type="button" :disabled="!isTeamDriverSelected(member.id)" @click="moveTeamDriver(member.id, -1)">↑</button>
                  <button class="button small" type="button" :disabled="!isTeamDriverSelected(member.id)" @click="moveTeamDriver(member.id, 1)">↓</button>
                </span>
              </div>
            </div>
            <div class="race-participant-list">
              <article v-for="member in selectedTeamDriverMembers()" :key="`selected-team-driver-${member.id}`" class="race-participant-row" :class="{ 'is-current-user': isCurrentUser(member.id) }">
                <UserAvatar class="pilot-avatar-slot" :src="member.avatar_url" :color="member.avatar_color" :label="teamMemberName(member)" />
                <div class="race-participant-main">
                  <span class="user-name-line"><strong>{{ teamMemberName(member) }}</strong><PilotRoles :roles="member.pilot_roles" /></span>
                  <span>#{{ formatPilotNumber(member.pilot_number) }}</span>
                </div>
              </article>
            </div>
            <p v-if="isChampionshipStage" class="muted">Для командного чемпионата заявка подаётся отдельно на этот этап.</p>
            <button class="button primary race-register-button" type="submit">{{ t('common.register') }}</button>
          </template>
        </form>
        <div v-else-if="registered" class="section-header">
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
            <input v-model="pilotNumber" inputmode="numeric" pattern="[0-9]{3}" minlength="3" maxlength="3" placeholder="001" required />
          </label>
          <p v-if="isChampionshipStage" class="muted">{{ t('raceDetails.championshipStageRegistrationHint') }}</p>
          <button class="button primary race-register-button" type="submit">{{ isChampionshipStage ? t('raceDetails.championshipStageRegister') : t('common.register') }}</button>
        </form>
      </section>

      <div v-if="race.status === 'finished'" class="race-main-layout">
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
                    <span class="user-name-line">
                      <strong>{{ fanVotePilotName(option) }}</strong>
                      <LicenseBadge :user="option" :game="raceRatingGame" />
                      <PilotRoles :roles="option.pilot_roles" />
                    </span>
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
                    <span class="user-name-line">
                      <span>{{ participantName(item) }}</span>
                      <LicenseBadge :user="item" :game="raceRatingGame" />
                      <PilotRoles :roles="item.pilot_roles" />
                    </span>
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

      <section v-if="showRaceParticipants" class="card race-participants-panel">
        <div class="section-header">
          <div>
            <h2>{{ race.is_team_event ? t('raceDetails.teams') : t('raceDetails.participants') }}</h2>
            <p class="muted">
              {{ race.is_team_event
                ? t('raceDetails.registeredTeams', { count: teamRegistrations.length })
                : t('raceDetails.registeredPilots', { count: participants.length }) }}
            </p>
          </div>
          <div class="toolbar">
            <span class="pill">{{ race.is_team_event ? teamRegistrations.length : `${visibleParticipants.length} / ${participants.length}` }}</span>
            <button class="icon-button" type="button" :title="participantsExpanded ? t('raceDetails.collapseParticipants') : t('raceDetails.expandParticipants')" :aria-label="participantsExpanded ? t('raceDetails.collapseParticipants') : t('raceDetails.expandParticipants')" @click="participantsExpanded = !participantsExpanded">
              <ChevronUp v-if="participantsExpanded" :size="18" />
              <ChevronDown v-else :size="18" />
            </button>
          </div>
        </div>

        <form v-if="canForcePilotRegistration" class="force-pilot-registration" @submit.prevent="forceRegisterPilot">
          <div class="force-pilot-registration-copy">
            <strong>{{ t('raceDetails.forceRegistrationTitle') }}</strong>
            <span>{{ t('raceDetails.forceRegistrationHint') }}</span>
          </div>
          <div class="force-pilot-registration-search">
            <label class="field">
              <span>{{ t('raceDetails.forceRegistrationSearch') }}</span>
              <input v-model="forcePilotSearch" type="search" :placeholder="t('raceDetails.forceRegistrationSearch')" :disabled="forcePilotLoading || actionPending" @keydown.enter.prevent />
            </label>
            <span class="pill">{{ forcePilotLoading ? t('common.loading') : forcePilotCandidates.length }}</span>
          </div>
          <div class="force-pilot-registration-fields">
            <label class="field">
              <span>{{ t('raceDetails.forceRegistrationPilot') }}</span>
              <select v-model="forcePilotId" :disabled="forcePilotLoading || actionPending" required @change="updateForcePilotDefaults">
                <option value="" disabled>{{ forcePilotLoading ? t('common.loading') : t('raceDetails.forceRegistrationPilotRequired') }}</option>
                <option v-for="pilot in forcePilotCandidates" :key="pilot.id" :value="String(pilot.id)">
                  {{ participantName(pilot) }} · #{{ formatPilotNumber(pilot.pilot_number) }}
                </option>
              </select>
            </label>
            <label class="field">
              <span>{{ t('common.car') }}</span>
              <select v-model="forcePilotCar" :disabled="actionPending">
                <option v-if="!race.allowed_cars?.length" value="">TBD</option>
                <option v-for="item in race.allowed_cars" :key="item" :value="item">{{ item }}</option>
              </select>
            </label>
            <label class="field">
              <span>{{ t('fields.pilotNumber') }}</span>
              <input v-model="forcePilotNumber" inputmode="numeric" pattern="[0-9]{3}" minlength="3" maxlength="3" placeholder="001" required :disabled="actionPending" />
            </label>
            <button class="button primary" type="submit" :disabled="actionPending || forcePilotLoading || !forcePilotId">
              {{ t('raceDetails.forceRegistrationSubmit') }}
            </button>
          </div>
        </form>

        <div v-if="participantsExpanded && !race.is_team_event" class="pilot-inline-controls">
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

        <div v-if="participantsExpanded && race.is_team_event && teamRegistrations.length" class="race-participant-list">
          <article v-for="item in teamRegistrations" :key="item.id" class="race-participant-row race-team-registration-row" :class="{ 'is-current-user': teamIncludesCurrentUser(item) }">
            <UserAvatar class="pilot-avatar-slot" :src="item.team_avatar_url" :color="item.team_avatar_color" :label="item.team_name" />
            <div class="race-participant-main">
              <strong>{{ item.team_name }} <span v-if="item.team_abbreviation">({{ item.team_abbreviation }})</span></strong>
              <span class="user-name-line"><template v-for="(driver, index) in item.drivers || []" :key="driver.user_id || index"><span>{{ participantName(driver) }}</span><LicenseBadge :user="driver" :game="raceRatingGame" /><PilotRoles :roles="driver.pilot_roles" /><span v-if="index < (item.drivers || []).length - 1"> → </span></template></span>
            </div>
            <div class="race-participant-stat">
              <span>#</span>
              <strong>{{ formatPilotNumber(item.race_number) }}</strong>
            </div>
            <div class="race-participant-car">
              <span>{{ t('common.car') }}</span>
              <strong>{{ item.car_model }}</strong>
            </div>
          </article>
        </div>

        <div v-else-if="participantsExpanded && visibleParticipants.length" class="race-participant-list">
          <article v-for="item in pagedParticipants" :key="item.user_id" class="race-participant-row" :class="{ 'has-registration-action': canRemovePilotRegistration, 'is-current-user': isCurrentUser(item.user_id) }">
            <UserAvatar class="pilot-avatar-slot" :src="item.avatar_url" :color="item.avatar_color" :label="participantName(item)" />
            <div class="race-participant-main">
              <span class="user-name-line">
                <RouterLink v-if="participantHref(item)" class="race-participant-link" :to="participantHref(item)">
                  <strong>{{ participantName(item) }}</strong>
                </RouterLink>
                <strong v-else>{{ participantName(item) }}</strong>
                <LicenseBadge :user="item" :game="raceRatingGame" />
                <PilotRoles :roles="item.pilot_roles" />
              </span>
              <span>{{ participantSubtitle(item) }} · RER {{ formatRating(ratingForGame(item, raceRatingGame)) }} · {{ pilotTeamChip(item) }}</span>
            </div>
            <div class="race-participant-stat">
              <span>SR</span>
              <strong>{{ item.sr ?? '-' }}</strong>
            </div>
            <div class="race-participant-stat">
              <span>RER</span>
                <strong>{{ formatRating(ratingForGame(item, raceRatingGame)) }}</strong>
            </div>
            <div class="race-participant-country">
              <span>{{ t('fields.country') }}</span>
              <strong>{{ countryLabel(t, item.country) }}</strong>
            </div>
            <div class="race-participant-car">
              <span>{{ t('common.car') }}</span>
              <strong>{{ item.car_model }}</strong>
            </div>
            <button
              v-if="canRemovePilotRegistration"
              class="icon-button danger-icon"
              type="button"
              :title="t('raceDetails.removePilot')"
              :aria-label="t('raceDetails.removePilot')"
              :disabled="actionPending"
              @click="removePilotRegistration(item)"
            >
              <UserMinus :size="16" />
            </button>
          </article>
        </div>

        <PaginationControls v-if="participantsExpanded && !race.is_team_event && visibleParticipants.length" v-model:page="participantPage" :page-size="participantPageSize" :total-items="visibleParticipants.length" />

        <div v-if="participantsExpanded && race.is_team_event && !teamRegistrations.length" class="empty-row">{{ t('raceDetails.noRegisteredTeams') }}</div>
        <div v-else-if="participantsExpanded && !race.is_team_event && !visibleParticipants.length" class="empty-row">{{ participants.length ? t('common.noMatches') : t('raceDetails.noRegisteredPilots') }}</div>
      </section>

      <section v-if="race.status !== 'finished'" id="race-operational-details" class="card race-operational-details">
        <div class="section-header">
          <div>
            <h2>{{ race.status === 'ongoing' && raceOperationalTab === 'session' ? t('raceDetails.sessionTab') : t('raceDetails.eventInfoTab') }}</h2>
            <p class="muted">{{ gameLabel(t, race.game) }} · {{ race.track }} · {{ race.car_class }}</p>
          </div>
        </div>
        <div class="race-operational-grid">
          <article v-if="race.status !== 'ongoing' || raceOperationalTab === 'information'">
            <span>{{ t('raceDetails.infoRaceTime') }}</span>
            <strong>{{ formatDate(race.datetime_start) }}</strong>
          </article>
          <article v-if="race.status !== 'ongoing' || raceOperationalTab === 'information'">
            <span>{{ t('raceDetails.infoRegistration') }}</span>
            <strong>{{ formatDate(race.registration_start) }} – {{ formatDate(race.datetime_end) }}</strong>
          </article>
          <article v-if="race.status !== 'ongoing' || raceOperationalTab === 'information'">
            <span>{{ t('raceDetails.infoWeather') }}</span>
            <strong>{{ weatherSummary(race) }} · {{ weatherTemperature(race) }}</strong>
          </article>
          <article v-if="race.status !== 'ongoing' || raceOperationalTab === 'information'">
            <span>{{ t('raceDetails.infoRating') }}</span>
            <strong>{{ race.is_official ? t('raceDetails.ratingCounted') : t('raceDetails.ratingNotCounted') }}</strong>
          </article>
          <article v-if="race.description" class="race-operational-description">
            <span>{{ t('raceDetails.infoDescription') }}</span>
            <strong>{{ race.description }}</strong>
          </article>
          <article>
            <span>{{ t('fields.server') }}</span>
            <a v-if="race.server_link" :href="race.server_link" target="_blank" rel="noopener noreferrer">{{ race.server_link }}</a>
            <strong v-else>{{ t('common.none') }}</strong>
          </article>
          <article class="race-operational-mods">
            <span>{{ t('fields.mods') }}</span>
            <div v-if="race.mods_pack?.length" class="race-mod-links">
              <a v-for="mod in race.mods_pack" :key="mod" :href="modHref(mod)" target="_blank" rel="noopener noreferrer">{{ mod }}</a>
            </div>
            <strong v-else>{{ t('common.none') }}</strong>
          </article>
          <article v-if="isLmuRace && race.lmu_results_at">
            <span>{{ t('raceDetails.infoLmuResults') }}</span>
            <strong>{{ formatDate(race.lmu_results_at) }}</strong>
          </article>
        </div>
      </section>

      <section v-if="resultRows.length || qualificationRows.length || canEditManualResults || race.status === 'finished'" class="card race-results-panel">
        <div class="section-header">
          <div>
            <h2>{{ t('raceDetails.results') }}</h2>
            <p v-if="canEditManualResults" class="muted">{{ usesSimulatorJsonResults && race.has_qualification ? t('raceDetails.manualAccResultsHint') : t('raceDetails.manualResultsHint') }}</p>
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

        <form v-if="canEditManualResults" class="form race-results-upload" @submit.prevent="uploadManualResults">
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
              <span class="user-name-line">
                <span>{{ participantName({ ...pilot, user_id: pilot.id }) }}</span>
                <LicenseBadge :user="pilot" :game="raceRatingGame" />
                <PilotRoles :roles="pilot.pilot_roles" />
              </span>
            <small>#{{ formatPilotNumber(pilot.pilot_number) }} - RER {{ formatRating(ratingForGame(pilot, raceRatingGame)) }}</small>
            </button>
          </div>
          <div class="manual-results-table">
            <div class="manual-results-head" :class="{ 'has-actions': isLmuRace, 'has-qualification': usesSimulatorJsonResults && race.has_qualification }">
              <span>{{ t('roles.pilot') }}</span>
              <span v-if="usesSimulatorJsonResults && race.has_qualification">{{ t('raceDetails.qualificationBestLap') }}</span>
              <span>{{ t('raceDetails.resultTime') }}</span>
              <span>{{ t('raceDetails.laps') }}</span>
              <span>{{ t('raceDetails.bestLap') }}</span>
              <span v-if="isLmuRace"></span>
            </div>
            <div v-for="row in manualRows" :key="row.user_id" class="manual-results-row" :class="{ 'has-actions': isLmuRace, 'has-qualification': usesSimulatorJsonResults && race.has_qualification }">
              <span class="user-name-line">
                <strong>{{ row.label }}</strong>
                <LicenseBadge :user="row" :game="raceRatingGame" />
              </span>
              <input v-if="usesSimulatorJsonResults && race.has_qualification" v-model="row.qualification_best_lap_time" placeholder="1:48.250" required />
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

        <div v-if="resultRows.length || qualificationRows.length || race.status === 'finished'" class="race-results-shell">
          <div v-if="podiumRows.length && resultsTab !== 'information'" class="race-results-podium">
            <article v-for="row in podiumRows.slice(0, 3)" :key="`podium-${row.user_id || row.player_id || row.position}`" class="result-podium-card" :class="resultPodiumClass(row)">
              <span class="result-position-badge" :class="resultPodiumClass(row)">{{ row.position || '-' }}</span>
              <div class="result-podium-driver">
                <span class="user-name-line">
                  <RouterLink v-if="resultPilotId(row)" class="result-pilot-link" :to="`/pilots/${resultPilotId(row)}`">
                    <strong>{{ resultPilotName(row) }}</strong>
                  </RouterLink>
                  <strong v-else>{{ resultPilotName(row) }}</strong>
                  <LicenseBadge :user="resultPilotUser(row)" :game="raceRatingGame" />
                  <PilotRoles :roles="resultPilotRoles(row)" />
                </span>
                <span>{{ resultPilotSubtitle(row) }}</span>
              </div>
              <div class="result-podium-times">
                <strong class="result-podium-time">{{ podiumUsesQualification ? resultBestLapLabel(row) : resultFinishLabel(row) }}</strong>
                <span v-if="!podiumUsesQualification" class="result-podium-best-lap">
                  <span class="result-podium-best-lap-label">{{ t('raceDetails.bestLap') }}</span>
                  <strong>{{ resultBestLapLabel(row) }}</strong>
                </span>
                <span v-if="!podiumUsesQualification && Number.isFinite(Number(resultQualificationBestLapMs(row)))" class="result-podium-best-lap">
                  <span class="result-podium-best-lap-label">{{ t('raceDetails.qualificationBestLap') }}</span>
                  <strong>{{ resultQualificationBestLapLabel(row) }}</strong>
                </span>
              </div>
              <span v-if="!podiumUsesQualification" class="result-podium-rating-line">
                <span class="result-podium-rating-label">{{ t('raceDetails.ratingDelta') }}</span>
                <span class="rating-delta" :class="resultRatingDeltaClass(row)">{{ resultRatingDelta(row) }}</span>
              </span>
            </article>
          </div>

          <div v-if="resultsTab === 'information'" class="race-results-info-grid">
            <article>
              <span>{{ t('raceDetails.infoSimulator') }}</span>
              <strong>{{ gameLabel(t, race.game) }}</strong>
            </article>
            <article>
              <span>{{ t('raceDetails.infoTrackClass') }}</span>
              <strong>{{ race.track }} · {{ race.car_class }}</strong>
            </article>
            <article>
              <span>{{ t('raceDetails.infoRaceTime') }}</span>
              <strong>{{ formatDate(race.datetime_start) }}</strong>
            </article>
            <article>
              <span>{{ t('raceDetails.infoRegistration') }}</span>
              <strong>{{ formatDate(race.registration_start) }} – {{ formatDate(race.datetime_end) }}</strong>
            </article>
            <article>
              <span>{{ t('raceDetails.infoWeather') }}</span>
              <strong>{{ weatherSummary(race) }} · {{ weatherTemperature(race) }}</strong>
            </article>
            <article>
              <span>{{ t('raceDetails.infoRating') }}</span>
              <strong>{{ race.is_official ? t('raceDetails.ratingCounted') : t('raceDetails.ratingNotCounted') }}</strong>
            </article>
            <article v-if="race.description" class="race-results-info-description">
              <span>{{ t('raceDetails.infoDescription') }}</span>
              <strong>{{ race.description }}</strong>
            </article>
            <article v-if="isLmuRace && race.lmu_results_at">
              <span>{{ t('raceDetails.infoLmuResults') }}</span>
              <strong>{{ formatDate(race.lmu_results_at) }}</strong>
            </article>
            <article>
              <span>{{ t('fields.server') }}</span>
              <a v-if="race.server_link" :href="race.server_link" target="_blank" rel="noopener noreferrer">{{ race.server_link }}</a>
              <strong v-else>{{ t('common.none') }}</strong>
            </article>
            <article class="race-results-info-mods">
              <span>{{ t('fields.mods') }}</span>
              <div v-if="race.mods_pack?.length" class="race-mod-links">
                <a v-for="mod in race.mods_pack" :key="mod" :href="modHref(mod)" target="_blank" rel="noopener noreferrer">{{ mod }}</a>
              </div>
              <strong v-else>{{ t('common.none') }}</strong>
            </article>
          </div>

          <div v-else-if="activeResultRows.length > 3" class="race-results-table-wrap">
            <table class="race-results-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>{{ t('roles.pilot') }}</th>
                  <th v-if="resultsTab === 'race'">{{ t('raceDetails.laps') }}</th>
                  <th v-else>{{ t('common.car') }}</th>
                  <th>{{ t('raceDetails.bestLap') }}</th>
                  <th v-if="resultsTab === 'race' && qualificationRows.length">{{ t('raceDetails.qualificationBestLap') }}</th>
                  <th v-if="resultsTab === 'race'">{{ t('raceDetails.resultTime') }}</th>
                  <th v-if="resultsTab === 'race'">{{ t('raceDetails.timePenalty') }}</th>
                  <th v-if="resultsTab === 'race'">{{ t('raceDetails.srPenalty') }}</th>
                  <th v-if="resultsTab === 'race'">{{ t('raceDetails.adjustedTime') }}</th>
                  <th v-if="resultsTab === 'race'">{{ t('raceDetails.ratingDelta') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in activeResultRows.slice(3)" :key="`${resultsTab}-${row.user_id || row.player_id || row.raw_position}-${row.position}`" :class="resultPodiumClass(row)">
                  <td data-label="#"><span class="result-position-badge" :class="resultPodiumClass(row)">{{ row.position || '-' }}</span></td>
                  <td :data-label="t('roles.pilot')">
                    <div class="result-driver-cell">
                      <UserAvatar mini :src="resultPilotAvatar(row)" :color="resultPilotColor(row)" :label="resultPilotName(row)" />
                      <div>
                        <span class="user-name-line">
                          <RouterLink v-if="resultPilotId(row)" class="result-pilot-link" :to="`/pilots/${resultPilotId(row)}`">
                            <strong>{{ resultPilotName(row) }}</strong>
                          </RouterLink>
                          <strong v-else>{{ resultPilotName(row) }}</strong>
                          <LicenseBadge :user="resultPilotUser(row)" :game="raceRatingGame" />
                          <PilotRoles :roles="resultPilotRoles(row)" />
                        </span>
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
                  <td v-if="resultsTab === 'race'" :data-label="t('raceDetails.laps')">{{ row.lap_count ?? '-' }}</td>
                  <td v-else :data-label="t('common.car')">{{ carModelLabel(row.car_model) }}</td>
                  <td :data-label="t('raceDetails.bestLap')">{{ resultBestLapLabel(row) }}</td>
                  <td v-if="resultsTab === 'race' && qualificationRows.length" :data-label="t('raceDetails.qualificationBestLap')">{{ resultQualificationBestLapLabel(row) }}</td>
                  <td v-if="resultsTab === 'race'" :data-label="t('raceDetails.resultTime')">{{ resultFinishLabel(row) }}</td>
                  <td v-if="resultsTab === 'race'" :data-label="t('raceDetails.timePenalty')">
                    <button
                      v-if="Number(row.time_penalty_ms || 0) > 0 && state.user"
                      class="result-penalty-link"
                      type="button"
                      :aria-label="`${t('raceDetails.timePenalty')}: ${resultPenalty(row)}`"
                      @click="openResultPenalty(row)"
                    >
                      {{ resultPenalty(row) }}
                    </button>
                    <strong v-else-if="Number(row.time_penalty_ms || 0) > 0" class="result-penalty-value">{{ resultPenalty(row) }}</strong>
                    <span v-else>-</span>
                  </td>
                  <td v-if="resultsTab === 'race'" :data-label="t('raceDetails.srPenalty')">
                    <button
                      v-if="Number(row.sr_penalty || 0) > 0 && state.user"
                      class="result-penalty-link"
                      type="button"
                      :aria-label="`${t('raceDetails.srPenalty')}: ${resultSrPenalty(row)}`"
                      @click="openResultPenalty(row)"
                    >
                      {{ resultSrPenalty(row) }}
                    </button>
                    <strong v-else-if="Number(row.sr_penalty || 0) > 0" class="result-penalty-value">{{ resultSrPenalty(row) }}</strong>
                    <span v-else>-</span>
                  </td>
                  <td v-if="resultsTab === 'race'" :data-label="t('raceDetails.adjustedTime')">{{ resultTimeLabel(row, row.adjusted_finish_ms ?? row.finish_ms) }}</td>
                  <td v-if="resultsTab === 'race'" :data-label="t('raceDetails.ratingDelta')"><span class="rating-delta" :class="resultRatingDeltaClass(row)">{{ resultRatingDelta(row) }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else-if="resultsTab !== 'information' && !activeResultRows.length" class="empty-row">{{ t('raceDetails.noResults') }}</div>
        </div>
      </section>
      </div>
      </div>

      <RacePenaltyListModal
        :open="penaltiesOpen"
        :penalties="penalties"
        :appeals="appeals"
        :participants="penaltyParticipants"
        :focus-penalty-id="focusedPenaltyId"
        :game="raceRatingGame"
        :can-create="canIssuePenalty"
        :can-delete="state.user?.role === 'admin'"
        v-model:create-open="penaltyCreateOpen"
        :busy="actionPending"
        @close="closePenaltiesModal"
        @create-penalty="createPenalty"
        @create-appeal="createAppeal"
        @delete-penalty="deletePenalty"
      />
    </template>
  </section>
</template>

<style scoped>
.race-details-page {
  gap: 16px;
}

.race-details-hero {
  position: relative;
  gap: 18px;
  overflow: hidden;
  padding: 24px 26px;
  border: 1px solid #1a4d9c;
  border-radius: 20px;
  color: #f5f8ff;
  background: linear-gradient(112deg, #07172d 0%, #0b2854 64%, #123c7c 100%);
  box-shadow: 0 16px 34px rgba(4, 18, 42, 0.16);
}

.race-details-hero > * {
  position: relative;
  z-index: 1;
}

.race-details-hero .section-header {
  align-items: flex-start;
  gap: 20px;
}

.race-details-title {
  display: grid;
  gap: 9px;
}

.race-details-title h1 {
  color: #f7f9ff;
  font-size: 2.35rem;
  letter-spacing: 0;
  line-height: 1.08;
  white-space: normal;
  overflow-wrap: anywhere;
}

.race-details-title p,
.race-details-hero > p,
.race-details-hero .muted {
  color: #c6d7f1;
}

.race-details-hero .race-track-link {
  color: #e0ebff;
}

.race-details-actions {
  justify-content: flex-end;
  flex-wrap: wrap;
  max-width: 620px;
}

.race-details-meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  align-items: stretch;
  gap: 8px;
  padding-top: 14px;
  border-top: 1px solid rgba(208, 224, 250, 0.2);
  color: #d8e5fa;
}

.race-details-meta > span:not(.status-badge) {
  display: flex;
  min-width: 0;
  min-height: 38px;
  align-items: center;
  padding: 8px 10px;
  border: 1px solid rgba(208, 224, 250, 0.15);
  border-radius: 9px;
  background: rgba(3, 15, 34, 0.28);
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.race-details-meta .status-badge {
  align-self: center;
  justify-self: start;
}

.race-details-hero .race-details-weather-summary {
  padding: 10px 12px;
  border: 1px solid rgba(208, 224, 250, 0.15);
  border-radius: 8px;
  background: rgba(3, 15, 34, 0.28);
}

.race-details-hero > p:last-child {
  overflow-wrap: anywhere;
}

.race-details-hero .race-mods-line {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.race-details-hero .race-mod-links {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.race-details-hero .race-mod-links a,
.race-details-hero > p a {
  color: #d7e6ff;
  overflow-wrap: anywhere;
}

.race-track-media {
  display: grid;
  grid-template-columns: minmax(240px, 0.9fr) minmax(0, 1.1fr);
  align-items: stretch;
  gap: 0;
  overflow: hidden;
  padding: 0;
  border-radius: 16px;
}

.race-track-media .race-track-image-display {
  min-width: 0;
  min-height: 180px;
  max-height: 25vh;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  margin: 0;
  background: #07172d;
}

.race-track-media .race-track-image-trigger {
  display: flex;
  width: 100%;
  height: 100%;
  min-height: 180px;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: zoom-in;
}

.race-track-media .race-track-image {
  width: auto;
  height: auto;
  max-width: 100%;
  max-height: 25vh;
  border: 0;
  border-radius: 0;
  background: transparent;
  object-fit: contain;
}

.race-track-image-empty {
  display: grid;
  min-height: 180px;
  align-content: center;
  justify-items: center;
  gap: 8px;
  padding: 20px;
  color: #cbd9ee;
  text-align: center;
}

.race-track-media-copy {
  display: grid;
  align-content: center;
  gap: 14px;
  min-width: 0;
  padding: 20px 24px;
}

.race-track-media-kicker {
  color: var(--brand-blue);
  font-size: var(--small-text-size);
  font-weight: 900;
}

.race-track-media-copy h2 {
  margin: 0;
  font-size: 1.65rem;
  line-height: 1.15;
  overflow-wrap: anywhere;
}

.race-track-media-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(112px, 1fr));
  gap: 8px;
}

.race-track-media-stats > div {
  display: grid;
  gap: 4px;
  min-width: 0;
  padding: 9px 10px;
  border: 1px solid color-mix(in srgb, var(--brand-blue) 16%, var(--border));
  background: color-mix(in srgb, var(--brand-blue) 6%, var(--panel));
}

.race-track-media-stats span {
  color: var(--muted);
  font-size: var(--tiny-text-size);
  font-weight: 850;
}

.race-track-media-stats strong {
  min-width: 0;
  overflow-wrap: anywhere;
  font-variant-numeric: tabular-nums;
}

.race-track-media .race-track-image-control {
  grid-column: 1 / -1;
  grid-template-columns: minmax(0, 1fr) auto auto;
  margin: 0;
  border: 0;
  border-top: 1px solid var(--border);
  border-radius: 0;
  background: var(--panel);
}

.race-details-content-grid {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.race-details-content-grid[data-status='finished'] {
  grid-template-columns: minmax(0, 1fr) minmax(290px, 350px);
  grid-template-areas:
    'results video'
    'results vote'
    'participants participants';
  align-items: start;
}

.race-details-content-grid[data-status='finished'] > .race-main-layout {
  display: contents;
}

.race-details-content-grid[data-status='finished'] .race-main-column {
  grid-area: video;
  min-width: 0;
}

.race-details-content-grid[data-status='finished'] .race-vote-column {
  grid-area: vote;
  min-width: 0;
}

.race-details-content-grid[data-status='finished'] .race-results-panel {
  grid-area: results;
  min-width: 0;
}

.race-details-content-grid[data-status='finished'] .race-participants-panel {
  grid-area: participants;
  min-width: 0;
}

.race-details-content-grid[data-status='finished'] .race-video-panel,
.race-details-content-grid[data-status='finished'] .race-fan-vote-panel {
  align-content: start;
}

.race-results-shell {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.race-results-tabs {
  grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
}

.race-results-tabs .tab-button {
  min-height: 42px;
}

.race-results-info-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.race-results-info-grid article {
  display: grid;
  align-content: start;
  gap: 6px;
  min-width: 0;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--control-radius);
  background: color-mix(in srgb, var(--panel-muted) 44%, var(--panel));
}

.race-results-info-grid article > span {
  color: var(--muted);
  font-size: var(--tiny-text-size);
  font-weight: 900;
}

.race-results-info-grid article > strong {
  min-width: 0;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.race-results-info-grid .race-results-info-description {
  grid-column: 1 / -1;
}

@media (max-width: 980px) {
  .race-details-content-grid[data-status='finished'] {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas:
      'results'
      'video'
      'vote'
      'participants';
  }
}

@media (max-width: 680px) {
  .race-details-hero {
    gap: 14px;
    padding: 18px 14px;
    border-radius: 15px;
  }

  .race-details-hero .section-header {
    align-items: stretch;
  }

  .race-details-title h1 {
    font-size: 1.8rem;
  }

  .race-details-actions {
    justify-content: flex-start;
    max-width: none;
  }

  .race-details-meta {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .race-track-media {
    grid-template-columns: minmax(0, 1fr);
  }

  .race-track-media .race-track-image-display,
  .race-track-media .race-track-image-trigger {
    min-height: 140px;
  }

  .race-track-media .race-track-image-control {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px;
  }

  .race-track-image-copy {
    grid-column: 1 / -1;
  }

  .race-track-media-copy {
    padding: 16px;
  }

  .race-details-content-grid,
  .race-details-content-grid[data-status='finished'] {
    gap: 12px;
  }

  .race-results-info-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .race-results-info-grid .race-results-info-description {
    grid-column: auto;
  }
}

@media (max-width: 420px) {
  .race-details-title h1 {
    font-size: 1.55rem;
  }

  .race-details-meta {
    grid-template-columns: minmax(0, 1fr);
  }

  .race-track-media .race-track-image-control {
    grid-template-columns: minmax(0, 1fr);
  }
}

.race-details-page .race-details-hero {
  position: relative;
  display: grid;
  gap: 0;
  overflow: hidden;
  padding: 0;
  border: 1px solid #1a4d9c;
  border-radius: 18px;
  color: #f5f8ff;
  background: linear-gradient(116deg, #07172d 0%, #0b2854 68%, #123b78 100%);
  box-shadow: 0 16px 34px rgba(4, 18, 42, 0.16);
}

.race-details-page .race-details-breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  color: var(--muted);
  font-size: var(--small-text-size);
  font-weight: 800;
}

.race-details-page .race-details-breadcrumb a {
  color: var(--brand-blue);
  text-decoration: none;
}

.race-details-page .race-details-breadcrumb > span:last-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.race-details-page .race-details-hero::before {
  position: absolute;
  inset: 0 0 auto;
  height: 3px;
  background: linear-gradient(90deg, #1652d8, #6fa5ff 52%, transparent);
  content: '';
}

.race-details-page .race-hero-main {
  position: relative;
  isolation: isolate;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 275px);
  align-items: stretch;
  min-width: 0;
  overflow: hidden;
}

.race-details-page .race-hero-main::after {
  position: absolute;
  z-index: 0;
  right: 0;
  bottom: 8px;
  left: 50%;
  height: 92px;
  overflow: hidden;
  color: rgba(255, 255, 255, 0.055);
  content: attr(data-track-name);
  font-size: 88px;
  font-weight: 1000;
  line-height: 1;
  text-overflow: clip;
  text-transform: uppercase;
  white-space: nowrap;
  pointer-events: none;
}

.race-details-page .race-details-title {
  position: relative;
  z-index: 1;
  display: grid;
  align-content: center;
  gap: 9px;
  min-width: 0;
  overflow: hidden;
  padding: 24px 26px 20px;
}

.race-details-page .race-hero-kicker {
  color: #a9caff;
  font-size: var(--small-text-size);
  font-weight: 900;
}

.race-details-page .race-details-title h1 {
  max-width: 100%;
  color: #f7f9ff;
  font-size: 2.3rem;
  line-height: 1.08;
  overflow-wrap: anywhere;
  white-space: normal;
}

.race-details-page .race-title-heading-row {
  display: flex;
  min-width: 0;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 10px 14px;
}

.race-details-page .race-title-heading-row h1 {
  flex: 1 1 320px;
  min-width: 0;
  margin: 0;
}

.race-details-page .race-penalties-button {
  flex: 0 0 auto;
  white-space: nowrap;
}

.race-details-page .race-hero-track-line {
  color: #c6d7f1;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.race-details-page .race-hero-track-line .race-track-link {
  color: #e0ebff;
}

.race-details-page .race-hero-badges {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 3px;
}

.race-details-page .race-hero-chip {
  display: inline-flex;
  min-height: 27px;
  align-items: center;
  padding: 4px 10px;
  border: 1px solid rgba(205, 224, 255, 0.28);
  border-radius: 999px;
  color: #dbe8fc;
  background: rgba(255, 255, 255, 0.055);
  font-size: var(--tiny-text-size);
  font-weight: 850;
  line-height: 1.25;
}

.race-details-page .race-hero-status {
  position: relative;
  z-index: 1;
  display: grid;
  align-content: center;
  justify-items: start;
  gap: 7px;
  min-width: 0;
  padding: 22px 24px;
  border-left: 1px solid rgba(199, 219, 255, 0.2);
  background: rgba(2, 14, 39, 0.2);
}

.race-details-page .race-hero-status > span {
  color: #a9caff;
  font-size: var(--tiny-text-size);
  font-weight: 900;
  text-transform: uppercase;
}

.race-details-page .race-hero-status strong {
  color: #fff;
  font-size: 1.75rem;
  line-height: 1.1;
}

.race-details-page .race-details-actions {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  flex-wrap: wrap;
  gap: 8px;
  max-width: none;
  padding: 11px 26px;
  border-top: 1px solid rgba(199, 219, 255, 0.19);
}

.race-details-page .race-details-actions .button {
  min-height: 36px;
  padding: 7px 12px;
  border-color: rgba(190, 214, 252, 0.28);
  color: #e6efff;
  background: rgba(255, 255, 255, 0.045);
}

.race-details-page .race-details-actions .button.primary {
  border-color: #2865dd;
  color: #fff;
  background: #1652d8;
}

.race-details-page .race-details-actions .button.danger {
  border-color: rgba(251, 75, 93, 0.55);
  color: #ffd6db;
  background: rgba(179, 31, 55, 0.22);
}

.race-details-page .race-track-media {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(290px, 0.9fr);
  align-items: stretch;
  gap: 0;
  overflow: hidden;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: var(--panel);
  box-shadow: var(--shadow);
}

.race-details-page .race-track-media .race-track-image-display {
  display: flex;
  height: min(25vh, 250px);
  min-height: min(25vh, 180px);
  max-height: 25vh;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  margin: 0;
  background: #07172d;
}

.race-details-page .race-track-media .race-track-image-trigger {
  display: flex;
  width: 100%;
  height: 100%;
  min-height: 0;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: zoom-in;
}

.race-details-page .race-track-media .race-track-image {
  width: auto;
  height: auto;
  max-width: 100%;
  max-height: 25vh;
  border: 0;
  border-radius: 0;
  object-fit: contain;
}

.race-details-page .race-track-image-empty {
  display: grid;
  min-height: min(25vh, 180px);
  align-content: center;
  justify-items: center;
  gap: 8px;
  color: #cbd9ee;
}

.race-details-page .race-track-media-copy {
  display: grid;
  align-content: center;
  gap: 12px;
  min-width: 0;
  padding: 19px 22px;
}

.race-details-page .race-track-media-kicker {
  color: var(--brand-blue);
  font-size: var(--tiny-text-size);
  font-weight: 900;
}

.race-details-page .race-track-media-copy h2 {
  margin: 0;
  font-size: 1.55rem;
  line-height: 1.18;
  overflow-wrap: anywhere;
}

.race-details-page .race-track-media-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(112px, 1fr));
  gap: 8px;
}

.race-details-page .race-track-media-stats > div {
  display: grid;
  align-content: start;
  gap: 5px;
  min-width: 0;
  padding: 9px 10px;
  border: 1px solid color-mix(in srgb, var(--brand-blue) 16%, var(--border));
  border-radius: var(--control-radius);
  background: color-mix(in srgb, var(--brand-blue) 5%, var(--panel));
}

.race-details-page .race-track-media-stats span {
  color: var(--muted);
  font-size: var(--tiny-text-size);
  font-weight: 850;
}

.race-details-page .race-track-media-stats strong {
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
}

.race-details-page .race-track-media .race-track-image-control {
  grid-column: 1 / -1;
  grid-template-columns: minmax(0, 1fr) auto auto;
  margin: 0;
  border: 0;
  border-top: 1px solid var(--border);
  border-radius: 0;
  background: var(--panel);
}

.race-details-page .race-results-tabs.race-results-tabs-top {
  display: flex;
  width: fit-content;
  max-width: 100%;
  flex-wrap: wrap;
  gap: 4px;
  padding: 4px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--panel);
}

.race-details-page .race-results-tabs-top .tab-button {
  display: inline-flex;
  min-width: 126px;
  min-height: 38px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 6px 14px;
  border: 0;
  border-radius: 999px;
  color: var(--muted);
  background: transparent;
}

.race-details-page .race-results-tabs-top .tab-button.active {
  color: #fff;
  background: linear-gradient(120deg, #1652d8, #0d2f8f);
}

.race-details-page .race-results-tabs-top .tab-button.active strong {
  color: #fff;
  background: rgba(255, 255, 255, 0.18);
}

.race-details-page .race-details-content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 350px);
  grid-template-areas:
    'details participants'
    'results results';
  align-items: start;
  gap: 14px;
  min-width: 0;
}

.race-details-page .race-details-content-grid.has-registration {
  grid-template-areas:
    'registration participants'
    'details details'
    'results results';
}

.race-details-page .race-details-content-grid.is-lmu:not([data-status='finished']) {
  grid-template-columns: minmax(0, 1fr);
  grid-template-areas:
    'registration'
    'details'
    'results';
}

.race-details-page .race-details-content-grid.is-lmu:not(.has-registration):not([data-status='finished']) {
  grid-template-areas:
    'details'
    'results';
}

.race-details-page .race-details-content-grid:not([data-status='finished']) .race-registration-panel {
  grid-area: registration;
  min-width: 0;
}

.race-details-page .race-details-content-grid:not([data-status='finished']) .race-operational-details {
  grid-area: details;
  min-width: 0;
}

.race-details-page .race-details-content-grid:not([data-status='finished']) .race-participants-panel {
  grid-area: participants;
  min-width: 0;
}

.race-details-page .race-details-content-grid:not([data-status='finished']) .race-results-panel {
  grid-area: results;
  min-width: 0;
}

.race-details-page .race-details-content-grid[data-status='finished'] {
  grid-template-columns: minmax(0, 1fr) minmax(290px, 350px);
  grid-template-areas:
    'results video'
    'results vote'
    'participants participants';
}

.race-details-page .race-details-content-grid[data-status='finished'] > .race-main-layout {
  display: contents;
}

.race-details-page .race-details-content-grid[data-status='finished'] .race-main-column {
  grid-area: video;
  min-width: 0;
}

.race-details-page .race-details-content-grid[data-status='finished'] .race-vote-column {
  grid-area: vote;
  min-width: 0;
}

.race-details-page .race-details-content-grid[data-status='finished'] .race-results-panel {
  grid-area: results;
  min-width: 0;
}

.race-details-page .race-details-content-grid.is-lmu[data-status='finished'] {
  grid-template-areas:
    'results video'
    'results vote';
}

.race-details-page .race-details-content-grid[data-status='finished'] .race-participants-panel {
  grid-area: participants;
  min-width: 0;
}

.race-details-page .race-details-content-grid[data-status='finished'] .race-video-panel,
.race-details-page .race-details-content-grid[data-status='finished'] .race-fan-vote-panel {
  align-content: start;
}

.race-details-page .race-registration-panel,
.race-details-page .race-operational-details,
.race-details-page .race-participants-panel,
.race-details-page .race-video-panel,
.race-details-page .race-results-panel,
.race-details-page .race-fan-vote-panel {
  min-width: 0;
  border-radius: 14px;
}

.race-details-page .race-registration-panel,
.race-details-page .race-operational-details,
.race-details-page .race-participants-panel,
.race-details-page .race-results-panel {
  padding: 18px;
}

.race-details-page .race-operational-details > .section-header,
.race-details-page .race-results-panel > .section-header {
  align-items: flex-start;
  margin-bottom: 2px;
}

.race-details-page .race-operational-grid,
.race-details-page .race-results-info-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  min-width: 0;
}

.race-details-page .race-operational-grid article,
.race-details-page .race-results-info-grid article {
  display: grid;
  align-content: start;
  gap: 6px;
  min-width: 0;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--control-radius);
  background: color-mix(in srgb, var(--panel-muted) 44%, var(--panel));
}

.race-details-page .race-operational-grid article > span,
.race-details-page .race-results-info-grid article > span {
  color: var(--muted);
  font-size: var(--tiny-text-size);
  font-weight: 900;
}

.race-details-page .race-operational-grid article > strong,
.race-details-page .race-results-info-grid article > strong,
.race-details-page .race-operational-grid article > a,
.race-details-page .race-results-info-grid article > a {
  min-width: 0;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.race-details-page .race-operational-description,
.race-details-page .race-results-info-description,
.race-details-page .race-operational-mods,
.race-details-page .race-results-info-mods {
  grid-column: 1 / -1;
}

.race-details-page .race-mod-links {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  min-width: 0;
}

.race-details-page .race-mod-links a {
  overflow-wrap: anywhere;
}

.race-details-page .race-results-shell {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.race-details-page .race-results-panel .section-header h2 {
  font-size: 1.3rem;
}

.race-details-page .race-results-podium {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  align-items: end;
  gap: 10px;
}

.race-details-page .race-results-table-wrap {
  max-width: 100%;
  overflow-x: auto;
  overscroll-behavior-inline: contain;
}

.race-details-page .race-results-table {
  min-width: 760px;
}

.race-details-page .race-participants-panel .section-header {
  align-items: center;
}

.race-details-page .race-video-panel,
.race-details-page .race-fan-vote-panel {
  padding: 15px;
}

.race-details-page .race-video-frame video {
  display: block;
  width: 100%;
  max-height: 360px;
  border-radius: var(--control-radius);
  background: #020914;
}

@media (max-width: 1100px) {
  .race-details-page .race-details-content-grid[data-status='finished'] {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas:
      'results'
      'video'
      'vote'
      'participants';
  }

  .race-details-page .race-details-content-grid:not([data-status='finished']) {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas:
      'registration'
      'details'
      'participants'
      'results';
  }

  .race-details-page .race-details-content-grid:not([data-status='finished']):not(.has-registration) {
    grid-template-areas:
      'details'
      'participants'
      'results';
  }

  .race-details-page .race-details-content-grid:not([data-status='finished']).is-lmu.has-registration {
    grid-template-areas:
      'registration'
      'details'
      'results';
  }

  .race-details-page .race-details-content-grid:not([data-status='finished']).is-lmu:not(.has-registration) {
    grid-template-areas:
      'details'
      'results';
  }

  .race-details-page .race-details-content-grid.is-lmu[data-status='finished'] {
    grid-template-areas:
      'results'
      'video'
      'vote';
  }
}

@media (max-width: 680px) {
  .race-details-page .race-details-hero {
    border-radius: 15px;
  }

  .race-details-page .race-hero-main {
    grid-template-columns: minmax(0, 1fr);
  }

  .race-details-page .race-details-title {
    padding: 20px 16px 16px;
  }

  .race-details-page .race-details-title h1 {
    font-size: 1.75rem;
  }

  .race-details-page .race-hero-status {
    grid-template-columns: auto minmax(0, 1fr);
    align-items: center;
    gap: 5px 12px;
    padding: 12px 16px;
    border-top: 1px solid rgba(199, 219, 255, 0.2);
    border-left: 0;
  }

  .race-details-page .race-hero-status > span {
    grid-column: 1;
  }

  .race-details-page .race-hero-status strong {
    grid-column: 1;
    grid-row: 2;
    font-size: 1.25rem;
  }

  .race-details-page .race-details-actions {
    padding: 10px 14px;
  }

  .race-details-page .race-details-actions .button {
    flex: 1 1 auto;
    justify-content: center;
  }

  .race-details-page .race-track-media {
    grid-template-columns: minmax(0, 1fr);
  }

  .race-details-page .race-track-media .race-track-image-display {
    height: min(25vh, 220px);
    min-height: min(25vh, 140px);
  }

  .race-details-page .race-track-media-copy {
    gap: 10px;
    padding: 15px;
  }

  .race-details-page .race-track-media .race-track-image-control {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px;
  }

  .race-details-page .race-track-image-copy {
    grid-column: 1 / -1;
  }

  .race-details-page .race-results-tabs.race-results-tabs-top {
    width: 100%;
    justify-content: stretch;
    border-radius: 14px;
  }

  .race-details-page .race-results-tabs-top .tab-button {
    min-width: 0;
    flex: 1 1 100px;
    padding-inline: 9px;
  }

  .race-details-page .race-registration-panel,
  .race-details-page .race-operational-details,
  .race-details-page .race-participants-panel,
  .race-details-page .race-results-panel {
    padding: 14px;
  }

  .race-details-page .race-operational-grid,
  .race-details-page .race-results-info-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .race-details-page .race-operational-description,
  .race-details-page .race-results-info-description,
  .race-details-page .race-operational-mods,
  .race-details-page .race-results-info-mods {
    grid-column: auto;
  }
}

@media (max-width: 420px) {
  .race-details-page .race-details-title h1 {
    font-size: 1.55rem;
  }

  .race-details-page .race-results-podium {
    gap: 5px;
  }

  .race-details-page .race-results-podium .result-podium-card {
    padding: 9px 6px;
  }

  .race-details-page .race-track-media .race-track-image-control {
    grid-template-columns: minmax(0, 1fr);
  }
}

.race-details-page .race-hero-weather {
  padding: 10px 26px 14px;
  border-top: 1px solid rgba(199, 219, 255, 0.19);
  color: #f4f7ff;
  background: rgba(0, 0, 0, 0.1);
}

.race-details-page .race-hero-weather-summary {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 12px;
}

.race-details-page .race-weather-icon {
  flex: 0 0 auto;
  color: #f7d66b;
}

.race-details-page .race-weather-icon.weather-partly_cloudy,
.race-details-page .race-weather-icon.weather-overcast {
  color: #c9dcfa;
}

.race-details-page .race-weather-icon.weather-light_rain,
.race-details-page .race-weather-icon.weather-heavy_rain {
  color: #89caff;
}

.race-details-page .race-weather-icon.weather-storm {
  color: #ffd18a;
}

.race-details-page .race-weather-condition {
  display: grid;
  min-width: 0;
  gap: 3px;
}

.race-details-page .race-weather-condition > span {
  color: #a9c2ea;
  font-size: var(--tiny-text-size);
  font-weight: 850;
}

.race-details-page .race-weather-condition > strong {
  overflow-wrap: anywhere;
}

.race-details-page .race-weather-temperature {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: 16px;
  padding-left: 16px;
  border-left: 1px solid rgba(199, 219, 255, 0.2);
  font-variant-numeric: tabular-nums;
}

.race-details-page .race-weather-temperature svg {
  color: #a9caff;
}

.race-details-page .race-weather-toggle {
  display: inline-flex;
  min-height: 36px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-left: auto;
  padding: 7px 11px;
  border: 1px solid rgba(190, 214, 252, 0.3);
  border-radius: 9px;
  color: #e6efff;
  background: rgba(255, 255, 255, 0.05);
  cursor: pointer;
}

.race-details-page .race-weather-toggle:hover {
  border-color: #6fa5ff;
  background: rgba(255, 255, 255, 0.1);
}

.race-details-page .race-weather-details {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 7px;
  margin-top: 11px;
}

.race-details-page .race-weather-probability {
  display: grid;
  gap: 4px;
  min-width: 0;
  padding: 8px 10px;
  border: 1px solid rgba(190, 214, 252, 0.18);
  border-radius: 9px;
  background: rgba(2, 14, 39, 0.3);
}

.race-details-page .race-weather-probability > span {
  color: #c6d7f1;
  font-size: var(--tiny-text-size);
  line-height: 1.25;
  overflow-wrap: anywhere;
}

.race-details-page .race-hero-overview {
  display: grid;
  grid-template-columns: minmax(220px, 0.85fr) minmax(0, 3.4fr);
  align-items: stretch;
  gap: 10px;
  padding: 12px 20px 16px;
  border-top: 1px solid rgba(199, 219, 255, 0.19);
  color: #f4f7ff;
  background: rgba(0, 0, 0, 0.1);
}

.race-details-page .race-hero-overview.has-two-facts {
  grid-template-columns: minmax(0, 1fr) minmax(0, 2fr);
}

.race-details-page .race-hero-weather,
.race-details-page .race-overview-fact {
  min-width: 0;
  overflow: hidden;
  border: 1px solid rgba(190, 214, 252, 0.2);
  border-radius: 11px;
  background: rgba(2, 14, 39, 0.28);
}

.race-details-page .race-hero-weather {
  min-height: 92px;
  padding: 0;
  border-top: 1px solid rgba(190, 214, 252, 0.2);
}

.race-details-page .race-overview-facts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  grid-auto-rows: minmax(92px, auto);
  align-items: stretch;
  gap: 8px;
  min-width: 0;
}

.race-details-page .race-hero-overview.has-four-facts .race-overview-facts {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.race-details-page .race-hero-overview.has-two-facts .race-overview-facts {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.race-details-page .race-hero-overview.weather-details-expanded .race-overview-facts {
  align-self: start;
}

.race-details-page .race-overview-fact {
  display: flex;
  min-height: 92px;
  flex-direction: column;
}

.race-details-page .race-session-fact-list {
  display: grid;
  gap: 3px;
  width: 100%;
  min-width: 0;
  padding: 1px 10px 8px;
  font-size: 11px;
  line-height: 1.15;
}

.race-details-page .race-session-fact-list > div {
  display: flex;
  justify-content: space-between;
  gap: 6px;
  min-width: 0;
}

.race-details-page .race-session-fact-list span {
  min-width: 0;
  color: #b9d1f5;
}

.race-details-page .race-session-fact-list strong {
  flex: 0 0 auto;
  color: #f4f7ff;
  font-variant-numeric: tabular-nums;
}

.race-details-page .race-overview-toggle {
  display: flex;
  width: 100%;
  min-height: 40px;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 0;
  border-radius: inherit;
  color: #e6efff;
  background: transparent;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.race-details-page .race-overview-toggle:hover {
  background: rgba(255, 255, 255, 0.07);
}

.race-details-page .race-overview-toggle:focus-visible {
  outline: 2px solid #8bb8ff;
  outline-offset: -3px;
}

.race-details-page .race-overview-toggle > span:first-of-type {
  min-width: 0;
  color: #b9d1f5;
  font-size: var(--tiny-text-size);
  font-weight: 850;
  line-height: 1.25;
  overflow-wrap: anywhere;
}

.race-details-page .race-overview-toggle > svg:last-child {
  flex: 0 0 auto;
  margin-left: auto;
  color: #a9caff;
}

.race-details-page .race-weather-card-toggle > span:first-of-type {
  color: #f4f7ff;
}

.race-details-page .race-weather-card-toggle > .race-weather-icon {
  flex: 0 0 auto;
}

.race-details-page .race-weather-collapsed-summary {
  min-width: 0;
  margin-left: auto;
  color: #e6efff;
  font-size: var(--tiny-text-size);
  font-weight: 750;
  line-height: 1.25;
  text-align: right;
  overflow-wrap: anywhere;
}

.race-details-page .race-hero-weather-body {
  padding: 0 10px 10px;
}

.race-details-page .race-hero-weather-summary {
  flex-wrap: wrap;
  gap: 8px;
}

.race-details-page .race-weather-condition > span {
  display: none;
}

.race-details-page .race-weather-condition > strong {
  color: #f4f7ff;
  line-height: 1.3;
}

.race-details-page .race-weather-temperature {
  gap: 5px;
  margin-left: auto;
  padding-left: 9px;
  border-left: 1px solid rgba(199, 219, 255, 0.2);
  white-space: nowrap;
}

.race-details-page .race-weather-toggle {
  min-height: 32px;
  margin-left: 0;
  padding: 5px 8px;
  font-size: var(--tiny-text-size);
}

.race-details-page .race-weather-details {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  margin-top: 8px;
}

.race-details-page .race-weather-probability {
  padding: 7px;
}

.race-details-page .race-overview-fact-value {
  display: flex;
  flex: 1 1 auto;
  min-width: 0;
  min-height: 50px;
  align-items: center;
  padding: 0 10px 10px;
}

.race-details-page .race-overview-fact-value strong {
  min-width: 0;
  color: #f4f7ff;
  font-size: 0.86rem;
  line-height: 1.35;
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
}

.race-details-page .race-overview-fact.is-collapsed .race-overview-toggle {
  flex: 1 1 auto;
}

@media (max-width: 1080px) {
  .race-details-page .race-hero-overview {
    grid-template-columns: minmax(0, 1fr);
  }

  .race-details-page .race-hero-overview.has-two-facts {
    grid-template-columns: minmax(0, 1fr);
  }

  .race-details-page .race-overview-facts {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 680px) {
  .race-details-page .race-hero-overview {
    gap: 8px;
    padding: 10px 12px 14px;
  }

  .race-details-page .race-overview-facts {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 7px;
  }

  .race-details-page .race-weather-details {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 380px) {
  .race-details-page .race-overview-facts {
    grid-template-columns: minmax(0, 1fr);
  }
}

.race-details-page .race-details-content-grid:not([data-status='finished']) {
  grid-template-columns: minmax(0, 1fr);
  grid-template-areas:
    'registration'
    'participants'
    'details'
    'results';
}

.race-details-page .race-details-content-grid:not([data-status='finished']):not(.has-registration) {
  grid-template-areas:
    'details'
    'participants'
    'results';
}

.race-details-page .race-details-content-grid.is-lmu:not([data-status='finished']) {
  grid-template-areas:
    'registration'
    'details'
    'results';
}

.race-details-page .race-details-content-grid.is-lmu:not(.has-registration):not([data-status='finished']) {
  grid-template-areas:
    'details'
    'results';
}

.race-details-page .race-details-content-grid[data-status='finished'] {
  grid-template-columns: minmax(0, 1fr) minmax(300px, 360px);
  grid-template-areas:
    'results media'
    'participants participants';
  align-items: start;
}

.race-details-page .race-details-content-grid[data-status='finished'] > .race-main-layout {
  display: grid;
  grid-area: media;
  grid-template-columns: minmax(0, 1fr);
  align-content: start;
  gap: 14px;
  min-width: 0;
  width: 100%;
}

.race-details-page .race-details-content-grid[data-status='finished'] .race-main-column,
.race-details-page .race-details-content-grid[data-status='finished'] .race-vote-column {
  grid-area: auto;
  min-width: 0;
}

.race-details-page .race-details-content-grid.is-lmu[data-status='finished'] {
  grid-template-areas: 'results media';
}

.race-details-page .race-track-media {
  position: relative;
  isolation: isolate;
  grid-template-columns: minmax(0, 2.2fr) minmax(240px, 1.1fr) minmax(260px, 1.2fr);
  grid-template-rows: minmax(220px, auto) auto;
}

.race-details-page .race-track-image-display {
  position: relative;
  isolation: isolate;
}

.race-details-page .race-track-media > * {
  position: relative;
  z-index: 1;
}

.race-details-page .race-track-media:not(.has-race-video) {
  grid-template-columns: minmax(0, 1.7fr) minmax(240px, 1fr);
}

.race-details-page .race-track-media .race-track-image-display {
  display: block;
  height: 100%;
  min-height: 220px;
  max-height: none;
  margin: 0;
  overflow: hidden;
  background: #07172d;
}

.race-details-page .race-track-media .race-track-image-trigger {
  display: block;
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 220px;
  padding: 0;
  overflow: hidden;
  border: 0;
  background: #07172d;
}

.race-details-page .race-track-media .race-track-image {
  display: block;
  width: 100%;
  height: 100%;
  max-width: 100%;
  max-height: 100%;
  object-fit: cover;
  transition: transform 150ms ease;
}

.race-details-page .race-track-media .race-track-image-display::after {
  content: none;
}

.race-details-page .race-track-media .race-track-image-control {
  grid-template-columns: minmax(0, 1fr) repeat(3, auto);
}

.race-details-page .race-track-image-viewer {
  width: 100%;
  height: min(700px, calc(100dvh - 190px));
  min-height: 0;
  overflow: hidden;
  background: #07172d;
}

.race-details-page .race-track-image-viewer img {
  display: block;
  width: 100%;
  height: 100%;
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.race-details-page .race-track-video-panel {
  display: grid;
  grid-template-rows: auto minmax(132px, 1fr) auto;
  align-content: stretch;
  gap: 8px;
  min-height: 0;
  padding: 10px 12px;
  border-left: 1px solid var(--border);
  border-radius: 0;
}

.race-details-page .race-track-video-panel .section-header {
  align-items: flex-start;
  margin: 0;
}

.race-details-page .race-track-video-panel .race-video-frame {
  min-width: 0;
  height: 100%;
  min-height: 132px;
  overflow: hidden;
  background: #020914;
}

.race-details-page .race-track-video-panel .race-video-frame video {
  width: 100%;
  height: 100%;
  max-height: none;
  object-fit: contain;
}

.race-details-page .race-track-video-panel > .empty-row {
  display: grid;
  min-height: 132px;
  place-items: center;
}

.race-details-page .race-track-video-panel .race-video-upload {
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  align-items: end;
  gap: 8px;
  margin: 0;
}

@media (max-width: 900px) {
  .race-details-page .race-track-media,
  .race-details-page .race-track-media:not(.has-race-video) {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto auto auto;
  }

  .race-details-page .race-track-media .race-track-image-display {
    grid-column: 1;
    grid-row: 1;
    align-self: center;
    height: clamp(220px, 35vw, 320px);
    min-height: 220px;
  }

  .race-details-page .race-track-media .race-track-image-control {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .race-details-page .race-track-image-copy {
    grid-column: 1 / -1;
  }

  .race-details-page .race-track-media .race-track-image-trigger {
    height: 100%;
  }

  .race-details-page .race-track-media .race-track-image {
    height: 100%;
  }

  .race-details-page .race-track-media-copy {
    grid-column: 1;
    grid-row: 2;
  }

  .race-details-page .race-track-video-panel {
    grid-column: 1 / -1;
    grid-row: 3;
    min-height: 0;
    border-top: 1px solid var(--border);
    border-left: 0;
  }
}

@media (max-width: 680px) {
  .race-details-page .race-track-media {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto;
  }

  .race-details-page .race-track-media .race-track-image-display {
    height: 220px;
    min-height: 220px;
  }

  .race-details-page .race-track-image-viewer {
    width: 100%;
    height: min(620px, calc(100dvh - 190px));
  }

  .race-details-page .race-title-heading-row {
    align-items: flex-start;
  }

  .race-details-page .race-hero-main::after {
    bottom: 6px;
    height: 66px;
    font-size: 62px;
  }

  .race-details-page .race-track-video-panel {
    min-height: 0;
    grid-column: auto;
    border-top: 1px solid var(--border);
    border-left: 0;
  }
}

@media (max-width: 420px) {
  .race-details-page .race-track-media .race-track-image-control {
    grid-template-columns: minmax(0, 1fr);
  }

  .race-details-page .race-track-image-copy {
    grid-column: 1;
  }

}

@media (max-width: 1100px) {
  .race-details-page .race-details-content-grid[data-status='finished'] {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas:
      'results'
      'media'
      'participants';
  }

  .race-details-page .race-details-content-grid.is-lmu[data-status='finished'] {
    grid-template-areas:
      'results'
      'media';
  }
}

@media (max-width: 680px) {
  .race-details-page .race-hero-weather {
    padding: 10px 14px 12px;
  }

  .race-details-page .race-hero-weather-summary {
    flex-wrap: wrap;
    gap: 10px;
  }

  .race-details-page .race-weather-temperature {
    margin-left: auto;
    padding-left: 10px;
  }

  .race-details-page .race-weather-toggle {
    flex: 1 0 100%;
    margin-left: 0;
  }

  .race-details-page .race-weather-details {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .race-details-page .race-hero-status {
    grid-template-columns: minmax(0, 1fr);
  }

  .race-details-page .race-hero-status strong {
    grid-column: auto;
    grid-row: auto;
  }
}

.race-details-page .race-results-table-wrap {
  width: 100%;
  min-width: 0;
}

.race-details-page .race-results-table {
  width: 100%;
  min-width: 0;
  table-layout: fixed;
}

.race-details-page .race-results-table th,
.race-details-page .race-results-table td {
  padding: 8px 6px;
  overflow-wrap: anywhere;
  white-space: normal;
}

.race-details-page .race-results-table th:first-child,
.race-details-page .race-results-table td:first-child {
  width: 44px;
  text-align: center;
}

.race-details-page .race-results-table th:nth-child(2),
.race-details-page .race-results-table td:nth-child(2) {
  width: 210px;
}

@media (max-width: 1600px) {
  .race-details-page .race-details-content-grid[data-status='finished'] {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas:
      'results'
      'media'
      'participants';
  }

  .race-details-page .race-details-content-grid.is-lmu[data-status='finished'] {
    grid-template-areas:
      'results'
      'media';
  }
}

.race-details-page .race-details-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  grid-template-areas:
    'track'
    'tabs'
    'details'
    'participants'
    'results';
  gap: 14px;
  min-width: 0;
}

.race-details-page .race-details-layout > .race-track-media {
  grid-area: track;
}

.race-details-page .race-details-tabs {
  display: grid;
  grid-area: tabs;
  gap: 10px;
  min-width: 0;
}

.race-details-page .race-details-content-grid:not([data-status='finished']) {
  display: contents;
}

.race-details-page .race-details-content-grid[data-status='finished'] {
  grid-area: content;
}

.race-details-page .race-details-layout.has-registration:not([data-status='finished']) {
  grid-template-areas:
    'registration'
    'track'
    'tabs'
    'participants'
    'details'
    'results';
}

.race-details-page .race-details-layout:not([data-status='finished']):not(.has-tabs) {
  grid-template-areas:
    'track'
    'details'
    'participants'
    'results';
}

.race-details-page .race-details-layout.has-registration:not([data-status='finished']):not(.has-tabs) {
  grid-template-areas:
    'registration'
    'track'
    'participants'
    'details'
    'results';
}

.race-details-page .race-details-layout.is-lmu:not([data-status='finished']) {
  grid-template-areas:
    'track'
    'tabs'
    'details'
    'results';
}

.race-details-page .race-details-layout.is-lmu.has-registration:not([data-status='finished']) {
  grid-template-areas:
    'registration'
    'track'
    'tabs'
    'details'
    'results';
}

.race-details-page .race-details-layout.is-lmu:not([data-status='finished']):not(.has-tabs) {
  grid-template-areas:
    'track'
    'details'
    'results';
}

.race-details-page .race-details-layout.is-lmu.has-registration:not([data-status='finished']):not(.has-tabs) {
  grid-template-areas:
    'registration'
    'track'
    'details'
    'results';
}

.race-details-page .race-details-layout[data-status='finished'] {
  grid-template-areas:
    'track'
    'tabs'
    'content';
}

.race-details-page .race-operational-details {
  scroll-margin-top: calc(var(--topbar-height) + 16px);
}

.race-details-page .race-registration-panel .button.primary.race-register-button {
  border-color: #087a46;
  color: #fff;
  background: #087a46;
  box-shadow: 0 8px 18px rgba(8, 122, 70, 0.2);
}

.race-details-page .race-registration-panel .button.primary.race-register-button:hover:not(:disabled) {
  border-color: #075f3b;
  background: #075f3b;
}

.race-details-page .race-participant-row.is-current-user,
.race-details-page .race-participant-row.is-current-user:hover {
  border-color: color-mix(in srgb, var(--brand-blue) 54%, var(--border));
  background:
    linear-gradient(90deg, color-mix(in srgb, var(--brand-blue) 12%, transparent), transparent 72%),
    var(--panel);
  box-shadow: inset 3px 0 0 var(--brand-blue);
}

@media (min-width: 681px) {
  .race-details-page .race-results-podium .result-podium-card {
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 8px;
    height: auto;
    min-height: 200px;
    padding: 10px 12px;
  }

  .race-details-page .race-results-podium .result-podium-card.is-silver {
    grid-column: 1;
    align-self: end;
    min-height: 235px;
  }

  .race-details-page .race-results-podium .result-podium-card.is-gold {
    grid-column: 2;
    align-self: end;
    min-height: 285px;
  }

  .race-details-page .race-results-podium .result-podium-card.is-bronze {
    grid-column: 3;
    align-self: end;
    min-height: 200px;
  }
}
</style>
