<script setup>
// Race page (/races/:id): cinematic hero, registration, entry list, results,
// briefing, weather, penalties, fan vote and the staff "Управление" card.
// State and API calls live here and in the ./race composables; the section
// components in ./race are presentational.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { AlertTriangle, CalendarDays, Film, Heart, ListChecks, Settings2, UserPlus } from 'lucide-vue-next'
import { api } from '../api'
import ImageCropper from '../components/ImageCropper.vue'
import RacePenaltyListModal from '../components/RacePenaltyListModal.vue'
import EmptyState from '../ui/EmptyState.vue'
import { gameLabel, isExternalRace } from '../i18nLabels'
import { safeHttpUrl } from '../safeUrl'
import { registeredCount } from '../raceDisplay'
import { state } from '../store'
import { prefersReducedMotion } from '../ui/motion/env'
import FanVoteCard from './race/FanVoteCard.vue'
import ParticipantsPanel from './race/ParticipantsPanel.vue'
import PenaltiesCard from './race/PenaltiesCard.vue'
import RaceBriefing from './race/RaceBriefing.vue'
import RaceErrorToast from './race/RaceErrorToast.vue'
import RaceHero from './race/RaceHero.vue'
import RaceLayout from './race/RaceLayout.vue'
import RaceVideoCard from './race/RaceVideoCard.vue'
import RaceWeather from './race/RaceWeather.vue'
import RegistrationPanel from './race/RegistrationPanel.vue'
import ResultsPanel from './race/ResultsPanel.vue'
import StaffFanVoteSetup from './race/StaffFanVoteSetup.vue'
import StaffForceRegistration from './race/StaffForceRegistration.vue'
import StaffPanel from './race/StaffPanel.vue'
import StaffRaceActions from './race/StaffRaceActions.vue'
import StaffResults from './race/StaffResults.vue'
import StaffVideo from './race/StaffVideo.vue'
import TrackLightbox from './race/TrackLightbox.vue'
import { parseDurationMs, parsePilotNumberValue, pilotNumberDraft } from './race/raceFormat'
import { useFanVote } from './race/useFanVote'
import { useForceRegistration } from './race/useForceRegistration'
import { useAcImport } from './race/useAcImport'
import { useManualResults } from './race/useManualResults'
import { useRaceResults } from './race/useRaceResults'
import { useTrackImage } from './race/useTrackImage'

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
const registering = ref(false)
const accQualificationFile = ref(null)
const accRaceFile = ref(null)
const raceVideoFile = ref(null)
const raceAssets = ref({ tracks: [], classes: [], games: {} })
const hero = ref(null)
const trackAverageLapMs = ref(null)
const penaltiesOpen = ref(false)
const focusedPenaltyId = ref(null)
const penaltyCreateOpen = ref(false)
const resultsTab = ref('race')
const resultsExpanded = ref(false)
const myTeam = ref(null)
const teamRaceNumber = ref(pilotNumberDraft(state.user?.pilot_number))
const teamDriverIds = ref([])

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
const {
  trackImage: raceTrackImage,
  trackFrame,
  trackImageFile,
  trackLightboxOpen: trackImageOpen,
  trackFramingOpen,
  trackFramingError,
  trackFrameBox,
  openTrackImage,
  closeTrackImage,
  setTrackImage,
  uploadTrackImage,
  openTrackFraming,
  closeTrackFraming,
  saveTrackFrame
} = useTrackImage({ race, raceAssets, raceAssetConfig, actionPending, runAction })

const participants = computed(() => race.value?.registered_pilots || [])
const teamRegistrations = computed(() => race.value?.team_registrations || [])
const registered = computed(() => participants.value.some((item) => item.user_id === state.user?.id))
const myEntry = computed(() => participants.value.find((item) => item.user_id === state.user?.id) || null)
const myTeamRegistration = computed(() => teamRegistrations.value.find((item) => item.team_id === state.user?.team_id) || null)
const teamRegistered = computed(() => Boolean(myTeamRegistration.value))
const canManageTeamRegistration = computed(() => Boolean(race.value?.is_team_event && myTeam.value?.is_owner))
const canManageRace = computed(() => ['admin', 'moder'].includes(state.user?.role))
const canForcePilotRegistration = computed(() => canManageRace.value && state.user?.role === 'admin' && Boolean(race.value) && !race.value.is_team_event && !['ongoing', 'finished'].includes(race.value.status))
const canRemovePilotRegistration = computed(() => canManageRace.value && Boolean(race.value) && !race.value.is_team_event && !['ongoing', 'finished'].includes(race.value.status))
// A championship stage takes its numbers from the championship, not from here.
const canAssignProfileNumbers = computed(() => canRemovePilotRegistration.value && !race.value.championship_id && participants.value.length > 0)
const canIssuePenalty = computed(() => ['admin', 'moder', 'marshall'].includes(state.user?.role) && ['ongoing', 'finished'].includes(race.value?.status))
const isChampionshipStage = computed(() => Boolean(race.value?.championship_id))
const isLmuRace = computed(() => race.value?.game === 'LMU')
const usesSimulatorJsonResults = computed(() => race.value?.game === 'ACC')
const canShowRegistrationPanel = computed(() => Boolean(state.user) && (race.value?.status === 'registration_open' || (isChampionshipStage.value && race.value?.status === 'not_started')))

const {
  raceRatingGame,
  participantName,
  resultRows,
  resultParticipants,
  penaltyParticipants,
  qualificationRows,
  resultTabOptions,
  knownPilots: fanVoteCandidates,
  resultView,
  raceSummary,
  resultPenaltyId
} = useRaceResults({ race, participants, penalties, raceAssets, resultsTab, t })

const {
  fanVote,
  fanVoteSelection,
  fanVoteVoting,
  fanVoteCanSetup,
  fanVoteCanSaveSetup,
  toggleFanVoteCandidate,
  syncFanVoteSelection,
  refreshFanVote,
  setupFanVote,
  castFanVote
} = useFanVote({ race, canManageRace, candidates: fanVoteCandidates, error })

const {
  manualRows,
  manualPilotSearch,
  manualPilotResults,
  manualPilotLoading,
  fillManualRows,
  addManualPilot,
  removeManualRow,
  updateManualRow,
  manualPayloadRows
} = useManualResults({ isLmuRace, resultRows, resultParticipants, participants, raceRatingGame, participantName, error })
const { acImport, readAcFile, linkAcDriver } = useAcImport({ manualRows, participants, participantName, error, badFileMessage: () => t('racePage.staff.acImport.badFile') })

const {
  forcePilotId,
  forcePilotNumber,
  forcePilotCar,
  forcePilotCandidates,
  forcePilotLoading,
  forcePilotSearch,
  updateForcePilotDefaults,
  loadForcePilotCandidates,
  forceRegisterPilot
} = useForceRegistration({ race, canForce: canForcePilotRegistration, error, actionPending, parsePilotNumber, t })

const ownPenaltyCount = computed(() => penalties.value.filter((penalty) => penalty.target_id === state.user?.id).length)
const raceIsFull = computed(() => Boolean(race.value) && !isLmuRace.value && Number(race.value.max_pilots) > 0 && registeredCount(race.value) >= Number(race.value.max_pilots))
const isFinished = computed(() => race.value?.status === 'finished')
const showResultsSection = computed(() => Boolean(resultRows.value.length || qualificationRows.value.length || ['ongoing', 'finished'].includes(race.value?.status)))
const hasMainColumn = computed(() => canShowRegistrationPanel.value || showResultsSection.value || isFinished.value || !isLmuRace.value)

/** Which call to action the hero shows. */
const ctaState = computed(() => {
  const current = race.value
  if (!current) return 'closed'
  if (isExternalRace(current)) return 'external'
  if (current.status === 'finished') return 'finished'
  if (current.status === 'ongoing') return 'live'
  if (!state.user) return 'login'
  if (registered.value || teamRegistered.value) return canShowRegistrationPanel.value ? 'registered' : 'registered-closed'
  if (!canShowRegistrationPanel.value) {
    const opensLater = !isChampionshipStage.value && new Date(current.registration_start).getTime() > Date.now()
    return opensLater ? 'soon' : 'closed'
  }
  if (current.is_team_event && !canManageTeamRegistration.value) return 'owner-only'
  if (raceIsFull.value) return 'full'
  return 'open'
})

const staffTabs = computed(() => {
  if (!canManageRace.value || !race.value) return []
  return [
    { value: 'race', label: t('racePage.staff.tabRace'), icon: Settings2 },
    ...(canForcePilotRegistration.value ? [{ value: 'registration', label: t('racePage.staff.tabRegistration'), icon: UserPlus }] : []),
    { value: 'results', label: t('raceDetails.results'), icon: ListChecks },
    ...(isFinished.value ? [{ value: 'media', label: t('racePage.staff.tabVideo'), icon: Film }] : []),
    ...(fanVoteCanSetup.value ? [{ value: 'vote', label: t('racePage.staff.tabVote'), icon: Heart }] : [])
  ]
})

function parseDuration(value, required = true) {
  return parseDurationMs(value, required, t('raceDetails.invalidTime'))
}

function parsePilotNumber(value) {
  return parsePilotNumberValue(value, t('raceDetails.invalidRacePilotNumber'))
}

function scrollToSection(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'start' })
}

function handleKeydown(event) {
  if (event.key !== 'Escape') return
  if (trackFramingOpen.value) closeTrackFraming()
  else if (trackImageOpen.value) closeTrackImage()
  else if (penaltiesOpen.value) closePenaltiesModal()
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

function openPenaltyCreator() {
  penaltiesOpen.value = true
  penaltyCreateOpen.value = true
}

function closePenaltiesModal() {
  penaltiesOpen.value = false
  focusedPenaltyId.value = null
  penaltyCreateOpen.value = false
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
    // Track statistics are optional; the briefing simply omits them.
    trackAverageLapMs.value = null
  }
}

function toggleTeamDriver(userId) {
  const id = Number(userId)
  teamDriverIds.value = teamDriverIds.value.includes(id)
    ? teamDriverIds.value.filter((item) => item !== id)
    : [...teamDriverIds.value, id]
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

async function load() {
  try {
    const loadedRace = await api(`/races/${route.params.id}`)
    const externalHref = safeHttpUrl(loadedRace.server_link)
    if (isExternalRace(loadedRace) && externalHref && !['admin', 'moder'].includes(state.user?.role)) {
      window.location.href = externalHref
      return
    }
    const [loadedFanVote, loadedRaceAssets] = await Promise.all([
      // The fan vote is a side block: if it cannot be loaded the race itself still shows.
      api(`/races/${route.params.id}/fan-vote`).catch(() => null),
      api('/race-assets')
    ])
    race.value = loadedRace
    fanVote.value = loadedFanVote
    raceAssets.value = loadedRaceAssets
    await loadForcePilotCandidates(loadedRace)
    await loadTrackAverageLap(loadedRace)
    if (state.user?.team_id && loadedRace.is_team_event) {
      try {
        myTeam.value = await api(`/teams/${state.user.team_id}`)
      } catch {
        // Without the team payload the panel explains that only the owner can register.
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

async function register() {
  error.value = ''
  registering.value = true
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
  } finally {
    registering.value = false
  }
}

async function unregister() {
  error.value = ''
  registering.value = true
  try {
    if (race.value?.is_team_event) {
      await unregisterTeam()
      return
    }
    race.value = await api(`/races/${race.value.id}/register`, { method: 'DELETE' })
  } catch (err) {
    error.value = err.message
  } finally {
    registering.value = false
  }
}

async function registerTeam() {
  if (!canManageTeamRegistration.value) throw new Error(t('racePage.form.ownerOnly'))
  const selectedDrivers = teamDriverIds.value.map(Number).filter(Boolean)
  if (!selectedDrivers.length) throw new Error(t('racePage.form.pickDrivers'))
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

/** Runs a staff action with the shared pending flag and error reporting. */
async function runAction(action) {
  error.value = ''
  actionPending.value = true
  try {
    await action()
  } catch (err) {
    error.value = err.message
  } finally {
    actionPending.value = false
  }
}

async function removePilotRegistration(item) {
  if (!race.value || !canRemovePilotRegistration.value) return
  if (!window.confirm(t('raceDetails.removePilotConfirm', { name: participantName(item) }))) return
  await runAction(async () => {
    race.value = await api(`/races/${race.value.id}/registrations/${item.user_id}`, { method: 'DELETE' })
  })
}

async function assignProfileNumbers() {
  if (!race.value || !canAssignProfileNumbers.value) return
  if (!window.confirm(t('raceDetails.assignProfileNumbersConfirm', { name: race.value.name }))) return
  await runAction(async () => {
    race.value = await api(`/races/${race.value.id}/registrations/assign-profile-numbers`, { method: 'POST' })
  })
}

async function closeRace() {
  if (!race.value || !window.confirm(t('raceDetails.confirmClose'))) return
  await runAction(async () => {
    race.value = await api(`/races/${race.value.id}/close`, { method: 'POST' })
    await refreshFanVote()
  })
}

async function readJsonFile(file) {
  if (!file) throw new Error(t('raceDetails.resultsFileRequired'))
  const buffer = await file.arrayBuffer()
  const bytes = new Uint8Array(buffer)
  const isUtf16 = (bytes[0] === 0xff && bytes[1] === 0xfe) || bytes.slice(0, 40).some((byte, index) => index % 2 === 1 && byte === 0)
  const decoder = new TextDecoder(isUtf16 ? 'utf-16le' : 'utf-8')
  return JSON.parse(decoder.decode(buffer).replace(/^﻿/, ''))
}

function setAccFile(kind, event) {
  const file = event.target.files?.[0] || null
  if (kind === 'qualification') accQualificationFile.value = file
  else accRaceFile.value = file
}

async function uploadAccResults() {
  if (!race.value) return
  await runAction(async () => {
    const qualification_results = race.value.has_qualification ? await readJsonFile(accQualificationFile.value) : null
    const race_results = await readJsonFile(accRaceFile.value)
    race.value = await api(`/races/${race.value.id}/results/acc`, { method: 'POST', body: { qualification_results, race_results } })
    fillManualRows()
    await refreshFanVote()
  })
}

async function uploadManualResults() {
  if (!race.value) return
  await runAction(async () => {
    const rows = manualPayloadRows({ withQualification: Boolean(race.value.has_qualification && !isLmuRace.value), parseDuration })
    race.value = await api(`/races/${race.value.id}/results/manual`, { method: 'POST', body: { rows } })
    fillManualRows()
    await refreshFanVote()
  })
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
  await runAction(async () => {
    const body = new FormData()
    body.append('file', raceVideoFile.value)
    race.value = await api(`/races/${race.value.id}/video`, { method: 'POST', body })
    raceVideoFile.value = null
  })
}

async function deleteRaceVideo() {
  if (!race.value?.video_url || !window.confirm(t('raceDetails.confirmDeleteVideo'))) return
  await runAction(async () => {
    race.value = await api(`/races/${race.value.id}/video`, { method: 'DELETE' })
    raceVideoFile.value = null
  })
}

async function createAppeal(penalty, form) {
  await api('/appeals', { method: 'POST', body: { ...form, penalty_id: penalty.id, race_id: race.value.id } })
  await load()
}

async function createPenalty(form) {
  if (!race.value) return
  await runAction(async () => {
    await api('/penalties', {
      method: 'POST',
      body: { ...form, race_id: race.value.id, penalty_type: 'combined', penalty_value: form.time_penalty_ms }
    })
    penaltyCreateOpen.value = false
    await load()
  })
}

async function deletePenalty(penalty) {
  if (!window.confirm(t('raceDetails.confirmDeletePenalty'))) return
  await runAction(async () => {
    await api(`/penalties/${penalty.id}/permanent`, { method: 'DELETE' })
    await load()
  })
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  load()
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div class="ui-page ui-shell ui-shell--wide race-page">
    <template v-if="race">
      <!-- Keyed by the race, so opening another race plays its winner's graphic again. -->
      <RaceHero
        :key="race.id"
        ref="hero"
        v-reveal="{ y: 24, blur: 10 }"
        :race="race"
        :track-image="raceTrackImage"
        :track-frame="trackFrame"
        :cta="ctaState"
        :summary="raceSummary"
        :has-results="resultRows.length > 0"
        @register="scrollToSection('race-registration')"
        @open-track="openTrackImage"
        @show-results="scrollToSection('race-results')"
      />

      <RaceLayout :class="{ 'is-finished': isFinished }" :expanded="resultsExpanded" :aside-only="!hasMainColumn">
        <template #main>
          <RegistrationPanel
            v-if="canShowRegistrationPanel"
            v-model:car="car"
            v-model:pilotNumber="pilotNumber"
            v-model:teamRaceNumber="teamRaceNumber"
            v-reveal
            class="race-page__registration"
            :race="race"
            :is-championship-stage="isChampionshipStage"
            :registered="registered"
            :my-entry="myEntry"
            :team-registered="teamRegistered"
            :my-team-registration="myTeamRegistration"
            :can-manage-team="canManageTeamRegistration"
            :my-team="myTeam"
            :team-driver-ids="teamDriverIds"
            :participants="participants"
            :team-registrations="teamRegistrations"
            :full="raceIsFull"
            :busy="registering"
            @register="register"
            @unregister="unregister"
            @toggle-driver="toggleTeamDriver"
            @move-driver="moveTeamDriver"
          />

          <ResultsPanel
            v-if="showResultsSection"
            v-model:tab="resultsTab"
            v-model:expanded="resultsExpanded"
            v-reveal
            class="race-page__results"
            :rows="resultView"
            :tab-options="resultTabOptions"
            :show-tabs="resultTabOptions.length > 1 && !isLmuRace"
            :show-quali-column="qualificationRows.length > 0"
            :can-open-penalties="Boolean(state.user)"
            :status="race.status"
            @open-penalty="openResultPenalty"
          />

          <RaceVideoCard v-if="isFinished" v-reveal class="race-page__video" :race="race" :can-manage="canManageRace" />

          <ParticipantsPanel
            v-if="!isLmuRace"
            v-reveal
            class="race-page__entries"
            :participants="participants"
            :team-registrations="teamRegistrations"
            :is-team-event="Boolean(race.is_team_event)"
            :max-pilots="Number(race.max_pilots) || 0"
            :game="raceRatingGame"
            :can-remove="canRemovePilotRegistration"
            :can-assign-numbers="canAssignProfileNumbers"
            :pending="actionPending"
            @remove="removePilotRegistration"
            @assign-numbers="assignProfileNumbers"
          />
        </template>

        <template #aside>
          <RaceBriefing v-reveal="{ delay: 80 }" :race="race" :track-average-lap-ms="trackAverageLapMs" :track-expected-average-lap-ms="trackExpectedAverageLapMs" />
          <RaceWeather v-reveal="{ delay: 140 }" :race="race" />
          <PenaltiesCard
            v-reveal="{ delay: 180 }"
            :count="penalties.length"
            :own-count="ownPenaltyCount"
            :can-issue="canIssuePenalty"
            @open="penaltiesOpen = true"
            @issue="openPenaltyCreator"
          />
          <FanVoteCard v-if="isFinished" v-reveal="{ delay: 220 }" :fan-vote="fanVote" :game="raceRatingGame" :voting="fanVoteVoting" @vote="castFanVote" />
        </template>
      </RaceLayout>

      <StaffPanel v-if="canManageRace" v-reveal :tabs="staffTabs">
        <template #race>
          <StaffRaceActions
            :race="race"
            :pending="actionPending"
            :track-image-file="trackImageFile"
            :has-track-image="Boolean(raceTrackImage)"
            @frame-track="openTrackFraming(hero?.artSize())"
            @close-race="closeRace"
            @delete-race="deleteRace"
            @track-file="setTrackImage"
            @upload-track="uploadTrackImage"
          />
        </template>
        <template #registration>
          <StaffForceRegistration
            v-model:search="forcePilotSearch"
            v-model:pilotId="forcePilotId"
            v-model:number="forcePilotNumber"
            v-model:car="forcePilotCar"
            :candidates="forcePilotCandidates"
            :loading="forcePilotLoading"
            :pending="actionPending"
            :allowed-cars="race.allowed_cars || []"
            @submit="forceRegisterPilot"
            @pilot-change="updateForcePilotDefaults"
          />
        </template>
        <template #results>
          <StaffResults
            v-model:pilotSearch="manualPilotSearch"
            :race="race"
            :pending="actionPending"
            :show-acc-upload="race.status !== 'finished' && usesSimulatorJsonResults"
            :with-qualification="Boolean(race.has_qualification && !isLmuRace)"
            :qualification-required="usesSimulatorJsonResults"
            :is-lmu="isLmuRace"
            :game="raceRatingGame"
            :rows="manualRows"
            :pilot-results="manualPilotResults"
            :pilot-loading="manualPilotLoading"
            :ac-import="race.game === 'AC' ? acImport : null"
            :show-ac-import="race.game === 'AC'"
            @ac-file="readAcFile"
            @ac-link="linkAcDriver"
            @acc-file="setAccFile"
            @upload-acc="uploadAccResults"
            @upload-manual="uploadManualResults"
            @add-pilot="addManualPilot"
            @remove-row="removeManualRow"
            @update-row="updateManualRow"
          />
        </template>
        <template #media>
          <StaffVideo :race="race" :pending="actionPending" :video-file="raceVideoFile" @video-file="setRaceVideo" @upload="uploadRaceVideo" @delete="deleteRaceVideo" />
        </template>
        <template #vote>
          <StaffFanVoteSetup
            :candidates="fanVoteCandidates"
            :selection="fanVoteSelection"
            :enabled="Boolean(fanVote?.enabled)"
            :can-save="fanVoteCanSaveSetup"
            :game="raceRatingGame"
            @toggle="toggleFanVoteCandidate"
            @submit="setupFanVote"
          />
        </template>
      </StaffPanel>

      <TrackLightbox :open="trackImageOpen" :src="raceTrackImage" :title="race.track" :badge="gameLabel(t, race.game)" @close="closeTrackImage" />

      <!-- Staff: the frame the hero shows the artwork in. The file itself is not changed. -->
      <ImageCropper
        v-if="trackFramingOpen && raceTrackImage"
        view-mode
        :source-url="raceTrackImage"
        :title="t('raceDetails.trackImageCropTitle')"
        :hint="t('raceDetails.trackImageCropHint')"
        :target-width="trackFrameBox.width"
        :target-height="trackFrameBox.height"
        :initial-view="trackFrame"
        :saving="actionPending"
        :error="trackFramingError"
        @close="closeTrackFraming"
        @view="saveTrackFrame"
      />

      <RacePenaltyListModal
        v-model:create-open="penaltyCreateOpen"
        :open="penaltiesOpen"
        :penalties="penalties"
        :appeals="appeals"
        :participants="penaltyParticipants"
        :focus-penalty-id="focusedPenaltyId"
        :game="raceRatingGame"
        :can-create="canIssuePenalty"
        :can-delete="state.user?.role === 'admin'"
        :busy="actionPending"
        @close="closePenaltiesModal"
        @create-penalty="createPenalty"
        @create-appeal="createAppeal"
        @delete-penalty="deletePenalty"
      />
    </template>

    <EmptyState v-else-if="!error" loading :title="t('ui.common.loading')" />

    <div v-else class="race-page__failed">
      <p class="ui-alert" role="alert"><AlertTriangle :size="18" />{{ error }}</p>
      <RouterLink class="ui-btn ui-btn--outline" to="/calendar"><CalendarDays :size="16" />{{ t('racePage.backToCalendar') }}</RouterLink>
    </div>

    <RaceErrorToast :message="race ? error : ''" @dismiss="error = ''" />
  </div>
</template>

<style scoped>
/* The side panels fly out past the page's edge when the results take the whole width: that part is cut off, not scrolled to. */
.race-page {
  overflow-x: clip;
}

/* The two columns live in RaceLayout. Upcoming races lead with the entry form, finished races with the results. */
.race-page__registration {
  order: 1;
}

.race-page__entries {
  order: 2;
}

.race-page__results {
  order: 3;
}

.is-finished .race-page__results {
  order: 0;
}

.is-finished .race-page__video {
  order: 1;
}

.race-page__failed {
  display: grid;
  justify-items: start;
  gap: 14px;
  max-width: 640px;
}

</style>
