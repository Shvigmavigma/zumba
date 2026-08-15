<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { CalendarDays, Check, Flag, Pencil, Plus, RefreshCw, Search, Trash2, UserPlus, X } from 'lucide-vue-next'
import { api } from '../api'
import LicenseBadge from '../components/LicenseBadge.vue'
import PaginationControls from '../components/PaginationControls.vue'
import UserAvatar from '../components/UserAvatar.vue'
import { gameOptions } from '../i18nLabels'
import { formatPilotNumber, formatRating, pilotName, ratingForGame, teamHref, teamShortName } from '../pilotDisplay'
import { state } from '../store'
import { formatDateTime as formatDateTimeInZone, formatShortDate } from '../timezone'

const { t } = useI18n()
const championships = ref([])
const selectedId = ref(null)
const raceAssets = ref({ tracks: [], classes: [], games: {} })
const assetGames = ['ACC', 'AC', 'iRacing', 'LMU']
const filter = ref('active')
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const createOpen = ref(false)
const editOpen = ref(false)
const editingStageId = ref(null)
const pilotSearch = ref('')
const pilotResults = ref([])
const pilotLoading = ref(false)
const addPilotId = ref('')
const addPilotCar = ref('')
const addPilotNumber = ref('')
const carDrafts = ref({})
const numberDrafts = ref({})
const applyPilotNumber = ref(pilotNumberDraft(state.user?.pilot_number))
const applyCar = ref('')
const myCarDraft = ref('')
const stageCreateOpen = ref(false)
const defaultStage = () => ({
  name: '',
  datetime_start: '',
  track: '',
  car_class: '',
  server_link: '',
  lmu_results_at: '',
  has_qualification: true,
  scoring_system: 'fia',
  pole_bonus_enabled: false
})
const stageForm = ref(defaultStage())
const stageEditForm = ref(defaultStage())
const standingsPage = ref(1)
const standingsPageSize = 18

const defaultForm = () => ({
  name: '',
  description: '',
  classes: [],
  registration_start: '',
  registration_end: '',
  championship_start: '',
  championship_end: '',
  video_url: '',
  game: 'ACC',
  car_change_allowed: false,
  scoring_system: 'fia',
  pole_bonus_enabled: false,
  is_published: false,
  stages: []
})
const form = ref(defaultForm())
const editForm = ref(defaultForm())

const canManage = computed(() => ['admin', 'moder'].includes(state.user?.role))
const gameChoices = computed(() => gameOptions((key) => key, false))
const selected = computed(() => championships.value.find((item) => item.id === selectedId.value) || championships.value[0] || null)
const selectedClasses = computed(() => new Set(form.value.classes))
const editSelectedClasses = computed(() => new Set(editForm.value.classes))
const formRaceAssets = computed(() => assetConfigForGame(form.value.game))
const editRaceAssets = computed(() => assetConfigForGame(editForm.value.game))
const selectedRaceAssets = computed(() => assetConfigForGame(selected.value?.game || 'ACC'))
const selectedAllowedCars = computed(() => carsForClasses(new Set(selected.value?.classes || []), selected.value?.game || 'ACC'))

function assetConfigForGame(game) {
  if (!assetGames.includes(game)) return { tracks: [], classes: [] }
  if (game === 'ACC') return raceAssets.value.games?.ACC || raceAssets.value
  return raceAssets.value.games?.[game] || { tracks: [], classes: [] }
}

function carsForClasses(classes, game) {
  const cars = []
  const seen = new Set()
  ;(assetConfigForGame(game).classes || []).forEach((item) => {
    if (!classes.has(item.name)) return
    ;(item.cars || []).forEach((car) => {
      const key = car.toLowerCase()
      if (!seen.has(key)) {
        seen.add(key)
        cars.push(car)
      }
    })
  })
  return cars
}

const standings = computed(() => selected.value?.standings || [])
const standingsTotalPages = computed(() => Math.max(1, Math.ceil(standings.value.length / standingsPageSize)))
const pagedStandings = computed(() => standings.value.slice((standingsPage.value - 1) * standingsPageSize, standingsPage.value * standingsPageSize))
const pendingRegistrations = computed(() => selected.value?.registrations?.filter((item) => item.status === 'pending') || [])
const approvedRegistrations = computed(() => selected.value?.registrations?.filter((item) => item.status === 'approved') || [])
const myRegistration = computed(() => selected.value?.registrations?.find((item) => item.user_id === state.user?.id) || null)
const canChangeMyCar = computed(() => Boolean(selected.value?.car_change_allowed && myRegistration.value?.status === 'approved'))
const myStatusText = computed(() => {
  const status = selected.value?.my_registration_status
  if (!status) return ''
  if (status === 'pending') return t('championships.requestPending')
  if (status === 'approved') return t('championships.requestApproved')
  return t('championships.requestRejected')
})

function dateLabel(value) {
  return formatDateTimeInZone(value)
}

function dateShort(value) {
  return formatShortDate(value)
}

function toIso(value) {
  return new Date(value).toISOString()
}

function optionalIso(value) {
  return value ? toIso(value) : null
}

function toLocalInput(value) {
  if (!value) return ''
  const date = new Date(value)
  const offset = date.getTimezoneOffset() * 60000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

function addStage() {
  form.value.stages.push(defaultStage())
}

function removeStage(index) {
  form.value.stages.splice(index, 1)
}

function toggleClass(name) {
  toggleClassIn(form.value, name)
}

function toggleEditClass(name) {
  toggleClassIn(editForm.value, name)
}

function toggleClassIn(target, name) {
  const classes = new Set(target.classes)
  if (classes.has(name)) classes.delete(name)
  else classes.add(name)
  target.classes = [...classes]
}

function handleChampionshipGameChange(target) {
  target.classes = []
  ;(target.stages || []).forEach((stage) => {
    stage.track = ''
    stage.car_class = ''
    if (target.game === 'LMU' && !stage.lmu_results_at) stage.lmu_results_at = stage.datetime_start
    if (target.game !== 'LMU') stage.lmu_results_at = ''
  })
}

function resetForm() {
  form.value = defaultForm()
  addStage()
}

function resetStageForm() {
  stageForm.value = defaultStage()
}

function resetStageEditForm() {
  stageEditForm.value = defaultStage()
  editingStageId.value = null
}

function pilotTitle(user) {
  return pilotName(user, user.login)
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

function parseCar(value) {
  const car = String(value || '').trim()
  if (!car) throw new Error(t('championships.chooseCar'))
  return car
}

function pilotLine(user, pilotNumber = user.pilot_number) {
  return [`#${formatPilotNumber(pilotNumber)}`, user.nickname, teamShortName(user.team_name, user.team_abbreviation), `RER ${formatRating(ratingForGame(user, selected.value?.game))}`].filter(Boolean).join(' - ')
}

function registrationPilotName(item) {
  return pilotTitle(item.user)
}

function registrationPilotLine(item) {
  return pilotLine(item.user, item.pilot_number)
}

function registrationStatusText(status) {
  if (status === 'pending') return t('championships.requestPending')
  if (status === 'approved') return t('championships.requestApproved')
  if (status === 'rejected') return t('championships.requestRejected')
  return ''
}

function championshipUserStatus(championship) {
  return registrationStatusText(championship?.my_registration_status)
}

function isStageRegistered(stage) {
  return Boolean(state.user && stage.registered_pilots?.some((item) => item.user_id === state.user.id))
}

function championshipCar(userId) {
  return approvedRegistrations.value.find((item) => item.user_id === userId)?.car_model || '-'
}

function stageHref(stage) {
  return `/races/${stage.id}`
}

function statusClass(status) {
  return `race-status-${status}`
}

function statusText(status) {
  const labels = {
    draft: 'statuses.draft',
    registration_open: 'statuses.registration_open',
    active: 'statuses.ongoing',
    upcoming: 'statuses.upcoming',
    not_started: 'statuses.not_started',
    ongoing: 'statuses.ongoing',
    finished: 'statuses.finished'
  }
  return labels[status] ? t(labels[status]) : String(status || '').replaceAll('_', ' ')
}

function scoringText(value) {
  const labels = {
    fia: 'FIA',
    endurance: 'Endurance',
    linear: 'Linear'
  }
  return labels[value] || String(value || '').toUpperCase()
}

function cleanText(value) {
  const text = String(value || '').trim()
  if (!text || text.includes('\uFFFD') || /\?{3,}/.test(text)) return ''
  return text
}

function stagePluralSuffix(count) {
  if (state.locale !== 'ru') return count === 1 ? 'One' : 'Many'
  const mod10 = count % 10
  const mod100 = count % 100
  if (mod10 === 1 && mod100 !== 11) return 'One'
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return 'Few'
  return 'Many'
}

function stageCount(count) {
  return `${count} ${t(`championships.stageWord${stagePluralSuffix(count)}`)}`
}

function podiumRankClass(rank) {
  if (rank === 1) return 'is-gold'
  if (rank === 2) return 'is-silver'
  if (rank === 3) return 'is-bronze'
  return ''
}

async function loadChampionships() {
  loading.value = true
  error.value = ''
  try {
    const params = new URLSearchParams({ status_filter: filter.value, limit: '50' })
    championships.value = await api(`/championships?${params.toString()}`)
    if (!selectedId.value || !championships.value.some((item) => item.id === selectedId.value)) {
      selectedId.value = championships.value[0]?.id || null
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function reloadSelected() {
  if (!selected.value) return loadChampionships()
  const updated = await api(`/championships/${selected.value.id}`)
  const index = championships.value.findIndex((item) => item.id === updated.id)
  if (index >= 0) championships.value.splice(index, 1, updated)
  else championships.value.unshift(updated)
  selectedId.value = updated.id
}

async function createChampionship() {
  saving.value = true
  error.value = ''
  try {
    const classes = form.value.classes
    if (!classes.length) throw new Error(t('championships.classRequired'))
    const stages = form.value.stages
      .filter((stage) => stage.datetime_start)
      .map((stage) => ({
        ...stage,
        datetime_start: toIso(stage.datetime_start),
        lmu_results_at: form.value.game === 'LMU' ? optionalIso(stage.lmu_results_at) : null,
        name: stage.name || null,
        track: stage.track || null,
        car_class: stage.car_class || null,
        server_link: stage.server_link || '',
        has_qualification: form.value.game === 'LMU' ? false : stage.has_qualification,
      }))
    const created = await api('/championships', {
      method: 'POST',
      body: {
        ...form.value,
        classes,
        registration_start: toIso(form.value.registration_start),
        registration_end: toIso(form.value.registration_end),
        championship_start: toIso(form.value.championship_start),
        championship_end: toIso(form.value.championship_end),
        video_url: form.value.video_url || null,
        stages
      }
    })
    championships.value.unshift(created)
    selectedId.value = created.id
    createOpen.value = false
    resetForm()
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}

function startEditChampionship() {
  if (!selected.value) return
  editForm.value = {
    name: selected.value.name || '',
    description: selected.value.description || '',
    classes: [...(selected.value.classes || [])],
    registration_start: toLocalInput(selected.value.registration_start),
    registration_end: toLocalInput(selected.value.registration_end),
    championship_start: toLocalInput(selected.value.championship_start),
    championship_end: toLocalInput(selected.value.championship_end),
    video_url: selected.value.video_url || '',
    game: selected.value.game || 'ACC',
    car_change_allowed: Boolean(selected.value.car_change_allowed),
    scoring_system: selected.value.scoring_system || 'fia',
    pole_bonus_enabled: Boolean(selected.value.pole_bonus_enabled),
    is_published: Boolean(selected.value.is_published),
    stages: []
  }
  editOpen.value = true
}

async function updateChampionship() {
  if (!selected.value) return
  saving.value = true
  error.value = ''
  try {
    const classes = editForm.value.classes
    if (!classes.length) throw new Error(t('championships.classRequired'))
    const updated = await api(`/championships/${selected.value.id}`, {
      method: 'PATCH',
      body: {
        ...editForm.value,
        classes,
        registration_start: toIso(editForm.value.registration_start),
        registration_end: toIso(editForm.value.registration_end),
        championship_start: toIso(editForm.value.championship_start),
        championship_end: toIso(editForm.value.championship_end),
        video_url: editForm.value.video_url || null
      }
    })
    replaceChampionship(updated)
    editOpen.value = false
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}

async function deleteChampionship() {
  if (!selected.value || !window.confirm(t('championships.deleteConfirm', { name: selected.value.name }))) return
  saving.value = true
  error.value = ''
  try {
    const deletedId = selected.value.id
    await api(`/championships/${deletedId}`, { method: 'DELETE' })
    championships.value = championships.value.filter((item) => item.id !== deletedId)
    selectedId.value = championships.value[0]?.id || null
    editOpen.value = false
    stageCreateOpen.value = false
    resetStageEditForm()
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}

async function applyToChampionship() {
  if (!selected.value) return
  error.value = ''
  try {
    const updated = await api(`/championships/${selected.value.id}/apply`, {
      method: 'POST',
      body: {
        pilot_number: parsePilotNumber(applyPilotNumber.value),
        car_model: parseCar(applyCar.value)
      }
    })
    replaceChampionship(updated)
  } catch (err) {
    error.value = err.message
  }
}

function replaceChampionship(updated) {
  const index = championships.value.findIndex((item) => item.id === updated.id)
  if (index >= 0) championships.value.splice(index, 1, updated)
  else championships.value.unshift(updated)
}

async function moderateRegistration(registration, status) {
  if (!selected.value) return
  error.value = ''
  try {
    const updated = await api(`/championships/${selected.value.id}/registrations/${registration.id}`, {
      method: 'PATCH',
      body: {
        status,
        pilot_number: parsePilotNumber(numberDrafts.value[registration.user_id] || pilotNumberDraft(registration.pilot_number ?? registration.user.pilot_number)),
        car_model: parseCar(carDrafts.value[registration.user_id] || registration.car_model)
      }
    })
    replaceChampionship(updated)
  } catch (err) {
    error.value = err.message
  }
}

async function removeParticipant(userId) {
  if (!selected.value) return
  error.value = ''
  try {
    const updated = await api(`/championships/${selected.value.id}/participants/${userId}`, { method: 'DELETE' })
    replaceChampionship(updated)
  } catch (err) {
    error.value = err.message
  }
}

async function updateCar(userId) {
  if (!selected.value) return
  error.value = ''
  try {
    const car = parseCar(carDrafts.value[userId])
    const updated = await api(`/championships/${selected.value.id}/participants/${userId}/car`, {
      method: 'PATCH',
      body: { car_model: car }
    })
    replaceChampionship(updated)
  } catch (err) {
    error.value = err.message
  }
}

async function searchPilots() {
  pilotLoading.value = true
  try {
    const params = new URLSearchParams({ search: pilotSearch.value, limit: '20', rating_game: selected.value?.game || 'ACC' })
    pilotResults.value = await api(`/users/pilots?${params.toString()}`)
  } catch (err) {
    error.value = err.message
  } finally {
    pilotLoading.value = false
  }
}

async function addParticipant() {
  if (!selected.value || !addPilotId.value || !addPilotNumber.value || !addPilotCar.value) return
  error.value = ''
  try {
    const updated = await api(`/championships/${selected.value.id}/participants`, {
      method: 'POST',
      body: {
        user_id: Number(addPilotId.value),
        pilot_number: parsePilotNumber(addPilotNumber.value),
        car_model: parseCar(addPilotCar.value)
      }
    })
    replaceChampionship(updated)
    addPilotId.value = ''
    addPilotCar.value = ''
    addPilotNumber.value = ''
  } catch (err) {
    error.value = err.message
  }
}

async function addStageToSelected() {
  if (!selected.value || !stageForm.value.datetime_start) return
  error.value = ''
  try {
    const updated = await api(`/championships/${selected.value.id}/stages`, {
      method: 'POST',
      body: {
        ...stageForm.value,
        name: stageForm.value.name || null,
        track: stageForm.value.track || null,
        car_class: stageForm.value.car_class || null,
        server_link: stageForm.value.server_link || '',
        lmu_results_at: selected.value.game === 'LMU' ? optionalIso(stageForm.value.lmu_results_at) : null,
        has_qualification: selected.value.game === 'LMU' ? false : stageForm.value.has_qualification,
        datetime_start: toIso(stageForm.value.datetime_start)
      }
    })
    replaceChampionship(updated)
    resetStageForm()
    stageCreateOpen.value = false
  } catch (err) {
    error.value = err.message
  }
}

function startEditStage(stage) {
  editingStageId.value = stage.id
  stageEditForm.value = {
    name: stage.name || '',
    datetime_start: toLocalInput(stage.datetime_start),
    track: stage.track || '',
    car_class: stage.car_class || '',
    server_link: stage.server_link || '',
    lmu_results_at: stage.lmu_results_at ? toLocalInput(stage.lmu_results_at) : '',
    has_qualification: Boolean(stage.has_qualification),
    scoring_system: stage.scoring_system || 'fia',
    pole_bonus_enabled: Boolean(stage.pole_bonus_enabled)
  }
}

async function updateStage(stageId) {
  if (!selected.value || !stageEditForm.value.datetime_start) return
  error.value = ''
  try {
    const updated = await api(`/championships/${selected.value.id}/stages/${stageId}`, {
      method: 'PATCH',
      body: {
        ...stageEditForm.value,
        track: stageEditForm.value.track || null,
        car_class: stageEditForm.value.car_class || null,
        server_link: stageEditForm.value.server_link || '',
        lmu_results_at: selected.value.game === 'LMU' ? optionalIso(stageEditForm.value.lmu_results_at) : null,
        has_qualification: selected.value.game === 'LMU' ? false : stageEditForm.value.has_qualification,
        datetime_start: toIso(stageEditForm.value.datetime_start)
      }
    })
    replaceChampionship(updated)
    resetStageEditForm()
  } catch (err) {
    error.value = err.message
  }
}

async function deleteStage(stage) {
  if (!selected.value || !window.confirm(t('championships.stageDeleteConfirm'))) return
  error.value = ''
  try {
    const updated = await api(`/championships/${selected.value.id}/stages/${stage.id}`, { method: 'DELETE' })
    replaceChampionship(updated)
    resetStageEditForm()
  } catch (err) {
    error.value = err.message
  }
}

async function updateMyCar() {
  if (!selected.value) return
  error.value = ''
  try {
    const car = parseCar(myCarDraft.value)
    const updated = await api(`/championships/${selected.value.id}/me/car`, {
      method: 'PATCH',
      body: { car_model: car }
    })
    replaceChampionship(updated)
  } catch (err) {
    error.value = err.message
  }
}

onMounted(async () => {
  resetForm()
  await Promise.all([
    loadChampionships(),
    api('/race-assets').then((data) => {
      raceAssets.value = data
    })
  ])
})

watch(filter, loadChampionships)
watch(selected, () => {
  standingsPage.value = 1
  const drafts = {}
  const numberValues = {}
  ;(selected.value?.registrations || []).forEach((item) => {
    drafts[item.user_id] = item.car_model || ''
    numberValues[item.user_id] = pilotNumberDraft(item.pilot_number ?? item.user?.pilot_number)
  })
  carDrafts.value = drafts
  numberDrafts.value = numberValues
  myCarDraft.value = myRegistration.value?.car_model || ''
  applyPilotNumber.value = pilotNumberDraft(state.user?.pilot_number)
  applyCar.value = ''
  editOpen.value = false
  stageCreateOpen.value = false
  resetStageForm()
  resetStageEditForm()
})
watch(pilotSearch, () => {
  if (pilotSearch.value.trim().length >= 1) searchPilots()
  else pilotResults.value = []
})
watch(standings, () => {
  if (standingsPage.value > standingsTotalPages.value) {
    standingsPage.value = standingsTotalPages.value
  }
})
</script>

<template>
  <section class="section championships-page">
    <div class="section-header championships-header">
      <div>
        <h1>{{ t('championships.title') }}</h1>
        <p class="muted">{{ t('championships.subtitle') }}</p>
      </div>
      <div class="toolbar">
        <button class="button" type="button" :disabled="loading" @click="loadChampionships">
          <RefreshCw :size="16" />
          {{ t('common.reload') }}
        </button>
        <button v-if="canManage" class="button primary" type="button" @click="createOpen = !createOpen">
          <Plus :size="16" />
          {{ t('common.create') }}
        </button>
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <form v-if="canManage && createOpen" class="card championship-editor" @submit.prevent="createChampionship">
      <div class="championship-editor-head">
        <h2>{{ t('championships.createTitle') }}</h2>
        <label class="toggle-field">
          <input v-model="form.is_published" type="checkbox" />
          <span>{{ t('championships.published') }}</span>
        </label>
      </div>

      <div class="form-row">
        <label class="field"><span>{{ t('fields.name') }} *</span><input v-model="form.name" required maxlength="120" /></label>
        <label class="field">
          <span>{{ t('fields.game') }} *</span>
          <select v-model="form.game" @change="handleChampionshipGameChange(form)">
            <option v-for="option in gameChoices" :key="option.value" :value="option.value">{{ option.value }}</option>
          </select>
        </label>
      </div>

      <label class="field"><span>{{ t('fields.description') }}</span><textarea v-model="form.description" maxlength="3000" /></label>

      <div class="championship-class-grid">
        <button
          v-for="item in formRaceAssets.classes"
          :key="item.name"
          class="championship-class-chip"
          :class="{ active: selectedClasses.has(item.name) }"
          type="button"
          @click="toggleClass(item.name)"
        >
          {{ item.name }}
          <small>{{ item.cars?.length || 0 }}</small>
        </button>
      </div>
      <div class="form-row">
        <label class="field"><span>{{ t('fields.registrationStart') }} *</span><input v-model="form.registration_start" type="datetime-local" required /></label>
        <label class="field"><span>{{ t('fields.registrationEnd') }} *</span><input v-model="form.registration_end" type="datetime-local" required /></label>
      </div>
      <div class="form-row">
        <label class="field"><span>{{ t('championships.championshipStart') }} *</span><input v-model="form.championship_start" type="datetime-local" required /></label>
        <label class="field"><span>{{ t('championships.championshipEnd') }} *</span><input v-model="form.championship_end" type="datetime-local" required /></label>
      </div>

      <div class="form-row">
        <label class="field"><span>{{ t('championships.video') }}</span><input v-model="form.video_url" maxlength="255" placeholder="https://..." /></label>
      </div>

      <div class="form-row">
        <div class="championship-switches">
          <label class="toggle-field"><input v-model="form.car_change_allowed" type="checkbox" /><span>{{ t('championships.carCanChange') }}</span></label>
        </div>
      </div>

      <div class="championship-stage-editor">
        <div class="section-header compact">
          <h3>{{ t('championships.stages') }}</h3>
          <button class="button small" type="button" @click="addStage"><Plus :size="14" />{{ t('championships.stage') }}</button>
        </div>
        <div v-for="(stage, index) in form.stages" :key="index" class="championship-stage-draft">
          <label class="field"><span>{{ t('fields.name') }}</span><input v-model="stage.name" :placeholder="t('championships.stageNumber', { number: index + 1 })" maxlength="100" /></label>
          <label class="field"><span>{{ t('fields.date') }} *</span><input v-model="stage.datetime_start" type="datetime-local" required /></label>
          <label v-if="form.game === 'LMU'" class="field"><span>{{ t('fields.lmuResultsAt') }} *</span><input v-model="stage.lmu_results_at" type="datetime-local" required /></label>
          <label class="field"><span>{{ t('fields.linkUrl') }}</span><input v-model="stage.server_link" maxlength="255" /></label>
          <label class="field">
            <span>{{ t('fields.track') }}<template v-if="form.game === 'LMU'"> *</template></span>
            <select v-model="stage.track" :required="form.game === 'LMU'">
              <option value="">TBA</option>
              <option v-for="track in formRaceAssets.tracks" :key="track" :value="track">{{ track }}</option>
            </select>
          </label>
          <label v-if="form.game === 'LMU'" class="field">
            <span>{{ t('fields.class') }} *</span>
            <select v-model="stage.car_class" required>
              <option value="">TBA</option>
              <option v-for="item in formRaceAssets.classes" :key="item.name" :value="item.name">{{ item.name }}</option>
            </select>
          </label>
          <label v-if="form.game !== 'LMU'" class="toggle-field"><input v-model="stage.has_qualification" type="checkbox" /><span>{{ t('fields.qualification') }}</span></label>
          <label class="field">
            <span>{{ t('championships.stageScoring') }}</span>
            <select v-model="stage.scoring_system">
              <option value="fia">FIA 25-18-15</option>
              <option value="endurance">Endurance 38-27-23</option>
              <option value="linear">Linear N+1</option>
            </select>
          </label>
          <label class="toggle-field"><input v-model="stage.pole_bonus_enabled" type="checkbox" /><span>{{ t('championships.poleBonus') }}</span></label>
          <button class="icon-button" type="button" :title="t('championships.deleteStage')" @click="removeStage(index)"><Trash2 :size="16" /></button>
        </div>
      </div>

      <button class="button primary" type="submit" :disabled="saving">{{ saving ? t('common.saving') : t('championships.createChampionship') }}</button>
    </form>

    <div class="championships-layout">
      <section class="championships-list card">
        <div class="championship-filter-tabs" role="tablist" :aria-label="t('championships.filterAria')">
          <button type="button" :class="{ active: filter === 'active' }" @click="filter = 'active'">{{ t('championships.active') }}</button>
          <button type="button" :class="{ active: filter === 'inactive' }" @click="filter = 'inactive'">{{ t('championships.inactive') }}</button>
          <button type="button" :class="{ active: filter === 'all' }" @click="filter = 'all'">{{ t('championships.all') }}</button>
        </div>

        <div class="championship-card-strip">
          <button
            v-for="championship in championships"
            :key="championship.id"
            class="championship-list-card"
            :class="{ active: selected?.id === championship.id }"
            type="button"
            @click="selectedId = championship.id"
          >
            <span class="championship-list-icon"><Flag :size="18" /></span>
            <span>
              <strong>{{ championship.name }}</strong>
              <small>{{ championship.game }} - {{ championship.classes.join(', ') }}</small>
            </span>
            <span class="championship-card-badges">
              <span v-if="championshipUserStatus(championship)" class="status-badge championship-user-badge">{{ championshipUserStatus(championship) }}</span>
              <span class="status-badge" :class="statusClass(championship.status)">{{ statusText(championship.status) }}</span>
            </span>
          </button>
        </div>

        <div v-if="!championships.length" class="empty-state">
          {{ loading ? t('common.loading') : t('championships.noItems') }}
        </div>
      </section>

      <article v-if="selected" class="championship-detail">
        <section class="card championship-hero">
          <div>
            <div class="championship-eyebrow">
              <span>{{ selected.game }}</span>
              <span>{{ stageCount(selected.stages.length) }}</span>
            </div>
            <h2>{{ selected.name }}</h2>
            <p>{{ cleanText(selected.description) || t('championships.noDescription') }}</p>
            <div class="championship-meta-grid">
              <span><small>{{ t('championships.registration') }}</small><strong>{{ dateShort(selected.registration_start) }} - {{ dateShort(selected.registration_end) }}</strong></span>
              <span><small>{{ t('championships.championship') }}</small><strong>{{ dateShort(selected.championship_start) }} - {{ dateShort(selected.championship_end) }}</strong></span>
              <span><small>{{ t('fields.participants') }}</small><strong>{{ selected.participant_count }}</strong></span>
              <span><small>{{ t('championships.requests') }}</small><strong>{{ selected.pending_count }}</strong></span>
            </div>
          </div>
          <div class="championship-action-card">
            <span class="status-badge" :class="statusClass(selected.status)">{{ statusText(selected.status) }}</span>
            <strong>{{ selected.classes.join(' / ') }}</strong>
            <button v-if="canManage" class="button" type="button" @click="editOpen ? editOpen = false : startEditChampionship()">
              <Pencil :size="16" />
              {{ editOpen ? t('championships.closeEdit') : t('common.edit') }}
            </button>
            <button v-if="canManage" class="button danger" type="button" :disabled="saving" @click="deleteChampionship">
              <Trash2 :size="16" />
              {{ t('championships.deleteChampionship') }}
            </button>
            <p v-if="myStatusText" class="muted">{{ myStatusText }}</p>
            <form v-if="selected.can_apply" class="championship-my-car-form" @submit.prevent="applyToChampionship">
              <label class="field">
                <span>{{ t('fields.pilotNumber') }}</span>
                <input v-model="applyPilotNumber" inputmode="numeric" pattern="[0-9]{3}" minlength="3" maxlength="3" placeholder="000" required />
              </label>
              <label class="field">
                <span>{{ t('championships.car') }}</span>
                <select v-if="selectedAllowedCars.length" v-model="applyCar" required>
                  <option value="" disabled>{{ t('championships.chooseCar') }}</option>
                  <option v-for="car in selectedAllowedCars" :key="car" :value="car">{{ car }}</option>
                </select>
                <input v-else v-model="applyCar" maxlength="80" required />
              </label>
              <button class="button primary" type="submit">{{ t('championships.submitRequest') }}</button>
            </form>
            <form v-if="canChangeMyCar" class="championship-my-car-form" @submit.prevent="updateMyCar">
              <label class="field">
                <span>{{ t('championships.myCar') }}</span>
                <select v-if="selectedAllowedCars.length" v-model="myCarDraft" required>
                  <option value="" disabled>{{ t('championships.chooseCar') }}</option>
                  <option v-for="car in selectedAllowedCars" :key="car" :value="car">{{ car }}</option>
                </select>
                <input v-else v-model="myCarDraft" maxlength="80" required />
              </label>
              <button class="button small" type="submit">{{ t('championships.change') }}</button>
            </form>
            <a v-if="selected.video_url" class="button" :href="selected.video_url" target="_blank" rel="noreferrer">{{ t('championships.video') }}</a>
          </div>
        </section>

        <form v-if="canManage && editOpen" class="card championship-editor" @submit.prevent="updateChampionship">
          <div class="championship-editor-head">
            <h2>{{ t('championships.editTitle') }}</h2>
            <label class="toggle-field">
              <input v-model="editForm.is_published" type="checkbox" />
              <span>{{ t('championships.published') }}</span>
            </label>
          </div>

          <div class="form-row">
            <label class="field"><span>{{ t('fields.name') }} *</span><input v-model="editForm.name" required maxlength="120" /></label>
            <label class="field">
              <span>{{ t('fields.game') }} *</span>
              <select v-model="editForm.game" @change="handleChampionshipGameChange(editForm)">
                <option v-for="option in gameChoices" :key="option.value" :value="option.value">{{ option.value }}</option>
              </select>
            </label>
          </div>

          <label class="field"><span>{{ t('fields.description') }}</span><textarea v-model="editForm.description" maxlength="3000" /></label>

          <div class="championship-class-grid">
            <button
              v-for="item in editRaceAssets.classes"
              :key="item.name"
              class="championship-class-chip"
              :class="{ active: editSelectedClasses.has(item.name) }"
              type="button"
              @click="toggleEditClass(item.name)"
            >
              {{ item.name }}
              <small>{{ item.cars?.length || 0 }}</small>
            </button>
          </div>
          <div class="form-row">
            <label class="field"><span>{{ t('fields.registrationStart') }} *</span><input v-model="editForm.registration_start" type="datetime-local" required /></label>
            <label class="field"><span>{{ t('fields.registrationEnd') }} *</span><input v-model="editForm.registration_end" type="datetime-local" required /></label>
          </div>
          <div class="form-row">
            <label class="field"><span>{{ t('championships.championshipStart') }} *</span><input v-model="editForm.championship_start" type="datetime-local" required /></label>
            <label class="field"><span>{{ t('championships.championshipEnd') }} *</span><input v-model="editForm.championship_end" type="datetime-local" required /></label>
          </div>

          <div class="form-row">
            <label class="field"><span>{{ t('championships.video') }}</span><input v-model="editForm.video_url" maxlength="255" placeholder="https://..." /></label>
          </div>

          <div class="form-row">
            <div class="championship-switches">
              <label class="toggle-field"><input v-model="editForm.car_change_allowed" type="checkbox" /><span>{{ t('championships.carCanChange') }}</span></label>
            </div>
          </div>

          <button class="button primary" type="submit" :disabled="saving">{{ saving ? t('common.saving') : t('championships.saveChanges') }}</button>
        </form>

        <section class="card championship-stages">
          <div class="section-header compact">
            <h3>{{ t('championships.stages') }}</h3>
            <div class="toolbar">
              <span class="pill">{{ selected.stages.length }}</span>
              <button v-if="canManage" class="button small" type="button" @click="stageCreateOpen = !stageCreateOpen">
                <Plus :size="14" />
                {{ t('championships.stage') }}
              </button>
            </div>
          </div>
          <form v-if="canManage && stageCreateOpen" class="championship-stage-draft championship-stage-add-form" @submit.prevent="addStageToSelected">
            <label class="field"><span>{{ t('fields.name') }}</span><input v-model="stageForm.name" maxlength="100" /></label>
            <label class="field"><span>{{ t('fields.date') }} *</span><input v-model="stageForm.datetime_start" type="datetime-local" required /></label>
            <label v-if="selected.game === 'LMU'" class="field"><span>{{ t('fields.lmuResultsAt') }} *</span><input v-model="stageForm.lmu_results_at" type="datetime-local" required /></label>
            <label class="field"><span>{{ t('fields.linkUrl') }}</span><input v-model="stageForm.server_link" maxlength="255" /></label>
            <label class="field">
              <span>{{ t('fields.track') }}<template v-if="selected.game === 'LMU'"> *</template></span>
              <select v-model="stageForm.track" :required="selected.game === 'LMU'">
                <option value="">TBA</option>
                <option v-for="track in selectedRaceAssets.tracks" :key="track" :value="track">{{ track }}</option>
              </select>
            </label>
            <label v-if="selected.game === 'LMU'" class="field">
              <span>{{ t('fields.class') }} *</span>
              <select v-model="stageForm.car_class" required>
                <option value="">TBA</option>
                <option v-for="item in selectedRaceAssets.classes" :key="item.name" :value="item.name">{{ item.name }}</option>
              </select>
            </label>
            <label v-if="selected.game !== 'LMU'" class="toggle-field"><input v-model="stageForm.has_qualification" type="checkbox" /><span>{{ t('fields.qualification') }}</span></label>
            <label class="field">
              <span>{{ t('championships.stageScoring') }}</span>
              <select v-model="stageForm.scoring_system">
                <option value="fia">FIA 25-18-15</option>
                <option value="endurance">Endurance 38-27-23</option>
                <option value="linear">Linear N+1</option>
              </select>
            </label>
            <label class="toggle-field"><input v-model="stageForm.pole_bonus_enabled" type="checkbox" /><span>{{ t('championships.poleBonus') }}</span></label>
            <button class="button small primary" type="submit">{{ t('common.create') }}</button>
          </form>
          <div class="championship-stage-list">
            <article v-for="stage in selected.stages" :key="stage.id" class="championship-stage-row">
              <RouterLink class="championship-stage-card" :to="stageHref(stage)">
                <span class="championship-round">R{{ stage.championship_round }}</span>
                <span>
                  <strong>{{ stage.name }}</strong>
                  <small>{{ [dateLabel(stage.datetime_start), stage.track, stage.car_class].filter(Boolean).join(' - ') }}</small>
                  <small class="championship-stage-scoring">
                    {{ scoringText(stage.scoring_system) }}<template v-if="stage.pole_bonus_enabled"> + {{ t('championships.poleShort') }}</template>
                  </small>
                </span>
                <span class="championship-stage-statuses">
                  <span v-if="isStageRegistered(stage)" class="status-badge championship-user-badge">{{ t('championships.stageRegistered') }}</span>
                  <span class="status-badge" :class="statusClass(stage.status)">{{ statusText(stage.status) }}</span>
                </span>
              </RouterLink>
              <div v-if="canManage" class="championship-stage-actions">
                <button class="icon-button" type="button" :title="t('championships.editStage')" @click="startEditStage(stage)"><Pencil :size="16" /></button>
                <button class="icon-button danger" type="button" :title="t('championships.deleteStage')" :disabled="stage.status === 'finished'" @click="deleteStage(stage)"><Trash2 :size="16" /></button>
              </div>
              <form v-if="editingStageId === stage.id" class="championship-stage-draft championship-stage-edit-form" @submit.prevent="updateStage(stage.id)">
                <label class="field"><span>{{ t('fields.name') }}</span><input v-model="stageEditForm.name" maxlength="100" required /></label>
                <label class="field"><span>{{ t('fields.date') }} *</span><input v-model="stageEditForm.datetime_start" type="datetime-local" required /></label>
                <label v-if="selected.game === 'LMU'" class="field"><span>{{ t('fields.lmuResultsAt') }} *</span><input v-model="stageEditForm.lmu_results_at" type="datetime-local" required /></label>
                <label class="field"><span>{{ t('fields.linkUrl') }}</span><input v-model="stageEditForm.server_link" maxlength="255" /></label>
                <label class="field">
                  <span>{{ t('fields.track') }}<template v-if="selected.game === 'LMU'"> *</template></span>
                  <select v-model="stageEditForm.track" :required="selected.game === 'LMU'">
                    <option value="">TBA</option>
                    <option v-for="track in selectedRaceAssets.tracks" :key="track" :value="track">{{ track }}</option>
                  </select>
                </label>
                <label v-if="selected.game === 'LMU'" class="field">
                  <span>{{ t('fields.class') }} *</span>
                  <select v-model="stageEditForm.car_class" required>
                    <option value="">TBA</option>
                    <option v-for="item in selectedRaceAssets.classes" :key="item.name" :value="item.name">{{ item.name }}</option>
                  </select>
                </label>
                <label v-if="selected.game !== 'LMU'" class="toggle-field"><input v-model="stageEditForm.has_qualification" type="checkbox" /><span>{{ t('fields.qualification') }}</span></label>
                <label class="field">
                  <span>{{ t('championships.stageScoring') }}</span>
                  <select v-model="stageEditForm.scoring_system">
                    <option value="fia">FIA 25-18-15</option>
                    <option value="endurance">Endurance 38-27-23</option>
                    <option value="linear">Linear N+1</option>
                  </select>
                </label>
                <label class="toggle-field"><input v-model="stageEditForm.pole_bonus_enabled" type="checkbox" /><span>{{ t('championships.poleBonus') }}</span></label>
                <button class="button small primary" type="submit">{{ t('common.save') }}</button>
              </form>
            </article>
          </div>
        </section>

        <section v-if="canManage" class="card championship-admin-panel">
          <div class="section-header compact">
            <h3>{{ t('championships.requestsAndParticipants') }}</h3>
            <span class="pill">{{ t('championships.pendingCount', { count: pendingRegistrations.length }) }}</span>
          </div>

          <div class="championship-request-list">
            <article v-for="registration in pendingRegistrations" :key="registration.id" class="championship-request-card">
              <UserAvatar mini :src="registration.user.avatar_url" :color="registration.user.avatar_color" :label="registrationPilotName(registration)" />
              <div>
                <strong>{{ registrationPilotName(registration) }}</strong>
                <small>{{ registrationPilotLine(registration) }}</small>
              </div>
              <input v-model="numberDrafts[registration.user_id]" inputmode="numeric" pattern="[0-9]{3}" minlength="3" maxlength="3" :placeholder="t('fields.pilotNumber')" />
              <select v-if="selectedAllowedCars.length" v-model="carDrafts[registration.user_id]" required>
                <option value="" disabled>{{ t('championships.chooseCar') }}</option>
                <option v-for="car in selectedAllowedCars" :key="car" :value="car">{{ car }}</option>
              </select>
              <input v-else v-model="carDrafts[registration.user_id]" maxlength="80" required />
              <button class="icon-button success" type="button" :title="t('common.approve')" @click="moderateRegistration(registration, 'approved')"><Check :size="16" /></button>
              <button class="icon-button danger" type="button" :title="t('common.reject')" @click="moderateRegistration(registration, 'rejected')"><X :size="16" /></button>
            </article>
            <div v-if="!pendingRegistrations.length" class="empty-state">{{ t('championships.noPendingRequests') }}</div>
          </div>

          <div class="championship-add-pilot">
            <label class="field">
              <span>{{ t('championships.addPilot') }}</span>
              <span class="search-field">
                <Search :size="16" />
                <input v-model="pilotSearch" type="search" :placeholder="t('championships.pilotSearchPlaceholder')" />
              </span>
            </label>
            <label class="field">
              <span>{{ t('championships.pilot') }}</span>
              <select v-model="addPilotId" :disabled="pilotLoading || !pilotResults.length">
                <option value="">{{ t('championships.choosePilot') }}</option>
                <option v-for="pilot in pilotResults" :key="pilot.id" :value="pilot.id">{{ pilotTitle(pilot) }} - #{{ formatPilotNumber(pilot.pilot_number) }}</option>
              </select>
            </label>
            <label class="field">
              <span>{{ t('fields.pilotNumber') }}</span>
              <input v-model="addPilotNumber" inputmode="numeric" pattern="[0-9]{3}" minlength="3" maxlength="3" placeholder="000" required />
            </label>
            <label class="field">
              <span>{{ t('championships.car') }}</span>
              <select v-if="selectedAllowedCars.length" v-model="addPilotCar" required>
                <option value="" disabled>{{ t('championships.chooseCar') }}</option>
                <option v-for="car in selectedAllowedCars" :key="car" :value="car">{{ car }}</option>
              </select>
              <input v-else v-model="addPilotCar" maxlength="80" required />
            </label>
            <button class="button" type="button" :disabled="!addPilotId || !addPilotNumber || !addPilotCar" @click="addParticipant"><UserPlus :size="16" />{{ t('common.add') }}</button>
          </div>

          <div class="championship-participant-list">
            <article v-for="registration in approvedRegistrations" :key="registration.id" class="championship-participant-card">
              <UserAvatar mini :src="registration.user.avatar_url" :color="registration.user.avatar_color" :label="registrationPilotName(registration)" />
              <div>
                <strong>{{ registrationPilotName(registration) }}</strong>
                <small>{{ registrationPilotLine(registration) }}</small>
              </div>
              <select v-if="selectedAllowedCars.length" v-model="carDrafts[registration.user_id]" required>
                <option value="" disabled>{{ t('championships.chooseCar') }}</option>
                <option v-for="car in selectedAllowedCars" :key="car" :value="car">{{ car }}</option>
              </select>
              <input v-else v-model="carDrafts[registration.user_id]" maxlength="80" required />
              <button class="button small" type="button" @click="updateCar(registration.user_id)">{{ t('championships.car') }}</button>
              <button class="icon-button danger" type="button" :title="t('teams.removeMember')" @click="removeParticipant(registration.user_id)"><Trash2 :size="16" /></button>
            </article>
          </div>
        </section>

        <section class="card championship-standings">
          <div class="section-header compact">
            <h3>{{ t('championships.standings') }}</h3>
            <span class="pill">{{ standings.length }}</span>
          </div>
          <div v-if="standings.length" class="race-results-podium championship-podium">
            <article
              v-for="(pilot, index) in standings.slice(0, 3)"
              :key="`championship-podium-${pilot.user_id}`"
              class="result-podium-card"
              :class="podiumRankClass(index + 1)"
            >
              <span class="result-position-badge" :class="podiumRankClass(index + 1)">{{ index + 1 }}</span>
              <div>
                <span class="user-name-line">
                  <strong>{{ pilotTitle(pilot) }}</strong>
                  <LicenseBadge :user="pilot" :game="selected.game" />
                </span>
                <span>#{{ formatPilotNumber(pilot.pilot_number) }} - {{ teamShortName(pilot.team_name, pilot.team_abbreviation) || t('championships.noTeam') }}</span>
              </div>
              <strong class="result-podium-time">{{ pilot.points }}</strong>
            </article>
          </div>
          <div class="championship-table-scroll">
            <table class="hall-table championship-results-table">
              <thead>
                <tr>
                  <th>{{ t('championships.position') }}</th>
                  <th>{{ t('championships.pilot') }}</th>
                  <th>{{ t('championships.team') }}</th>
                  <th>{{ t('championships.points') }}</th>
                  <th>{{ t('championships.pole') }}</th>
                  <th>{{ t('championships.starts') }}</th>
                  <th>{{ t('championships.car') }}</th>
                  <th>RER</th>
                  <th>SR</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(pilot, index) in pagedStandings" :key="pilot.user_id" :class="podiumRankClass((standingsPage - 1) * standingsPageSize + index + 1)">
                  <td>
                    <span class="result-position-badge" :class="podiumRankClass((standingsPage - 1) * standingsPageSize + index + 1)">
                      {{ (standingsPage - 1) * standingsPageSize + index + 1 }}
                    </span>
                  </td>
                  <td>
                    <div class="hall-person-cell">
                      <UserAvatar mini :src="pilot.avatar_url" :color="pilot.avatar_color" :label="pilotTitle(pilot)" />
                      <RouterLink class="hall-title" :to="`/pilots/${pilot.user_id}`">
                        <span class="user-name-line">
                          <strong>{{ pilotTitle(pilot) }}</strong>
                          <LicenseBadge :user="pilot" :game="selected.game" />
                        </span>
                        <span>#{{ formatPilotNumber(pilot.pilot_number) }} - {{ pilot.nickname || pilot.login }}</span>
                      </RouterLink>
                    </div>
                  </td>
                  <td>
                    <RouterLink v-if="pilot.team_id" class="team-mini-chip team-link-chip" :to="teamHref(pilot.team_id)" :title="pilot.team_name || t('common.none')">
                      {{ teamShortName(pilot.team_name, pilot.team_abbreviation) }}
                    </RouterLink>
                    <span v-else class="team-mini-chip">{{ teamShortName(pilot.team_name, pilot.team_abbreviation) }}</span>
                  </td>
                  <td><strong>{{ pilot.points }}</strong></td>
                  <td>{{ pilot.pole_points }}</td>
                  <td>{{ pilot.starts }}</td>
                  <td>{{ championshipCar(pilot.user_id) }}</td>
                  <td>{{ formatRating(ratingForGame(pilot, selected.game)) }}</td>
                  <td>{{ Number(pilot.sr).toFixed(1) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="!standings.length" class="empty-state">{{ t('championships.standingsEmpty') }}</div>
          <PaginationControls v-model:page="standingsPage" :page-size="standingsPageSize" :total-items="standings.length" />
        </section>
      </article>
    </div>
  </section>
</template>
