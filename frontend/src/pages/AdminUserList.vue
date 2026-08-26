<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Ban, Edit3, Plus, Save, Timer, TimerOff, Trash2, Undo2, Upload, X } from 'lucide-vue-next'
import { api } from '../api'
import { brandingSettings, setBrandingSettings } from '../brandingSettings'
import AvatarViewer from '../components/AvatarViewer.vue'
import AuditLogPanel from '../components/AuditLogPanel.vue'
import CountryCombobox from '../components/CountryCombobox.vue'
import GameCheckboxGroup from '../components/GameCheckboxGroup.vue'
import ImageCropper from '../components/ImageCropper.vue'
import LicenseBadge from '../components/LicenseBadge.vue'
import PaginationControls from '../components/PaginationControls.vue'
import RaceAssetsEditor from '../components/RaceAssetsEditor.vue'
import UserAvatar from '../components/UserAvatar.vue'
import { countryOptionsWithCurrent } from '../countries'
import { gameOptions, roleLabel, statusLabel } from '../i18nLabels'
import { isGifFile } from '../media'
import { setLicenseTiers } from '../licenseSettings'
import { DEFAULT_LICENSE_TIERS, formatPilotNumber, formatRating, licenseBadgeStyle, normalizeLicenseTiers, ratingForGame, teamShortName } from '../pilotDisplay'
import { setSession, state } from '../store'

const { t } = useI18n()
const users = ref([])
const roles = ['admin', 'moder', 'marshall', 'smm', 'pilot']
const error = ref('')
const busyUsers = ref({})
const timeoutDialogUser = ref(null)
const timeoutUntil = ref('')
const timeoutSaving = ref(false)
const editDialogUser = ref(null)
const editForm = ref({})
const editSaving = ref(false)
const editAvatarFile = ref(null)
const editAvatarSaving = ref(false)
const editAvatarViewerOpen = ref(false)
const teamLimit = ref(5)
const teamLimitSaving = ref(false)
const settingsSaved = ref(false)
const fanVoteDurationHours = ref(24)
const fanVoteSaving = ref(false)
const fanVoteSaved = ref(false)
const twitchConfig = ref({ fallback_video_url: '', fallback_video_title: '' })
const twitchConfigSaving = ref(false)
const twitchConfigSaved = ref(false)
const donationSettings = ref({ donation_url: '', top_donations: [] })
const donationSaving = ref(false)
const donationSaved = ref(false)
const licenseTiers = ref(DEFAULT_LICENSE_TIERS)
const licenseSaving = ref(false)
const licenseSaved = ref(false)
const systemSettings = ref({ requests_per_user_per_minute: 1200, rating_change_coefficient: 1.5, sr_per_race: 0.3 })
const systemSettingsSaving = ref(false)
const systemSettingsSaved = ref(false)
const logoFiles = ref({ light: null, dark: null })
const logoSaving = ref({ light: false, dark: false })
const logoSaved = ref({ light: false, dark: false })
const logoCropper = ref(null)
const defaultAvatarFile = ref(null)
const defaultAvatarSaving = ref(false)
const defaultAvatarSaved = ref(false)
const defaultAvatarCropper = ref(null)
const weatherImages = ref({
  clear_light_url: '', clear_dark_url: '',
  partly_cloudy_light_url: '', partly_cloudy_dark_url: '',
  overcast_light_url: '', overcast_dark_url: '',
  light_rain_light_url: '', light_rain_dark_url: '',
  heavy_rain_light_url: '', heavy_rain_dark_url: '',
  storm_light_url: '', storm_dark_url: ''
})
const weatherImageFiles = ref({})
const weatherImageSaving = ref({})
const weatherImageSaved = ref({})
const dangerDialog = ref(null)
const dangerForm = ref({ confirmation: '', confirmation_repeat: '', password: '' })
const dangerSaving = ref(false)
const dangerResult = ref('')
const userSearch = ref('')
const userSort = ref('rating_desc')
const userRatingGame = ref('ACC')
const page = ref(1)
const pageSize = 25
const visibleUsers = computed(() => users.value)
const hasNextPage = computed(() => users.value.length === pageSize)
const canUseDangerZone = computed(() => state.user?.is_system_admin === true)
const editCountries = computed(() => countryOptionsWithCurrent(state.locale, editForm.value.country || ''))
const weatherConditions = computed(() => [
  { key: 'clear', label: t('weather.clear') },
  { key: 'partly_cloudy', label: t('weather.partlyCloudy') },
  { key: 'overcast', label: t('weather.overcast') },
  { key: 'light_rain', label: t('weather.lightRain') },
  { key: 'heavy_rain', label: t('weather.heavyRain') },
  { key: 'storm', label: t('weather.storm') }
])
const dangerActions = {
  pilots: {
    endpoint: '/users/admin/delete-pilots',
    code: 'DELETE PILOTS',
    titleKey: 'adminUsers.deleteAllPilots',
    descriptionKey: 'adminUsers.deleteAllPilotsHint'
  },
  races: {
    endpoint: '/users/admin/delete-races',
    code: 'DELETE RACES',
    titleKey: 'adminUsers.deleteAllRaces',
    descriptionKey: 'adminUsers.deleteAllRacesHint'
  }
}
const activeDangerAction = computed(() => (dangerDialog.value ? dangerActions[dangerDialog.value] : null))
const dangerFormValid = computed(() => {
  const action = activeDangerAction.value
  if (!action) return false
  return (
    dangerForm.value.confirmation.trim() === action.code &&
    dangerForm.value.confirmation_repeat.trim() === action.code &&
    dangerForm.value.password.length > 0
  )
})

function datetimeLocalValue(date) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
  return local.toISOString().slice(0, 16)
}

function defaultTimeoutUntil() {
  return datetimeLocalValue(new Date(Date.now() + 24 * 60 * 60 * 1000))
}

function timeoutMin() {
  return datetimeLocalValue(new Date(Date.now() + 60 * 1000))
}

function formatDateTime(value) {
  if (!value) return t('common.none')
  return new Intl.DateTimeFormat(state.locale === 'ru' ? 'ru-RU' : 'en-US', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone: state.timeZone
  }).format(new Date(value))
}

function emptyDonationEntry() {
  return { name: '', amount: '', message: '' }
}

function normalizeDonationSettings(data = {}) {
  return {
    donation_url: data.donation_url || '',
    top_donations: (data.top_donations?.length ? data.top_donations : [emptyDonationEntry()]).map((item) => ({
      name: item.name || '',
      amount: item.amount || '',
      message: item.message || ''
    }))
  }
}

function licenseRange(tier) {
  return `${String(tier.min_rating).padStart(4, '0')}-${String(tier.max_rating).padStart(4, '0')}`
}

async function load() {
  try {
    const params = new URLSearchParams({
      limit: String(pageSize),
      offset: String((page.value - 1) * pageSize),
      sort: userSort.value,
      rating_game: userRatingGame.value
    })
    if (userSearch.value.trim()) params.set('search', userSearch.value.trim())
    const [loadedUsers, teamConfig, fanVoteConfig, loadedTwitchConfig, loadedDonationSettings, loadedLicenseSettings, loadedBrandingSettings, loadedSystemSettings, loadedWeatherImages] = await Promise.all([
      api(`/users/admin?${params.toString()}`),
      api('/teams/config'),
      api('/races/fan-vote/config'),
      api('/twitch/config'),
      api('/app-settings/donations'),
      api('/app-settings/licenses'),
      api('/app-settings/branding'),
      api('/app-settings/system'),
      api('/app-settings/weather').catch(() => ({
        clear_light_url: '', clear_dark_url: '',
        partly_cloudy_light_url: '', partly_cloudy_dark_url: '',
        overcast_light_url: '', overcast_dark_url: '',
        light_rain_light_url: '', light_rain_dark_url: '',
        heavy_rain_light_url: '', heavy_rain_dark_url: '',
        storm_light_url: '', storm_dark_url: ''
      }))
    ])
    users.value = loadedUsers
    teamLimit.value = teamConfig.member_limit
    fanVoteDurationHours.value = fanVoteConfig.duration_hours
    twitchConfig.value = {
      fallback_video_url: loadedTwitchConfig.fallback_video_url || '',
      fallback_video_title: loadedTwitchConfig.fallback_video_title || ''
    }
    donationSettings.value = normalizeDonationSettings(loadedDonationSettings)
    licenseTiers.value = normalizeLicenseTiers(loadedLicenseSettings)
    setBrandingSettings(loadedBrandingSettings)
    systemSettings.value = {
      requests_per_user_per_minute: loadedSystemSettings.requests_per_user_per_minute,
      rating_change_coefficient: loadedSystemSettings.rating_change_coefficient,
      sr_per_race: loadedSystemSettings.sr_per_race
    }
    weatherImages.value = loadedWeatherImages
  } catch (err) {
    error.value = err.message
  }
}

function resetUserPageAndLoad() {
  if (page.value === 1) {
    load()
    return
  }
  page.value = 1
}

async function saveTeamLimit() {
  teamLimitSaving.value = true
  settingsSaved.value = false
  error.value = ''
  try {
    const config = await api('/teams/config', {
      method: 'PATCH',
      body: { member_limit: Number(teamLimit.value) }
    })
    teamLimit.value = config.member_limit
    settingsSaved.value = true
  } catch (err) {
    error.value = err.message
  } finally {
    teamLimitSaving.value = false
  }
}

async function saveFanVoteConfig() {
  fanVoteSaving.value = true
  fanVoteSaved.value = false
  error.value = ''
  try {
    const config = await api('/races/fan-vote/config', {
      method: 'PATCH',
      body: { duration_hours: Number(fanVoteDurationHours.value) }
    })
    fanVoteDurationHours.value = config.duration_hours
    fanVoteSaved.value = true
  } catch (err) {
    error.value = err.message
  } finally {
    fanVoteSaving.value = false
  }
}

async function saveTwitchConfig() {
  twitchConfigSaving.value = true
  twitchConfigSaved.value = false
  error.value = ''
  try {
    const config = await api('/twitch/config', {
      method: 'PATCH',
      body: {
        fallback_video_url: twitchConfig.value.fallback_video_url.trim(),
        fallback_video_title: twitchConfig.value.fallback_video_title.trim()
      }
    })
    twitchConfig.value = {
      fallback_video_url: config.fallback_video_url || '',
      fallback_video_title: config.fallback_video_title || ''
    }
    twitchConfigSaved.value = true
  } catch (err) {
    error.value = err.message
  } finally {
    twitchConfigSaving.value = false
  }
}

function addDonationEntry() {
  if (donationSettings.value.top_donations.length >= 5) return
  donationSettings.value.top_donations = [...donationSettings.value.top_donations, emptyDonationEntry()]
}

function removeDonationEntry(index) {
  const nextItems = donationSettings.value.top_donations.filter((_, itemIndex) => itemIndex !== index)
  donationSettings.value.top_donations = nextItems.length ? nextItems : [emptyDonationEntry()]
}

async function saveDonationSettings() {
  donationSaving.value = true
  donationSaved.value = false
  error.value = ''
  try {
    const payload = {
      donation_url: donationSettings.value.donation_url.trim(),
      top_donations: donationSettings.value.top_donations
        .map((item) => ({
          name: item.name.trim(),
          amount: item.amount.trim(),
          message: item.message.trim()
        }))
        .filter((item) => item.name && item.amount)
    }
    donationSettings.value = normalizeDonationSettings(await api('/app-settings/donations', {
      method: 'PATCH',
      body: payload
    }))
    donationSaved.value = true
  } catch (err) {
    error.value = err.message
  } finally {
    donationSaving.value = false
  }
}

async function saveLicenseSettings() {
  licenseSaving.value = true
  licenseSaved.value = false
  error.value = ''
  try {
    licenseTiers.value = setLicenseTiers(await api('/app-settings/licenses', {
      method: 'PATCH',
      body: {
        tiers: licenseTiers.value.map((tier) => ({
          name: String(tier.name || '').trim(),
          color: tier.color
        }))
      }
    }))
    licenseSaved.value = true
  } catch (err) {
    error.value = err.message
  } finally {
    licenseSaving.value = false
  }
}

async function saveSystemSettings() {
  systemSettingsSaving.value = true
  systemSettingsSaved.value = false
  error.value = ''
  try {
    const saved = await api('/app-settings/system', {
      method: 'PATCH',
      body: {
        requests_per_user_per_minute: Number(systemSettings.value.requests_per_user_per_minute),
        rating_change_coefficient: Number(systemSettings.value.rating_change_coefficient),
        sr_per_race: Number(systemSettings.value.sr_per_race)
      }
    })
    systemSettings.value = saved
    systemSettingsSaved.value = true
  } catch (err) {
    error.value = err.message
  } finally {
    systemSettingsSaving.value = false
  }
}

function setLogoFile(theme, event) {
  const file = event.target.files?.[0] || null
  event.target.value = ''
  logoSaved.value = { ...logoSaved.value, [theme]: false }
  if (!file) return
  if (isGifFile(file)) {
    logoFiles.value = { ...logoFiles.value, [theme]: file }
    return
  }
  closeLogoCropper()
  logoFiles.value = { ...logoFiles.value, [theme]: null }
  logoCropper.value = { theme, sourceUrl: URL.createObjectURL(file), error: '' }
}

async function saveLogo(theme, file) {
  logoSaving.value = { ...logoSaving.value, [theme]: true }
  logoSaved.value = { ...logoSaved.value, [theme]: false }
  error.value = ''
  try {
    const formData = new FormData()
    formData.append('file', file)
    setBrandingSettings(await api(`/app-settings/branding/${theme}/upload`, {
      method: 'POST',
      body: formData
    }))
    logoFiles.value = { ...logoFiles.value, [theme]: null }
    logoSaved.value = { ...logoSaved.value, [theme]: true }
    return true
  } catch (err) {
    error.value = err.message
    if (logoCropper.value?.theme === theme) {
      logoCropper.value = { ...logoCropper.value, error: err.message }
    }
    return false
  } finally {
    logoSaving.value = { ...logoSaving.value, [theme]: false }
  }
}

async function uploadLogo(theme) {
  const file = logoFiles.value[theme]
  if (file) await saveLogo(theme, file)
}

async function uploadCroppedLogo(blob) {
  const theme = logoCropper.value?.theme
  if (!theme) return
  if (await saveLogo(theme, new File([blob], `${theme}-logo.webp`, { type: 'image/webp' }))) {
    closeLogoCropper()
  }
}

function closeLogoCropper() {
  if (!logoCropper.value || logoSaving.value[logoCropper.value.theme]) return
  URL.revokeObjectURL(logoCropper.value.sourceUrl)
  logoCropper.value = null
}

function setDefaultAvatarFile(event) {
  const file = event.target.files?.[0] || null
  event.target.value = ''
  defaultAvatarSaved.value = false
  if (!file) return
  if (isGifFile(file)) {
    defaultAvatarFile.value = file
    return
  }
  closeDefaultAvatarCropper()
  defaultAvatarFile.value = null
  defaultAvatarCropper.value = { sourceUrl: URL.createObjectURL(file), error: '' }
}

async function saveDefaultAvatar(file) {
  defaultAvatarSaving.value = true
  defaultAvatarSaved.value = false
  error.value = ''
  try {
    const formData = new FormData()
    formData.append('file', file)
    setBrandingSettings(await api('/app-settings/branding/default-avatar/upload', {
      method: 'POST',
      body: formData
    }))
    defaultAvatarFile.value = null
    defaultAvatarSaved.value = true
    return true
  } catch (err) {
    error.value = err.message
    if (defaultAvatarCropper.value) defaultAvatarCropper.value = { ...defaultAvatarCropper.value, error: err.message }
    return false
  } finally {
    defaultAvatarSaving.value = false
  }
}

async function uploadDefaultAvatar() {
  if (defaultAvatarFile.value) await saveDefaultAvatar(defaultAvatarFile.value)
}

function setWeatherImageFile(condition, theme, event) {
  const fileKey = `${condition}_${theme}`
  const file = event.target.files?.[0] || null
  event.target.value = ''
  weatherImageSaved.value = { ...weatherImageSaved.value, [fileKey]: false }
  if (file) weatherImageFiles.value = { ...weatherImageFiles.value, [fileKey]: file }
}

async function uploadWeatherImage(condition, theme) {
  const fileKey = `${condition}_${theme}`
  const file = weatherImageFiles.value[fileKey]
  if (!file) return
  weatherImageSaving.value = { ...weatherImageSaving.value, [fileKey]: true }
  weatherImageSaved.value = { ...weatherImageSaved.value, [fileKey]: false }
  error.value = ''
  try {
    const formData = new FormData()
    formData.append('file', file)
    weatherImages.value = await api(`/app-settings/weather/${condition}/${theme}/upload`, {
      method: 'POST',
      body: formData
    })
    weatherImageFiles.value = { ...weatherImageFiles.value, [fileKey]: null }
    weatherImageSaved.value = { ...weatherImageSaved.value, [fileKey]: true }
  } catch (err) {
    error.value = err.message
  } finally {
    weatherImageSaving.value = { ...weatherImageSaving.value, [fileKey]: false }
  }
}

async function uploadCroppedDefaultAvatar(blob) {
  if (await saveDefaultAvatar(new File([blob], 'default-avatar.webp', { type: 'image/webp' }))) {
    closeDefaultAvatarCropper()
  }
}

function closeDefaultAvatarCropper() {
  if (!defaultAvatarCropper.value || defaultAvatarSaving.value) return
  URL.revokeObjectURL(defaultAvatarCropper.value.sourceUrl)
  defaultAvatarCropper.value = null
}

function openDangerDialog(type) {
  dangerDialog.value = type
  dangerForm.value = { confirmation: '', confirmation_repeat: '', password: '' }
  dangerResult.value = ''
}

function closeDangerDialog() {
  if (dangerSaving.value) return
  dangerDialog.value = null
  dangerForm.value = { confirmation: '', confirmation_repeat: '', password: '' }
}

async function runDangerAction() {
  const action = activeDangerAction.value
  if (!action || !dangerFormValid.value) return
  dangerSaving.value = true
  error.value = ''
  dangerResult.value = ''
  try {
    const result = await api(action.endpoint, {
      method: 'POST',
      body: {
        confirmation: dangerForm.value.confirmation,
        confirmation_repeat: dangerForm.value.confirmation_repeat,
        password: dangerForm.value.password
      }
    })
    dangerResult.value = t('adminUsers.deletedCount', { count: result?.deleted ?? 0 })
    dangerDialog.value = null
    dangerForm.value = { confirmation: '', confirmation_repeat: '', password: '' }
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    dangerSaving.value = false
  }
}

async function chooseRole(user, role) {
  if (user.role === role) return
  const previousRole = user.role
  busyUsers.value = { ...busyUsers.value, [user.id]: true }
  try {
    user.role = role
    await api(`/users/${user.id}/role`, { method: 'PATCH', body: { role } })
  } catch (err) {
    user.role = previousRole
    error.value = err.message
  } finally {
    busyUsers.value = { ...busyUsers.value, [user.id]: false }
  }
}

async function ban(user) {
  if (user.is_system_admin || user.role === 'admin') return
  busyUsers.value = { ...busyUsers.value, [user.id]: true }
  try {
    await api(`/users/${user.id}/ban`, { method: 'POST' })
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    busyUsers.value = { ...busyUsers.value, [user.id]: false }
  }
}

async function unban(user) {
  if (user.is_system_admin) return
  busyUsers.value = { ...busyUsers.value, [user.id]: true }
  try {
    await api(`/users/${user.id}/unban`, { method: 'POST' })
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    busyUsers.value = { ...busyUsers.value, [user.id]: false }
  }
}

function openTimeoutDialog(user) {
  if (user.is_system_admin || user.role === 'admin') return
  timeoutDialogUser.value = user
  timeoutUntil.value = user.timeout_end ? datetimeLocalValue(new Date(user.timeout_end)) : defaultTimeoutUntil()
}

function closeTimeoutDialog() {
  if (timeoutSaving.value) return
  timeoutDialogUser.value = null
  timeoutUntil.value = ''
}

function openEditDialog(user) {
  if (user.is_system_admin) return
  editDialogUser.value = user
  const gameRatings = Object.fromEntries(gameOptions(t).map((option) => [
    option.value,
    Number(user.game_ratings?.[option.value]?.rating ?? user.rating ?? 1000)
  ]))
  editForm.value = {
    login: user.login || '',
    email: user.email || '',
    first_name: user.first_name || '',
    last_name: user.last_name || '',
    nickname: user.nickname || '',
    pilot_number: formatPilotNumber(user.pilot_number),
    country: user.country || '',
    discord: user.discord || '',
    games: user.games?.length ? [...user.games] : ['ACC'],
    sr: Number(user.sr ?? 5),
    rating: Number(user.rating ?? 1000),
    game_ratings: gameRatings
  }
  editAvatarFile.value = null
}

function closeEditDialog() {
  if (editSaving.value || editAvatarSaving.value) return
  editDialogUser.value = null
  editAvatarViewerOpen.value = false
  editAvatarFile.value = null
}

function setEditAvatarFile(event) {
  editAvatarFile.value = event.target.files?.[0] || null
}

function updateUserInList(updatedUser) {
  users.value = users.value.map((item) => (item.id === updatedUser.id ? updatedUser : item))
  if (updatedUser.id === state.user?.id) {
    setSession(state.token, updatedUser)
  }
}

async function saveUserProfile() {
  if (!editDialogUser.value) return
  editSaving.value = true
  error.value = ''
  try {
    const updatedUser = await api(`/users/${editDialogUser.value.id}`, {
      method: 'PATCH',
      body: {
        login: editForm.value.login,
        email: editForm.value.email,
        first_name: editForm.value.first_name,
        last_name: editForm.value.last_name,
        nickname: editForm.value.nickname,
        pilot_number: Number(editForm.value.pilot_number),
        country: editForm.value.country || null,
        discord: editForm.value.discord || null,
        games: editForm.value.games,
        sr: Number(editForm.value.sr),
        rating: Number(editForm.value.rating),
        game_ratings: Object.fromEntries(Object.entries(editForm.value.game_ratings || {}).map(([game, rating]) => [game, Number(rating)]))
      }
    })
    updateUserInList(updatedUser)
    editDialogUser.value = updatedUser
  } catch (err) {
    error.value = err.message
  } finally {
    editSaving.value = false
  }
}

async function uploadEditAvatar() {
  if (!editDialogUser.value || editDialogUser.value.is_system_admin || !editAvatarFile.value) return
  editAvatarSaving.value = true
  error.value = ''
  try {
    const payload = new FormData()
    payload.append('file', editAvatarFile.value)
    const updatedUser = await api(`/users/${editDialogUser.value.id}/avatar`, {
      method: 'POST',
      body: payload
    })
    updateUserInList(updatedUser)
    editDialogUser.value = updatedUser
    editAvatarFile.value = null
  } catch (err) {
    error.value = err.message
  } finally {
    editAvatarSaving.value = false
  }
}

async function issueTimeout() {
  const user = timeoutDialogUser.value
  if (!user) return
  const timeoutEnd = new Date(timeoutUntil.value)
  if (Number.isNaN(timeoutEnd.getTime()) || timeoutEnd <= new Date()) {
    error.value = t('adminUsers.timeoutInvalid')
    return
  }
  timeoutSaving.value = true
  busyUsers.value = { ...busyUsers.value, [user.id]: true }
  try {
    await api(`/users/${user.id}/timeout`, { method: 'POST', body: { timeout_end: timeoutEnd.toISOString() } })
    await load()
    timeoutDialogUser.value = null
    timeoutUntil.value = ''
  } catch (err) {
    error.value = err.message
  } finally {
    timeoutSaving.value = false
    busyUsers.value = { ...busyUsers.value, [user.id]: false }
  }
}

async function endTimeout(user) {
  if (user.is_system_admin || user.status !== 'timeout') return
  busyUsers.value = { ...busyUsers.value, [user.id]: true }
  try {
    await api(`/users/${user.id}/timeout`, { method: 'DELETE' })
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    busyUsers.value = { ...busyUsers.value, [user.id]: false }
  }
}

async function deleteAccount(user) {
  if (user.is_system_admin || user.id === state.user?.id) return
  if (!window.confirm(t('adminUsers.deleteConfirm', { login: user.login }))) return
  busyUsers.value = { ...busyUsers.value, [user.id]: true }
  try {
    await api(`/users/${user.id}`, { method: 'DELETE' })
    users.value = users.value.filter((item) => item.id !== user.id)
  } catch (err) {
    error.value = err.message
  } finally {
    busyUsers.value = { ...busyUsers.value, [user.id]: false }
  }
}

onMounted(load)
onBeforeUnmount(() => {
  closeLogoCropper()
  closeDefaultAvatarCropper()
})
watch(page, load)
watch([userSearch, userSort, userRatingGame], resetUserPageAndLoad)
</script>

<template>
  <section class="section admin-users-page">
    <div class="section-header">
      <h1>{{ t('nav.admin') }}</h1>
    </div>
    <p v-if="error" class="error">{{ error }}</p>

    <!-- Loading/empty states are N/A: bundled logos are always available as immediate defaults. -->
    <section class="admin-settings-card admin-logo-config-card card">
      <div>
        <h2>{{ t('adminUsers.logoTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.logoHint') }}</p>
      </div>
      <article v-for="theme in ['light', 'dark']" :key="theme" class="admin-logo-option">
        <div class="admin-logo-preview" :class="`is-${theme}`">
          <img :src="brandingSettings[`${theme}_logo_url`]" alt="" />
        </div>
        <label class="field">
          <span>{{ t(`adminUsers.${theme}Logo`) }}</span>
          <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" @change="setLogoFile(theme, $event)" />
        </label>
        <button class="button primary" type="button" :disabled="logoSaving[theme] || !logoFiles[theme]" @click="uploadLogo(theme)">
          <Upload :size="16" />
          {{ t('common.upload') }}
        </button>
        <span v-if="logoSaved[theme]" class="pill">{{ t('common.saved') }}</span>
      </article>
    </section>

    <ImageCropper
      v-if="logoCropper"
      :source-url="logoCropper.sourceUrl"
      :title="t('adminUsers.logoCropTitle')"
      :hint="t('adminUsers.logoCropHint')"
      :target-width="780"
      :target-height="200"
      :saving="logoSaving[logoCropper.theme]"
      :error="logoCropper.error"
      @close="closeLogoCropper"
      @crop="uploadCroppedLogo"
    />

    <section class="admin-settings-card admin-avatar-config-card card">
      <div>
        <h2>{{ t('adminUsers.defaultAvatarTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.defaultAvatarHint') }}</p>
      </div>
      <div class="admin-default-avatar-preview">
        <UserAvatar :src="brandingSettings.default_avatar_url" :label="t('adminUsers.defaultAvatarTitle')" />
      </div>
      <label class="field">
        <span>{{ t('adminUsers.defaultAvatarField') }}</span>
        <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" @change="setDefaultAvatarFile" />
      </label>
      <button class="button primary" type="button" :disabled="defaultAvatarSaving || !defaultAvatarFile" @click="uploadDefaultAvatar">
        <Upload :size="16" />
        {{ t('common.upload') }}
      </button>
      <span v-if="defaultAvatarSaved" class="pill">{{ t('common.saved') }}</span>
    </section>

    <ImageCropper
      v-if="defaultAvatarCropper"
      :source-url="defaultAvatarCropper.sourceUrl"
      :title="t('adminUsers.defaultAvatarCropTitle')"
      :hint="t('adminUsers.defaultAvatarCropHint')"
      :target-width="320"
      :target-height="320"
      :saving="defaultAvatarSaving"
      :error="defaultAvatarCropper.error"
      @close="closeDefaultAvatarCropper"
      @crop="uploadCroppedDefaultAvatar"
    />

    <section class="admin-settings-card admin-weather-config-card card">
      <div>
        <h2>{{ t('adminUsers.weatherImagesTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.weatherImagesHint') }}</p>
      </div>
      <div class="admin-weather-image-grid">
        <article v-for="condition in weatherConditions" :key="condition.key" class="admin-weather-image-option">
          <h3>{{ condition.label }}</h3>
          <div class="admin-weather-theme-grid">
            <div v-for="theme in ['light', 'dark']" :key="theme" class="admin-weather-theme-option">
              <div class="admin-weather-image-preview">
                <img v-if="weatherImages[`${condition.key}_${theme}_url`]" :src="weatherImages[`${condition.key}_${theme}_url`]" alt="" />
                <span v-else class="muted">{{ t('adminUsers.weatherImageEmpty') }}</span>
              </div>
              <label class="field">
                <span>{{ theme === 'light' ? t('common.lightTheme') : t('common.darkTheme') }}</span>
                <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" @change="setWeatherImageFile(condition.key, theme, $event)" />
              </label>
              <button class="button primary" type="button" :disabled="weatherImageSaving[`${condition.key}_${theme}`] || !weatherImageFiles[`${condition.key}_${theme}`]" @click="uploadWeatherImage(condition.key, theme)">
                <Upload :size="16" />
                {{ t('common.upload') }}
              </button>
              <span v-if="weatherImageSaved[`${condition.key}_${theme}`]" class="pill">{{ t('common.saved') }}</span>
            </div>
          </div>
        </article>
      </div>
    </section>

    <form class="admin-settings-card admin-system-config-card card" @submit.prevent="saveSystemSettings">
      <div>
        <h2>{{ t('adminUsers.systemTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.systemHint') }}</p>
      </div>
      <label class="field">
        <span>{{ t('adminUsers.rateLimitField') }}</span>
        <input v-model.number="systemSettings.requests_per_user_per_minute" type="number" min="1" max="10000" required />
      </label>
      <label class="field">
        <span>{{ t('adminUsers.ratingCoefficientField') }}</span>
        <input v-model.number="systemSettings.rating_change_coefficient" type="number" min="0.01" max="10" step="0.01" required />
      </label>
      <label class="field">
        <span>{{ t('adminUsers.srPerRaceField') }}</span>
        <input v-model.number="systemSettings.sr_per_race" type="number" min="0" max="100" step="0.01" required />
      </label>
      <button class="button primary" type="submit" :disabled="systemSettingsSaving">
        <Save :size="16" />
        {{ t('common.save') }}
      </button>
      <span v-if="systemSettingsSaved" class="pill">{{ t('common.saved') }}</span>
    </form>

    <form class="admin-settings-card card" @submit.prevent="saveTeamLimit">
      <div>
        <h2>{{ t('adminUsers.teamLimitTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.teamLimitHint') }}</p>
      </div>
      <label class="field admin-team-limit-field">
        <span>{{ t('adminUsers.teamLimitField') }}</span>
        <input v-model.number="teamLimit" type="number" min="1" max="100" required />
      </label>
      <button class="button primary" type="submit" :disabled="teamLimitSaving">
        <Save :size="16" />
        {{ t('common.save') }}
      </button>
      <span v-if="settingsSaved" class="pill">{{ t('common.saved') }}</span>
    </form>

    <form class="admin-settings-card card" @submit.prevent="saveFanVoteConfig">
      <div>
        <h2>{{ t('adminUsers.fanVoteTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.fanVoteHint') }}</p>
      </div>
      <label class="field admin-team-limit-field">
        <span>{{ t('adminUsers.fanVoteDurationField') }}</span>
        <input v-model.number="fanVoteDurationHours" type="number" min="1" max="168" required />
      </label>
      <button class="button primary" type="submit" :disabled="fanVoteSaving">
        <Save :size="16" />
        {{ t('common.save') }}
      </button>
      <span v-if="fanVoteSaved" class="pill">{{ t('common.saved') }}</span>
    </form>

    <form class="admin-settings-card admin-twitch-config-card card" @submit.prevent="saveTwitchConfig">
      <div>
        <h2>{{ t('adminUsers.twitchFallbackTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.twitchFallbackHint') }}</p>
      </div>
      <label class="field admin-twitch-video-field">
        <span>{{ t('adminUsers.twitchFallbackUrl') }}</span>
        <input v-model="twitchConfig.fallback_video_url" type="text" placeholder="https://www.twitch.tv/videos/1234567890" />
      </label>
      <label class="field admin-twitch-video-field">
        <span>{{ t('adminUsers.twitchFallbackTitleField') }}</span>
        <input v-model="twitchConfig.fallback_video_title" type="text" maxlength="120" :placeholder="t('twitch.latestVideo')" />
      </label>
      <button class="button primary" type="submit" :disabled="twitchConfigSaving">
        <Save :size="16" />
        {{ t('common.save') }}
      </button>
      <span v-if="twitchConfigSaved" class="pill">{{ t('common.saved') }}</span>
    </form>

    <form class="admin-settings-card admin-license-config-card card" @submit.prevent="saveLicenseSettings">
      <div>
        <h2>{{ t('adminUsers.licenseTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.licenseHint') }}</p>
      </div>
      <div class="admin-license-list">
        <article v-for="tier in licenseTiers" :key="tier.min_rating" class="admin-license-row">
          <span class="admin-license-range">{{ licenseRange(tier) }}</span>
          <label class="field">
            <span>{{ t('fields.name') }}</span>
            <input v-model="tier.name" maxlength="30" required />
          </label>
          <label class="field admin-license-color-field">
            <span>{{ t('adminUsers.licenseColor') }}</span>
            <input v-model="tier.color" type="color" />
          </label>
          <span class="license-badge" :style="licenseBadgeStyle(tier)">{{ tier.name }}</span>
        </article>
      </div>
      <button class="button primary" type="submit" :disabled="licenseSaving">
        <Save :size="16" />
        {{ t('common.save') }}
      </button>
      <span v-if="licenseSaved" class="pill">{{ t('common.saved') }}</span>
    </form>

    <form class="admin-settings-card admin-donation-config-card card" @submit.prevent="saveDonationSettings">
      <div>
        <h2>{{ t('adminUsers.donationTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.donationHint') }}</p>
      </div>
      <label class="field admin-donation-url-field">
        <span>{{ t('adminUsers.donationUrl') }}</span>
        <input v-model="donationSettings.donation_url" type="url" placeholder="https://www.donationalerts.com/r/..." />
      </label>
      <div class="admin-donation-list">
        <div class="section-header compact">
          <h3>{{ t('main.topDonations') }}</h3>
          <button class="button small" type="button" :disabled="donationSettings.top_donations.length >= 5" @click="addDonationEntry">
            <Plus :size="14" />
            {{ t('adminUsers.addDonation') }}
          </button>
        </div>
        <article v-for="(donation, index) in donationSettings.top_donations" :key="index" class="admin-donation-row">
          <label class="field">
            <span>{{ t('adminUsers.donationName') }}</span>
            <input v-model="donation.name" maxlength="80" />
          </label>
          <label class="field">
            <span>{{ t('adminUsers.donationAmount') }}</span>
            <input v-model="donation.amount" maxlength="40" placeholder="1000 RUB" />
          </label>
          <label class="field">
            <span>{{ t('adminUsers.donationMessage') }}</span>
            <input v-model="donation.message" maxlength="120" />
          </label>
          <button class="icon-button danger-icon" type="button" :title="t('common.delete')" @click="removeDonationEntry(index)">
            <Trash2 :size="16" />
          </button>
        </article>
      </div>
      <button class="button primary" type="submit" :disabled="donationSaving">
        <Save :size="16" />
        {{ t('common.save') }}
      </button>
      <span v-if="donationSaved" class="pill">{{ t('common.saved') }}</span>
    </form>

    <RaceAssetsEditor @error="error = $event" />

    <AuditLogPanel />

    <section v-if="canUseDangerZone" class="admin-danger-card card">
      <div>
        <h2>{{ t('adminUsers.dangerTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.dangerHint') }}</p>
        <span v-if="dangerResult" class="pill">{{ dangerResult }}</span>
      </div>
      <div class="admin-danger-actions">
        <button class="button danger" type="button" @click="openDangerDialog('pilots')">
          <Trash2 :size="16" />
          {{ t('adminUsers.deleteAllPilots') }}
        </button>
        <button class="button danger" type="button" @click="openDangerDialog('races')">
          <Trash2 :size="16" />
          {{ t('adminUsers.deleteAllRaces') }}
        </button>
      </div>
    </section>

    <div class="admin-users-card card">
      <div class="pilot-inline-controls admin-users-controls">
        <input v-model="userSearch" type="search" :placeholder="t('common.search')" />
        <select v-model="userSort" :aria-label="t('common.sort')">
          <option value="rating_desc">{{ t('sort.ratingDesc') }}</option>
          <option value="rating_asc">{{ t('sort.ratingAsc') }}</option>
          <option value="sr_desc">{{ t('sort.srDesc') }}</option>
          <option value="sr_asc">{{ t('sort.srAsc') }}</option>
          <option value="alpha_asc">{{ t('sort.alphaAsc') }}</option>
          <option value="alpha_desc">{{ t('sort.alphaDesc') }}</option>
        </select>
        <select v-model="userRatingGame" :aria-label="t('fields.game')">
          <option v-for="option in gameOptions(t)" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
      </div>
      <table class="admin-users-table">
        <thead>
          <tr>
            <th>{{ t('fields.user') }}</th>
            <th>{{ t('common.role') }}</th>
            <th>{{ t('common.status') }}</th>
            <th>{{ t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in visibleUsers" :key="user.id">
            <td>
              <div class="admin-user-cell">
                <UserAvatar mini :src="user.avatar_url" :color="user.avatar_color" :label="user.login" />
                <div class="admin-user-info">
                  <span class="user-name-line">
                    <strong>{{ user.login }}</strong>
                    <LicenseBadge :user="user" :game="userRatingGame" />
                  </span>
                  <span>#{{ formatPilotNumber(user.pilot_number) }} · RER {{ formatRating(ratingForGame(user, userRatingGame)) }} · {{ teamShortName(user.team_name, user.team_abbreviation) }}</span>
                </div>
              </div>
            </td>
            <td>
              <div class="role-segment" :aria-label="t('common.role')">
                <button
                  v-for="role in roles"
                  :key="role"
                  class="role-segment-option"
                  :class="{ 'is-selected': user.role === role }"
                  type="button"
                  :disabled="user.is_system_admin || busyUsers[user.id]"
                  @click="chooseRole(user, role)"
                >
                  {{ roleLabel(t, role) }}
                </button>
              </div>
            </td>
            <td>
              <div class="admin-status-cell">
                <span class="status-badge" :class="`status-${user.status}`">
                  {{ statusLabel(t, user.status) }}
                </span>
                <span v-if="user.status === 'timeout' && user.timeout_end" class="admin-status-note">
                  {{ t('adminUsers.timeoutUntilShort', { date: formatDateTime(user.timeout_end) }) }}
                </span>
              </div>
            </td>
            <td>
              <div class="admin-actions">
                <button
                  class="icon-button"
                  type="button"
                  :title="t('common.edit')"
                  :aria-label="t('common.edit')"
                  :disabled="user.is_system_admin || busyUsers[user.id]"
                  @click="openEditDialog(user)"
                >
                  <Edit3 :size="16" />
                </button>
                <button
                  class="icon-button danger-icon"
                  type="button"
                  :title="t('common.ban')"
                  :aria-label="t('common.ban')"
                  :disabled="user.is_system_admin || user.role === 'admin' || busyUsers[user.id]"
                  @click="ban(user)"
                >
                  <Ban :size="16" />
                </button>
                <button
                  class="icon-button"
                  type="button"
                  :title="t('adminUsers.issueTimeout')"
                  :aria-label="t('adminUsers.issueTimeout')"
                  :disabled="user.is_system_admin || user.role === 'admin' || busyUsers[user.id]"
                  @click="openTimeoutDialog(user)"
                >
                  <Timer :size="16" />
                </button>
                <button
                  class="icon-button"
                  type="button"
                  :title="t('adminUsers.endTimeout')"
                  :aria-label="t('adminUsers.endTimeout')"
                  :disabled="user.is_system_admin || user.status !== 'timeout' || busyUsers[user.id]"
                  @click="endTimeout(user)"
                >
                  <TimerOff :size="16" />
                </button>
                <button
                  class="icon-button"
                  type="button"
                  :title="t('common.unban')"
                  :aria-label="t('common.unban')"
                  :disabled="user.is_system_admin || busyUsers[user.id]"
                  @click="unban(user)"
                >
                  <Undo2 :size="16" />
                </button>
                <button
                  class="icon-button danger-icon"
                  type="button"
                  :title="t('common.delete')"
                  :aria-label="t('common.delete')"
                  :disabled="user.is_system_admin || user.id === state.user?.id || busyUsers[user.id]"
                  @click="deleteAccount(user)"
                >
                  <Trash2 :size="16" />
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="!visibleUsers.length">
            <td colspan="4">
              <div class="empty-row">{{ t('adminUsers.empty') }}</div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <PaginationControls v-model:page="page" :page-size="pageSize" :loaded-count="visibleUsers.length" :has-next="hasNextPage" />

    <div v-if="activeDangerAction" class="penalty-modal-backdrop" @click.self="closeDangerDialog">
      <form class="penalty-modal admin-danger-modal card" @submit.prevent="runDangerAction">
        <div class="penalty-modal-head section-header">
          <div>
            <h2>{{ t(activeDangerAction.titleKey) }}</h2>
            <p>{{ t(activeDangerAction.descriptionKey) }}</p>
          </div>
          <button class="icon-button" type="button" :title="t('common.close')" :aria-label="t('common.close')" @click="closeDangerDialog">
            <X :size="18" />
          </button>
        </div>
        <p class="admin-danger-warning">{{ t('adminUsers.dangerModalHint', { phrase: activeDangerAction.code }) }}</p>
        <label class="field">
          <span>{{ t('adminUsers.confirmationOne') }}</span>
          <input v-model="dangerForm.confirmation" autocomplete="off" :placeholder="activeDangerAction.code" required />
        </label>
        <label class="field">
          <span>{{ t('adminUsers.confirmationTwo') }}</span>
          <input v-model="dangerForm.confirmation_repeat" autocomplete="off" :placeholder="activeDangerAction.code" required />
        </label>
        <label class="field">
          <span>{{ t('adminUsers.dangerPassword') }}</span>
          <input v-model="dangerForm.password" type="password" autocomplete="off" required />
        </label>
        <div class="admin-timeout-actions">
          <button class="button" type="button" :disabled="dangerSaving" @click="closeDangerDialog">
            <X :size="16" />
            {{ t('common.close') }}
          </button>
          <button class="button danger" type="submit" :disabled="dangerSaving || !dangerFormValid">
            <Trash2 :size="16" />
            {{ t('common.delete') }}
          </button>
        </div>
      </form>
    </div>

    <div v-if="timeoutDialogUser" class="penalty-modal-backdrop" @click.self="closeTimeoutDialog">
      <form class="penalty-modal admin-timeout-modal card" @submit.prevent="issueTimeout">
        <div class="penalty-modal-head">
          <h2>{{ t('adminUsers.timeoutTitle') }}</h2>
          <p>{{ t('adminUsers.timeoutUser', { login: timeoutDialogUser.login }) }}</p>
        </div>
        <label class="field">
          <span>{{ t('adminUsers.timeoutUntil') }}</span>
          <input v-model="timeoutUntil" type="datetime-local" :min="timeoutMin()" required />
        </label>
        <p class="admin-timeout-hint">{{ t('adminUsers.timeoutHint') }}</p>
        <div class="admin-timeout-actions">
          <button class="button" type="button" :disabled="timeoutSaving" @click="closeTimeoutDialog">
            <X :size="16" />
            {{ t('common.close') }}
          </button>
          <button class="button primary" type="submit" :disabled="timeoutSaving">
            <Timer :size="16" />
            {{ t('adminUsers.issueTimeout') }}
          </button>
        </div>
      </form>
    </div>

    <div v-if="editDialogUser" class="penalty-modal-backdrop" @click.self="closeEditDialog">
      <form class="penalty-modal admin-profile-modal card" @submit.prevent="saveUserProfile">
        <div class="penalty-modal-head section-header">
          <div>
            <h2>{{ t('adminUsers.editProfileTitle') }}</h2>
            <p>{{ editDialogUser.login }} · #{{ formatPilotNumber(editDialogUser.pilot_number) }}</p>
          </div>
          <button class="icon-button" type="button" :title="t('common.close')" :aria-label="t('common.close')" @click="closeEditDialog">
            <X :size="18" />
          </button>
        </div>

        <div class="avatar-edit-panel">
          <button class="avatar-open-button" type="button" :title="t('avatar.open')" @click="editAvatarViewerOpen = true">
            <UserAvatar :src="editDialogUser.avatar_url" :color="editDialogUser.avatar_color" :label="editDialogUser.nickname || editDialogUser.login" />
          </button>
          <div class="avatar-edit-main">
            <strong>{{ t('avatar.userTitle') }}</strong>
            <p class="muted">{{ t('avatar.userHint') }}</p>
            <div class="avatar-upload-row">
              <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" @change="setEditAvatarFile" />
              <button class="button" type="button" :disabled="editAvatarSaving || !editAvatarFile" @click="uploadEditAvatar">
                <Upload :size="16" />
                {{ t('common.upload') }}
              </button>
            </div>
          </div>
        </div>

        <div class="admin-profile-edit-grid">
          <label class="field">
            <span>{{ t('fields.login') }}</span>
            <input v-model="editForm.login" maxlength="50" required />
          </label>
          <label class="field">
            <span>{{ t('fields.email') }}</span>
            <input v-model="editForm.email" type="email" required />
          </label>
          <label class="field">
            <span>{{ t('fields.firstName') }}</span>
            <input v-model="editForm.first_name" maxlength="50" required />
          </label>
          <label class="field">
            <span>{{ t('fields.lastName') }}</span>
            <input v-model="editForm.last_name" maxlength="50" required />
          </label>
          <label class="field">
            <span>{{ t('fields.nickname') }}</span>
            <input v-model="editForm.nickname" maxlength="80" required />
          </label>
          <label class="field">
            <span>{{ t('fields.pilotNumber') }}</span>
            <input v-model="editForm.pilot_number" inputmode="numeric" pattern="[0-9]{3}" minlength="3" maxlength="3" placeholder="000" required />
          </label>
          <div class="field">
            <span>{{ t('fields.country') }}</span>
            <CountryCombobox v-model="editForm.country" :options="editCountries" />
          </div>
          <label class="field">
            <span>{{ t('fields.discord') }}</span>
            <input v-model="editForm.discord" maxlength="100" />
          </label>
          <label class="field">
            <span>{{ t('fields.sr') }}</span>
            <input v-model.number="editForm.sr" type="number" min="0" max="30" step="0.1" required />
          </label>
          <div class="field admin-profile-ratings">
            <span>{{ t('adminUsers.simulatorRatings') }}</span>
            <div class="admin-profile-ratings-grid">
              <label v-for="option in gameOptions(t)" :key="option.value" class="field">
                <span>{{ option.label }}</span>
                <input v-model.number="editForm.game_ratings[option.value]" type="number" min="10" max="10000" step="1" required />
              </label>
            </div>
          </div>
          <div class="field admin-profile-games is-required">
            <span>{{ t('fields.games') }}</span>
            <GameCheckboxGroup v-model="editForm.games" />
          </div>
        </div>

        <div class="admin-timeout-actions">
          <button class="button" type="button" :disabled="editSaving" @click="closeEditDialog">
            <X :size="16" />
            {{ t('common.close') }}
          </button>
          <button class="button primary" type="submit" :disabled="editSaving">
            <Save :size="16" />
            {{ t('common.save') }}
          </button>
        </div>
      </form>
      <AvatarViewer
        :open="editAvatarViewerOpen"
        :src="editDialogUser.avatar_url"
        :label="editDialogUser.nickname || editDialogUser.login"
        :fallback-color="editDialogUser.avatar_color"
        @close="editAvatarViewerOpen = false"
      />
    </div>
  </section>
</template>
