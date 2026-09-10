<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Ban, ChevronDown, Download, Edit3, Eye, Monitor, Plus, Save, Shield, Timer, TimerOff, Trash2, Undo2, Upload, X } from 'lucide-vue-next'
import { api, apiDownload } from '../api'
import { brandingSettings, setBrandingSettings } from '../brandingSettings'
import AvatarViewer from '../components/AvatarViewer.vue'
import AuditLogPanel from '../components/AuditLogPanel.vue'
import CountryCombobox from '../components/CountryCombobox.vue'
import GameCheckboxGroup from '../components/GameCheckboxGroup.vue'
import ImageCropper from '../components/ImageCropper.vue'
import LicenseBadge from '../components/LicenseBadge.vue'
import PaginationControls from '../components/PaginationControls.vue'
import PilotRoles from '../components/PilotRoles.vue'
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
const detailDialogUser = ref(null)
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
const systemSettings = ref({ requests_per_user_per_minute: 1200, requests_per_ip_per_minute: 1200, rating_change_coefficient: 1.5, sr_per_race: 0.3, show_setups_section: true })
const systemSettingsSaving = ref(false)
const systemSettingsSaved = ref(false)
const logoFiles = ref({ light: null, dark: null })
const logoSaving = ref({ light: false, dark: false })
const logoSaved = ref({ light: false, dark: false })
const logoCropper = ref(null)
const browserTitle = ref('BMRL Race Control')
const browserTitleSaving = ref(false)
const browserTitleSaved = ref(false)
const browserIconFile = ref(null)
const browserIconSaving = ref(false)
const browserIconSaved = ref(false)
const browserIconCropper = ref(null)
const defaultAvatarFile = ref(null)
const defaultAvatarSaving = ref(false)
const defaultAvatarSaved = ref(false)
const defaultAvatarCropper = ref(null)
const steamBlacklist = ref([])
const steamBlacklistForm = ref({ steam_id: '', reason: '' })
const steamBlacklistSaving = ref(false)
const steamBlacklistImporting = ref(false)
const steamBlacklistSaved = ref(false)
const steamBlacklistRowSaving = ref({})
const pilotRoles = ref([])
const pilotRoleForm = ref({ name: '', display_mode: 'text', border_color: '#2563eb' })
const pilotRoleImageFile = ref(null)
const pilotRoleImagePreview = ref('')
const pilotRoleCropper = ref(null)
const pilotRoleSaving = ref(false)
const pilotRoleDeleting = ref({})
const pilotRoleDialogUser = ref(null)
const pilotRoleSelection = ref([])
const pilotRoleAssignSaving = ref(false)
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
const collapsedAdminZones = ref({})
const dangerDialog = ref(null)
const dangerForm = ref({ confirmation: '', confirmation_repeat: '', password: '' })
const dangerSaving = ref(false)
const dangerResult = ref('')
const auditLogPanel = ref(null)
const userSearch = ref('')
const userSearchBy = ref('all')
const userSort = ref('rating_desc')
const userRatingGame = ref('ACC')
const page = ref(1)
const pageSize = 25
const visibleUsers = computed(() => users.value)
const userSearchOptions = computed(() => [
  { value: 'all', label: t('adminUsers.searchAll') },
  { value: 'id', label: t('adminUsers.searchAccountId') },
  { value: 'login', label: t('adminUsers.searchLogin') },
  { value: 'email', label: t('adminUsers.searchEmail') },
  { value: 'name', label: t('adminUsers.searchName') },
  { value: 'nickname', label: t('adminUsers.searchNickname') },
  { value: 'pilot_number', label: t('adminUsers.searchPilotNumber') },
  { value: 'steam_id', label: t('adminUsers.searchSteamId') },
  { value: 'device_id', label: t('adminUsers.searchDeviceId') },
  { value: 'device', label: t('adminUsers.searchDevice') },
  { value: 'team', label: t('adminUsers.searchTeam') },
  { value: 'country', label: t('adminUsers.searchCountry') },
  { value: 'role', label: t('adminUsers.searchRole') },
  { value: 'status', label: t('adminUsers.searchStatus') }
])
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
  },
  backup: {
    endpoint: '/users/admin/backup',
    code: 'DOWNLOAD DATABASE BACKUP',
    titleKey: 'adminUsers.downloadDatabaseBackup',
    descriptionKey: 'adminUsers.downloadDatabaseBackupHint',
    kind: 'download'
  },
  audit: {
    endpoint: '/audit/clear',
    code: 'CLEAR AUDIT LOGS',
    titleKey: 'adminUsers.auditClearTitle',
    descriptionKey: 'adminUsers.auditClearHint',
    resultKey: 'adminUsers.auditClearSuccess',
    submitKey: 'adminUsers.auditClear',
    kind: 'audit'
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
      rating_game: userRatingGame.value,
      search_by: userSearchBy.value
    })
    if (userSearch.value.trim()) params.set('search', userSearch.value.trim())
    const [loadedUsers, teamConfig, fanVoteConfig, loadedTwitchConfig, loadedDonationSettings, loadedLicenseSettings, loadedBrandingSettings, loadedSystemSettings, loadedWeatherImages, loadedSteamBlacklist, loadedPilotRoles] = await Promise.all([
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
      })),
      api('/users/admin/steam-blacklist'),
      api('/users/admin/pilot-roles').catch(() => [])
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
    browserTitle.value = brandingSettings.browser_title
    systemSettings.value = {
      requests_per_user_per_minute: loadedSystemSettings.requests_per_user_per_minute,
      requests_per_ip_per_minute: loadedSystemSettings.requests_per_ip_per_minute ?? loadedSystemSettings.requests_per_user_per_minute,
      rating_change_coefficient: loadedSystemSettings.rating_change_coefficient,
      sr_per_race: loadedSystemSettings.sr_per_race,
      show_setups_section: loadedSystemSettings.show_setups_section !== false
    }
    weatherImages.value = loadedWeatherImages
    steamBlacklist.value = loadedSteamBlacklist
    pilotRoles.value = loadedPilotRoles
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
        requests_per_ip_per_minute: Number(systemSettings.value.requests_per_ip_per_minute),
        rating_change_coefficient: Number(systemSettings.value.rating_change_coefficient),
        sr_per_race: Number(systemSettings.value.sr_per_race),
        show_setups_section: Boolean(systemSettings.value.show_setups_section)
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

async function loadSteamBlacklist() {
  steamBlacklist.value = await api('/users/admin/steam-blacklist')
}

async function addSteamBlacklistEntry() {
  const steamId = String(steamBlacklistForm.value.steam_id || '').trim()
  const reason = String(steamBlacklistForm.value.reason || '').trim()
  if (!/^\d+$/.test(steamId) || !reason) return
  steamBlacklistSaving.value = true
  steamBlacklistSaved.value = false
  error.value = ''
  try {
    const entry = await api('/users/admin/steam-blacklist', {
      method: 'POST',
      body: { steam_id: steamId, reason }
    })
    steamBlacklist.value = [entry, ...steamBlacklist.value.filter((item) => item.id !== entry.id)]
    steamBlacklistForm.value = { steam_id: '', reason: '' }
    steamBlacklistSaved.value = true
  } catch (err) {
    error.value = err.message
  } finally {
    steamBlacklistSaving.value = false
  }
}

async function saveSteamBlacklistEntry(entry) {
  const reason = String(entry.reason || '').trim()
  if (!/^\d+$/.test(String(entry.steam_id || '').trim()) || !reason) return
  steamBlacklistRowSaving.value = { ...steamBlacklistRowSaving.value, [entry.id]: true }
  error.value = ''
  try {
    const saved = await api(`/users/admin/steam-blacklist/${entry.id}`, {
      method: 'PATCH',
      body: { steam_id: String(entry.steam_id).trim(), reason }
    })
    steamBlacklist.value = steamBlacklist.value.map((item) => (item.id === saved.id ? saved : item))
    steamBlacklistSaved.value = true
  } catch (err) {
    error.value = err.message
  } finally {
    steamBlacklistRowSaving.value = { ...steamBlacklistRowSaving.value, [entry.id]: false }
  }
}

async function removeSteamBlacklistEntry(entry) {
  if (!window.confirm(t('adminUsers.steamBlacklistDeleteConfirm', { steamId: entry.steam_id }))) return
  error.value = ''
  try {
    await api(`/users/admin/steam-blacklist/${entry.id}`, { method: 'DELETE' })
    steamBlacklist.value = steamBlacklist.value.filter((item) => item.id !== entry.id)
  } catch (err) {
    error.value = err.message
  }
}

async function importSteamBlacklist(event) {
  const file = event.target.files?.[0] || null
  event.target.value = ''
  if (!file) return
  steamBlacklistImporting.value = true
  steamBlacklistSaved.value = false
  error.value = ''
  try {
    const formData = new FormData()
    formData.append('file', file)
    const result = await api('/users/admin/steam-blacklist/import', { method: 'POST', body: formData })
    await loadSteamBlacklist()
    steamBlacklistSaved.value = true
    if (result.errors?.length) {
      error.value = t('adminUsers.steamBlacklistImportErrors', { count: result.errors.length })
    }
  } catch (err) {
    error.value = err.message
  } finally {
    steamBlacklistImporting.value = false
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

async function saveBrowserTitle() {
  browserTitleSaving.value = true
  browserTitleSaved.value = false
  error.value = ''
  try {
    const saved = await api('/app-settings/branding', {
      method: 'PATCH',
      body: { browser_title: String(browserTitle.value || '').trim() }
    })
    setBrandingSettings(saved)
    browserTitle.value = brandingSettings.browser_title
    browserTitleSaved.value = true
  } catch (err) {
    error.value = err.message
  } finally {
    browserTitleSaving.value = false
  }
}

function setBrowserIconFile(event) {
  const file = event.target.files?.[0] || null
  event.target.value = ''
  browserIconSaved.value = false
  if (!file) return
  if (isGifFile(file)) {
    browserIconFile.value = file
    return
  }
  closeBrowserIconCropper()
  browserIconFile.value = null
  browserIconCropper.value = { sourceUrl: URL.createObjectURL(file), error: '' }
}

async function saveBrowserIcon(file) {
  browserIconSaving.value = true
  browserIconSaved.value = false
  error.value = ''
  try {
    const formData = new FormData()
    formData.append('file', file)
    setBrandingSettings(await api('/app-settings/branding/browser-icon/upload', {
      method: 'POST',
      body: formData
    }))
    browserIconFile.value = null
    browserIconSaved.value = true
    return true
  } catch (err) {
    error.value = err.message
    if (browserIconCropper.value) browserIconCropper.value = { ...browserIconCropper.value, error: err.message }
    return false
  } finally {
    browserIconSaving.value = false
  }
}

async function uploadBrowserIcon() {
  if (browserIconFile.value) await saveBrowserIcon(browserIconFile.value)
}

async function uploadCroppedBrowserIcon(blob) {
  if (await saveBrowserIcon(new File([blob], 'browser-icon.webp', { type: 'image/webp' }))) {
    closeBrowserIconCropper()
  }
}

function closeBrowserIconCropper() {
  if (!browserIconCropper.value || browserIconSaving.value) return
  URL.revokeObjectURL(browserIconCropper.value.sourceUrl)
  browserIconCropper.value = null
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
    const requestOptions = {
      method: 'POST',
      body: {
        confirmation: dangerForm.value.confirmation,
        confirmation_repeat: dangerForm.value.confirmation_repeat,
        password: dangerForm.value.password
      }
    }
    if (action.kind === 'download') {
      const blob = await apiDownload(action.endpoint, requestOptions)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `bmrl-database-${new Date().toISOString().replace(/[:.]/g, '-')}.dump`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      dangerResult.value = t('adminUsers.backupDownloaded')
    } else {
      const result = await api(action.endpoint, requestOptions)
      dangerResult.value = action.resultKey
        ? t(action.resultKey, { count: result?.deleted ?? 0 })
        : t('adminUsers.deletedCount', { count: result?.deleted ?? 0 })
    }
    dangerDialog.value = null
    dangerForm.value = { confirmation: '', confirmation_repeat: '', password: '' }
    if (action.kind === 'audit') {
      await auditLogPanel.value?.load()
    } else if (action.kind !== 'download') {
      await load()
    }
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
  closeBrowserIconCropper()
  closeDefaultAvatarCropper()
  closePilotRoleCropper()
  revokePilotRolePreview()
})

function isAdminZoneCollapsed(key) {
  return collapsedAdminZones.value[key] === true
}

function openUserDetails(user) {
  detailDialogUser.value = user
}

function closeUserDetails() {
  detailDialogUser.value = null
}

function detailValue(value) {
  if (Array.isArray(value)) return value.length ? value.join(', ') : t('common.none')
  if (value === null || value === undefined || value === '') return t('common.none')
  return String(value)
}

function detailRows(user) {
  if (!user) return []
  const ratings = Object.entries(user.game_ratings || {})
    .map(([game, value]) => `${game}: ${value?.rating ?? t('common.none')} (${value?.race_count ?? 0})`)
    .join(' · ')
  const linkedLogins = user.same_device_logins || []
  return [
    { label: t('adminUsers.accountId'), value: user.id },
    { label: t('fields.login'), value: user.login },
    { label: t('fields.email'), value: user.email },
    { label: t('fields.firstName'), value: user.first_name },
    { label: t('fields.lastName'), value: user.last_name },
    { label: t('fields.nickname'), value: user.nickname },
    { label: t('fields.pilotNumber'), value: `#${formatPilotNumber(user.pilot_number)}` },
    { label: t('fields.country'), value: user.country },
    { label: t('fields.discord'), value: user.discord },
    { label: t('common.role'), value: roleLabel(t, user.role) },
    { label: t('common.status'), value: statusLabel(t, user.status) },
    { label: t('adminUsers.systemAdmin'), value: user.is_system_admin ? t('common.yes') : t('common.no') },
    { label: t('fields.games'), value: user.games },
    { label: t('adminUsers.teamId'), value: user.team_id },
    { label: t('fields.team'), value: teamShortName(user.team_name, user.team_abbreviation) },
    { label: t('fields.sr'), value: user.sr },
    { label: t('fields.rating'), value: formatRating(user.rating) },
    { label: t('adminUsers.simulatorRatings'), value: ratings },
    { label: t('fields.ratingRaces'), value: user.rating_race_count },
    { label: t('profile.favoriteCar'), value: user.favorite_car },
    { label: t('adminUsers.avatarColor'), value: user.avatar_color },
    { label: t('adminUsers.rolesVisible'), value: user.show_pilot_roles ? t('common.yes') : t('common.no') },
    { label: t('fields.joinedAt'), value: formatDateTime(user.created_at) },
    { label: t('profile.updatedAt'), value: formatDateTime(user.updated_at) },
    { label: t('adminUsers.steamBlacklistSteamId'), value: user.steam_id },
    { label: t('adminUsers.device'), value: user.device_label },
    { label: t('adminUsers.deviceId'), value: user.device_id },
    { label: t('adminUsers.linkedAccounts'), value: linkedLogins.length ? `${user.same_device_account_count || linkedLogins.length + 1}: ${linkedLogins.join(', ')}` : t('common.none') },
    { label: t('profile.banEnd'), value: formatDateTime(user.ban_end) },
    { label: t('profile.timeoutStart'), value: formatDateTime(user.timeout_start) },
    { label: t('profile.timeoutEnd'), value: formatDateTime(user.timeout_end) },
    { label: t('profile.pendingChanges'), value: user.pending_profile_changes ? JSON.stringify(user.pending_profile_changes) : t('common.none') }
  ]
}

function setPilotRoleFile(event) {
  const file = event.target.files?.[0] || null
  event.target.value = ''
  if (!file) return
  if (!file.type.startsWith('image/')) {
    error.value = 'Выберите файл изображения.'
    return
  }
  closePilotRoleCropper()
  pilotRoleImageFile.value = null
  revokePilotRolePreview()
  pilotRoleCropper.value = { sourceUrl: URL.createObjectURL(file), error: '' }
}

function revokePilotRolePreview() {
  if (pilotRoleImagePreview.value) URL.revokeObjectURL(pilotRoleImagePreview.value)
  pilotRoleImagePreview.value = ''
}

function uploadCroppedPilotRole(blob) {
  revokePilotRolePreview()
  pilotRoleImageFile.value = new File([blob], 'pilot-role.webp', { type: 'image/webp' })
  pilotRoleImagePreview.value = URL.createObjectURL(pilotRoleImageFile.value)
  closePilotRoleCropper()
}

function closePilotRoleCropper() {
  if (!pilotRoleCropper.value || pilotRoleSaving.value) return
  URL.revokeObjectURL(pilotRoleCropper.value.sourceUrl)
  pilotRoleCropper.value = null
}

function pilotRoleModeLabel(mode) {
  return {
    text: 'Текст',
    text_image: 'Текст + изображение',
    image: 'Изображение'
  }[mode] || 'Текст'
}

async function createPilotRole() {
  const name = String(pilotRoleForm.value.name || '').trim()
  if (!name) return
  const displayMode = pilotRoleForm.value.display_mode || 'text'
  if (displayMode !== 'text' && !pilotRoleImageFile.value) {
    error.value = displayMode === 'image' ? 'Для роли-изображения выберите файл.' : 'Для роли «Текст + изображение» выберите файл.'
    return
  }
  pilotRoleSaving.value = true
  error.value = ''
  try {
    let role = await api('/users/admin/pilot-roles', {
      method: 'POST',
      body: {
        name,
        display_mode: displayMode,
        border_color: pilotRoleForm.value.border_color || '#2563eb'
      }
    })
    if (pilotRoleImageFile.value && displayMode !== 'text') {
      const body = new FormData()
      body.append('file', pilotRoleImageFile.value, pilotRoleImageFile.value.name)
      role = await api(`/users/admin/pilot-roles/${role.id}/image`, { method: 'POST', body })
    }
    pilotRoles.value = [...pilotRoles.value.filter((item) => item.id !== role.id), role].sort((left, right) => left.name.localeCompare(right.name))
    pilotRoleForm.value = { name: '', display_mode: 'text', border_color: '#2563eb' }
    pilotRoleImageFile.value = null
    revokePilotRolePreview()
  } catch (err) {
    error.value = err.message
  } finally {
    pilotRoleSaving.value = false
  }
}

async function deletePilotRole(role) {
  if (!window.confirm(`Удалить роль «${role.name}» у всех пилотов?`)) return
  pilotRoleDeleting.value = { ...pilotRoleDeleting.value, [role.id]: true }
  try {
    await api(`/users/admin/pilot-roles/${role.id}`, { method: 'DELETE' })
    pilotRoles.value = pilotRoles.value.filter((item) => item.id !== role.id)
    users.value = users.value.map((user) => ({ ...user, pilot_roles: (user.pilot_roles || []).filter((item) => item.id !== role.id) }))
  } catch (err) {
    error.value = err.message
  } finally {
    pilotRoleDeleting.value = { ...pilotRoleDeleting.value, [role.id]: false }
  }
}

function openPilotRoleDialog(user) {
  pilotRoleDialogUser.value = user
  pilotRoleSelection.value = (user.pilot_roles || []).map((role) => role.id)
}

function closePilotRoleDialog() {
  if (pilotRoleAssignSaving.value) return
  pilotRoleDialogUser.value = null
  pilotRoleSelection.value = []
}

function togglePilotRole(roleId) {
  const id = Number(roleId)
  pilotRoleSelection.value = pilotRoleSelection.value.includes(id)
    ? pilotRoleSelection.value.filter((item) => item !== id)
    : [...pilotRoleSelection.value, id]
}

async function savePilotRoles() {
  if (!pilotRoleDialogUser.value) return
  pilotRoleAssignSaving.value = true
  try {
    const updated = await api(`/users/${pilotRoleDialogUser.value.id}/pilot-roles`, {
      method: 'PUT',
      body: { role_ids: pilotRoleSelection.value }
    })
    updateUserInList(updated)
    pilotRoleDialogUser.value = updated
  } catch (err) {
    error.value = err.message
  } finally {
    pilotRoleAssignSaving.value = false
  }
}

function toggleAdminZone(key) {
  collapsedAdminZones.value = {
    ...collapsedAdminZones.value,
    [key]: !isAdminZoneCollapsed(key)
  }
}
watch(page, load)
watch([userSearch, userSearchBy, userSort, userRatingGame], resetUserPageAndLoad)
watch(() => pilotRoleForm.value.display_mode, (mode) => {
  if (mode === 'text') {
    pilotRoleImageFile.value = null
    revokePilotRolePreview()
    closePilotRoleCropper()
  }
})
</script>

<template>
  <section class="section admin-users-page">
    <div class="section-header">
      <h1>{{ t('nav.admin') }}</h1>
    </div>
    <p v-if="error" class="error">{{ error }}</p>

    <!-- Loading/empty states are N/A: bundled logos are always available as immediate defaults. -->
    <section class="admin-settings-card admin-logo-config-card card" :class="{ 'is-collapsed': isAdminZoneCollapsed('logos') }">
      <div class="admin-zone-head">
        <h2>{{ t('adminUsers.logoTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.logoHint') }}</p>
        <button class="icon-button admin-zone-toggle" type="button" :aria-expanded="!isAdminZoneCollapsed('logos')" :aria-label="isAdminZoneCollapsed('logos') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" :title="isAdminZoneCollapsed('logos') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" @click="toggleAdminZone('logos')">
          <ChevronDown :size="18" />
        </button>
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

    <form class="admin-settings-card admin-browser-branding-card card" :class="{ 'is-collapsed': isAdminZoneCollapsed('browser-branding') }" @submit.prevent="saveBrowserTitle">
      <div class="admin-browser-branding-copy admin-zone-head">
        <h2>{{ t('adminUsers.browserBrandingTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.browserBrandingHint') }}</p>
        <button class="icon-button admin-zone-toggle" type="button" :aria-expanded="!isAdminZoneCollapsed('browser-branding')" :aria-label="isAdminZoneCollapsed('browser-branding') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" :title="isAdminZoneCollapsed('browser-branding') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" @click="toggleAdminZone('browser-branding')">
          <ChevronDown :size="18" />
        </button>
      </div>
      <label class="field admin-browser-title-field">
        <span>{{ t('adminUsers.browserTitleField') }}</span>
        <input v-model="browserTitle" type="text" maxlength="120" required />
      </label>
      <div class="admin-browser-icon-preview">
        <img :src="brandingSettings.browser_icon_url" alt="" />
      </div>
      <label class="field admin-browser-icon-field">
        <span>{{ t('adminUsers.browserIconField') }}</span>
        <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" @change="setBrowserIconFile" />
      </label>
      <button class="button primary" type="submit" :disabled="browserTitleSaving">
        <Save :size="16" />
        {{ browserTitleSaving ? t('common.saving') : t('common.save') }}
      </button>
      <button class="button" type="button" :disabled="browserIconSaving || !browserIconFile" @click="uploadBrowserIcon">
        <Upload :size="16" />
        {{ t('common.upload') }}
      </button>
      <span v-if="browserTitleSaved || browserIconSaved" class="pill">{{ t('common.saved') }}</span>
    </form>

    <ImageCropper
      v-if="browserIconCropper"
      :source-url="browserIconCropper.sourceUrl"
      :title="t('adminUsers.browserIconCropTitle')"
      :hint="t('adminUsers.browserIconCropHint')"
      :target-width="256"
      :target-height="256"
      :saving="browserIconSaving"
      :error="browserIconCropper.error"
      @close="closeBrowserIconCropper"
      @crop="uploadCroppedBrowserIcon"
    />

    <section class="admin-settings-card admin-avatar-config-card card" :class="{ 'is-collapsed': isAdminZoneCollapsed('avatar') }">
      <div class="admin-zone-head">
        <h2>{{ t('adminUsers.defaultAvatarTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.defaultAvatarHint') }}</p>
        <button class="icon-button admin-zone-toggle" type="button" :aria-expanded="!isAdminZoneCollapsed('avatar')" :aria-label="isAdminZoneCollapsed('avatar') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" :title="isAdminZoneCollapsed('avatar') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" @click="toggleAdminZone('avatar')">
          <ChevronDown :size="18" />
        </button>
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

    <section class="admin-settings-card admin-weather-config-card card" :class="{ 'is-collapsed': isAdminZoneCollapsed('weather') }">
      <div class="admin-zone-head">
        <h2>{{ t('adminUsers.weatherImagesTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.weatherImagesHint') }}</p>
        <button class="icon-button admin-zone-toggle" type="button" :aria-expanded="!isAdminZoneCollapsed('weather')" :aria-label="isAdminZoneCollapsed('weather') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" :title="isAdminZoneCollapsed('weather') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" @click="toggleAdminZone('weather')">
          <ChevronDown :size="18" />
        </button>
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

    <form class="admin-settings-card admin-system-config-card card" :class="{ 'is-collapsed': isAdminZoneCollapsed('system') }" @submit.prevent="saveSystemSettings">
      <div class="admin-zone-head">
        <h2>{{ t('adminUsers.systemTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.systemHint') }}</p>
        <button class="icon-button admin-zone-toggle" type="button" :aria-expanded="!isAdminZoneCollapsed('system')" :aria-label="isAdminZoneCollapsed('system') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" :title="isAdminZoneCollapsed('system') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" @click="toggleAdminZone('system')">
          <ChevronDown :size="18" />
        </button>
      </div>
      <label class="field">
        <span>{{ t('adminUsers.rateLimitField') }}</span>
        <input v-model.number="systemSettings.requests_per_user_per_minute" type="number" min="1" max="10000" required />
      </label>
      <label class="field">
        <span>{{ t('adminUsers.rateLimitIpField') }}</span>
        <input v-model.number="systemSettings.requests_per_ip_per_minute" type="number" min="1" max="10000" required />
      </label>
      <label class="field">
        <span>{{ t('adminUsers.ratingCoefficientField') }}</span>
        <input v-model.number="systemSettings.rating_change_coefficient" type="number" min="0.01" max="10" step="0.01" required />
      </label>
      <label class="field">
        <span>{{ t('adminUsers.srPerRaceField') }}</span>
        <input v-model.number="systemSettings.sr_per_race" type="number" min="0" max="100" step="0.01" required />
      </label>
      <label class="toggle-field admin-show-setups-field">
        <input v-model="systemSettings.show_setups_section" type="checkbox" />
        <span>{{ t('adminUsers.showSetupsField') }}</span>
      </label>
      <button class="button primary" type="submit" :disabled="systemSettingsSaving">
        <Save :size="16" />
        {{ t('common.save') }}
      </button>
      <span v-if="systemSettingsSaved" class="pill">{{ t('common.saved') }}</span>
    </form>

    <section class="admin-settings-card admin-steam-blacklist-card card" :class="{ 'is-collapsed': isAdminZoneCollapsed('steam-blacklist') }">
      <div class="admin-zone-head">
        <h2>{{ t('adminUsers.steamBlacklistTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.steamBlacklistHint') }}</p>
        <button class="icon-button admin-zone-toggle" type="button" :aria-expanded="!isAdminZoneCollapsed('steam-blacklist')" :aria-label="isAdminZoneCollapsed('steam-blacklist') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" :title="isAdminZoneCollapsed('steam-blacklist') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" @click="toggleAdminZone('steam-blacklist')">
          <ChevronDown :size="18" />
        </button>
      </div>
      <div class="admin-steam-blacklist-tools">
        <form class="admin-steam-blacklist-add" @submit.prevent="addSteamBlacklistEntry">
          <label class="field">
            <span>{{ t('adminUsers.steamBlacklistSteamId') }}</span>
            <input v-model="steamBlacklistForm.steam_id" type="text" inputmode="numeric" pattern="[0-9]+" required />
          </label>
          <label class="field">
            <span>{{ t('adminUsers.steamBlacklistReason') }}</span>
            <input v-model="steamBlacklistForm.reason" type="text" maxlength="1000" required />
          </label>
          <button class="button primary" type="submit" :disabled="steamBlacklistSaving">
            <Plus :size="16" />
            {{ t('adminUsers.steamBlacklistAdd') }}
          </button>
        </form>
        <div class="admin-steam-blacklist-import">
          <a class="button" href="/templates/steam-blacklist-example.xlsx" download="steam-blacklist-example.xlsx">
            <Download :size="16" />
            {{ t('adminUsers.steamBlacklistTemplate') }}
          </a>
          <label class="button" :class="{ disabled: steamBlacklistImporting }">
            <Upload :size="16" />
            {{ steamBlacklistImporting ? t('common.loading') : t('adminUsers.steamBlacklistImport') }}
            <input type="file" hidden accept=".xlsx,.csv,.tsv,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" :disabled="steamBlacklistImporting" @change="importSteamBlacklist" />
          </label>
        </div>
      </div>
      <div v-if="steamBlacklist.length" class="admin-steam-blacklist-table-wrap">
        <table class="admin-steam-blacklist-table">
          <thead>
            <tr>
              <th>{{ t('adminUsers.steamBlacklistSteamId') }}</th>
              <th>{{ t('adminUsers.steamBlacklistReason') }}</th>
              <th><span class="sr-only">{{ t('common.actions') }}</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="entry in steamBlacklist" :key="entry.id">
              <td><input v-model="entry.steam_id" class="admin-steam-blacklist-id" type="text" inputmode="numeric" pattern="[0-9]+" /></td>
              <td><input v-model="entry.reason" type="text" maxlength="1000" /></td>
              <td class="admin-steam-blacklist-actions">
                <button class="icon-button" type="button" :disabled="steamBlacklistRowSaving[entry.id]" :title="t('adminUsers.steamBlacklistSave')" :aria-label="t('adminUsers.steamBlacklistSave')" @click="saveSteamBlacklistEntry(entry)"><Save :size="16" /></button>
                <button class="icon-button danger-icon" type="button" :title="t('common.delete')" :aria-label="t('common.delete')" @click="removeSteamBlacklistEntry(entry)"><Trash2 :size="16" /></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="muted">{{ t('adminUsers.steamBlacklistEmpty') }}</p>
      <span v-if="steamBlacklistSaved" class="pill">{{ t('common.saved') }}</span>
    </section>

    <section class="admin-settings-card admin-pilot-roles-card card" :class="{ 'is-collapsed': isAdminZoneCollapsed('pilot-roles') }">
      <div class="admin-zone-head">
        <div>
          <h2>Роли пилотов</h2>
          <p class="muted">Создайте текстовую или графическую роль и назначайте её пилотам из списка ниже.</p>
        </div>
        <button class="icon-button admin-zone-toggle" type="button" :aria-expanded="!isAdminZoneCollapsed('pilot-roles')" @click="toggleAdminZone('pilot-roles')"><ChevronDown :size="18" /></button>
      </div>
      <form class="admin-pilot-role-create" @submit.prevent="createPilotRole">
        <label class="field"><span>Название роли</span><input v-model="pilotRoleForm.name" maxlength="80" placeholder="Например, Комментатор" required /></label>
        <label class="field admin-pilot-role-type"><span>Вариант отображения</span><select v-model="pilotRoleForm.display_mode"><option value="text">Текст</option><option value="text_image">Текст + изображение</option><option value="image">Только изображение</option></select></label>
        <label v-if="pilotRoleForm.display_mode !== 'text'" class="field admin-pilot-role-image-field">
          <span>Изображение роли</span>
          <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" aria-describedby="pilot-role-image-hint" @change="setPilotRoleFile" />
          <small id="pilot-role-image-hint" class="muted">Выберите файл — откроется обрезка.</small>
          <span v-if="pilotRoleImageFile" class="admin-pilot-role-image-ready"><img v-if="pilotRoleImagePreview" :src="pilotRoleImagePreview" alt="" />Готово к загрузке</span>
        </label>
        <label v-if="pilotRoleForm.display_mode !== 'image'" class="field admin-pilot-role-color"><span>Цвет рамки</span><input v-model="pilotRoleForm.border_color" type="color" aria-label="Цвет рамки роли" /></label>
        <button class="button primary" type="submit" :disabled="pilotRoleSaving"><Plus :size="16" />Добавить роль</button>
      </form>
      <div v-if="pilotRoles.length" class="admin-pilot-role-list">
        <div v-for="role in pilotRoles" :key="role.id" class="admin-pilot-role-row">
          <PilotRoles :roles="[role]" />
          <span class="muted">{{ pilotRoleModeLabel(role.display_mode || (role.image_url ? 'text_image' : 'text')) }}</span>
          <span v-if="role.display_mode !== 'image'" class="admin-pilot-role-color-swatch" :style="{ backgroundColor: role.border_color || 'var(--primary)' }" :title="role.border_color || 'Цвет рамки'" aria-hidden="true"></span>
          <button class="icon-button danger-icon" type="button" :disabled="pilotRoleDeleting[role.id]" title="Удалить роль" aria-label="Удалить роль" @click="deletePilotRole(role)"><Trash2 :size="16" /></button>
        </div>
      </div>
      <p v-else class="muted">Роли ещё не созданы.</p>
    </section>

    <ImageCropper
      v-if="pilotRoleCropper"
      :source-url="pilotRoleCropper.sourceUrl"
      title="Обрезка изображения роли"
      hint="Настройте квадратный фрагмент — он будет показан рядом с именем и не превысит его высоту."
      :target-width="256"
      :target-height="256"
      :saving="pilotRoleSaving"
      :error="pilotRoleCropper.error"
      @close="closePilotRoleCropper"
      @crop="uploadCroppedPilotRole"
    />

    <form class="admin-settings-card card" :class="{ 'is-collapsed': isAdminZoneCollapsed('team-limit') }" @submit.prevent="saveTeamLimit">
      <div class="admin-zone-head">
        <h2>{{ t('adminUsers.teamLimitTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.teamLimitHint') }}</p>
        <button class="icon-button admin-zone-toggle" type="button" :aria-expanded="!isAdminZoneCollapsed('team-limit')" :aria-label="isAdminZoneCollapsed('team-limit') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" :title="isAdminZoneCollapsed('team-limit') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" @click="toggleAdminZone('team-limit')">
          <ChevronDown :size="18" />
        </button>
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

    <form class="admin-settings-card card" :class="{ 'is-collapsed': isAdminZoneCollapsed('fan-vote') }" @submit.prevent="saveFanVoteConfig">
      <div class="admin-zone-head">
        <h2>{{ t('adminUsers.fanVoteTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.fanVoteHint') }}</p>
        <button class="icon-button admin-zone-toggle" type="button" :aria-expanded="!isAdminZoneCollapsed('fan-vote')" :aria-label="isAdminZoneCollapsed('fan-vote') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" :title="isAdminZoneCollapsed('fan-vote') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" @click="toggleAdminZone('fan-vote')">
          <ChevronDown :size="18" />
        </button>
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

    <form class="admin-settings-card admin-twitch-config-card card" :class="{ 'is-collapsed': isAdminZoneCollapsed('twitch') }" @submit.prevent="saveTwitchConfig">
      <div class="admin-zone-head">
        <h2>{{ t('adminUsers.twitchFallbackTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.twitchFallbackHint') }}</p>
        <button class="icon-button admin-zone-toggle" type="button" :aria-expanded="!isAdminZoneCollapsed('twitch')" :aria-label="isAdminZoneCollapsed('twitch') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" :title="isAdminZoneCollapsed('twitch') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" @click="toggleAdminZone('twitch')">
          <ChevronDown :size="18" />
        </button>
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

    <form class="admin-settings-card admin-license-config-card card" :class="{ 'is-collapsed': isAdminZoneCollapsed('licenses') }" @submit.prevent="saveLicenseSettings">
      <div class="admin-zone-head">
        <h2>{{ t('adminUsers.licenseTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.licenseHint') }}</p>
        <button class="icon-button admin-zone-toggle" type="button" :aria-expanded="!isAdminZoneCollapsed('licenses')" :aria-label="isAdminZoneCollapsed('licenses') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" :title="isAdminZoneCollapsed('licenses') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" @click="toggleAdminZone('licenses')">
          <ChevronDown :size="18" />
        </button>
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

    <form class="admin-settings-card admin-donation-config-card card" :class="{ 'is-collapsed': isAdminZoneCollapsed('donations') }" @submit.prevent="saveDonationSettings">
      <div class="admin-zone-head">
        <h2>{{ t('adminUsers.donationTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.donationHint') }}</p>
        <button class="icon-button admin-zone-toggle" type="button" :aria-expanded="!isAdminZoneCollapsed('donations')" :aria-label="isAdminZoneCollapsed('donations') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" :title="isAdminZoneCollapsed('donations') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" @click="toggleAdminZone('donations')">
          <ChevronDown :size="18" />
        </button>
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

    <AuditLogPanel ref="auditLogPanel" @clear="openDangerDialog('audit')" />

    <section v-if="canUseDangerZone" class="admin-danger-card card" :class="{ 'is-collapsed': isAdminZoneCollapsed('danger') }">
      <div class="admin-zone-head">
        <h2>{{ t('adminUsers.dangerTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.dangerHint') }}</p>
        <span v-if="dangerResult" class="pill">{{ dangerResult }}</span>
        <button class="icon-button admin-zone-toggle" type="button" :aria-expanded="!isAdminZoneCollapsed('danger')" :aria-label="isAdminZoneCollapsed('danger') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" :title="isAdminZoneCollapsed('danger') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" @click="toggleAdminZone('danger')">
          <ChevronDown :size="18" />
        </button>
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
        <button class="button" type="button" @click="openDangerDialog('backup')">
          <Download :size="16" />
          {{ t('adminUsers.downloadDatabaseBackup') }}
        </button>
      </div>
    </section>

    <div class="admin-users-card card" :class="{ 'is-collapsed': isAdminZoneCollapsed('users') }">
      <div class="admin-zone-head">
        <h2>{{ t('adminUsers.usersTitle') }}</h2>
        <button class="icon-button admin-zone-toggle" type="button" :aria-expanded="!isAdminZoneCollapsed('users')" :aria-label="isAdminZoneCollapsed('users') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" :title="isAdminZoneCollapsed('users') ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" @click="toggleAdminZone('users')">
          <ChevronDown :size="18" />
        </button>
      </div>
      <div class="pilot-inline-controls admin-users-controls">
        <input v-model="userSearch" type="search" :placeholder="t('common.search')" />
        <select v-model="userSearchBy" :aria-label="t('adminUsers.searchBy')">
          <option v-for="option in userSearchOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
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
          <tr v-for="user in visibleUsers" :key="user.id" :class="{ 'has-device-match': user.same_device_account_count > 1 }">
            <td>
              <div class="admin-user-cell">
                <UserAvatar mini :src="user.avatar_url" :color="user.avatar_color" :label="user.login" />
                <div class="admin-user-info">
                  <span class="user-name-line">
                    <strong>{{ user.login }}</strong>
                    <PilotRoles :roles="user.pilot_roles" />
                    <LicenseBadge :user="user" :game="userRatingGame" />
                  </span>
                  <span>#{{ formatPilotNumber(user.pilot_number) }} · RER {{ formatRating(ratingForGame(user, userRatingGame)) }} · {{ teamShortName(user.team_name, user.team_abbreviation) }}</span>
                  <span
                    v-if="user.device_label"
                    class="admin-user-device"
                    :title="user.same_device_account_count > 1 ? t('adminUsers.sameDeviceTooltip', { logins: user.same_device_logins?.join(', ') || t('common.none') }) : ''"
                  ><Monitor :size="13" /> {{ t('adminUsers.device') }}: {{ user.device_label }}<small v-if="user.same_device_account_count > 1">{{ t('adminUsers.sameDeviceAccounts', { count: user.same_device_account_count }) }}</small></span>
                  <span v-if="user.device_id" class="admin-user-device-id">{{ t('adminUsers.deviceIdShort') }}: {{ user.device_id }}</span>
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
                  :title="t('adminUsers.viewUser')"
                  :aria-label="t('adminUsers.viewUser')"
                  @click="openUserDetails(user)"
                >
                  <Eye :size="16" />
                </button>
                <button class="button small" type="button" :disabled="user.is_system_admin" @click="openPilotRoleDialog(user)">Роль</button>
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

    <div v-if="detailDialogUser" class="penalty-modal-backdrop" @click.self="closeUserDetails">
      <section class="penalty-modal admin-user-details-modal card" role="dialog" aria-modal="true" :aria-label="t('adminUsers.userDetailsTitle')">
        <div class="penalty-modal-head section-header">
          <div>
            <h2>{{ t('adminUsers.userDetailsTitle') }}</h2>
            <p>{{ detailDialogUser.login }} · #{{ formatPilotNumber(detailDialogUser.pilot_number) }}</p>
          </div>
          <button class="icon-button" type="button" :title="t('common.close')" :aria-label="t('common.close')" @click="closeUserDetails">
            <X :size="18" />
          </button>
        </div>

        <div class="admin-user-details-hero">
          <UserAvatar :src="detailDialogUser.avatar_url" :color="detailDialogUser.avatar_color" :label="detailDialogUser.nickname || detailDialogUser.login" />
          <div>
            <h3>{{ detailDialogUser.first_name }} {{ detailDialogUser.last_name }}</h3>
            <p class="muted">@{{ detailDialogUser.login }} · {{ detailDialogUser.nickname }}</p>
            <PilotRoles :roles="detailDialogUser.pilot_roles" />
          </div>
        </div>

        <div class="admin-user-details-grid">
          <div v-for="item in detailRows(detailDialogUser)" :key="item.label" class="admin-user-detail-item">
            <span>{{ item.label }}</span>
            <strong>{{ detailValue(item.value) }}</strong>
          </div>
        </div>

        <p class="admin-user-details-security">
          <Shield :size="15" />
          {{ t('adminUsers.passwordHashHidden') }}
        </p>

        <div class="admin-timeout-actions">
          <button class="button" type="button" @click="closeUserDetails">
            <X :size="16" />
            {{ t('common.close') }}
          </button>
        </div>
      </section>
    </div>

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
            {{ t(activeDangerAction.submitKey || 'common.delete') }}
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

    <div v-if="pilotRoleDialogUser" class="penalty-modal-backdrop" @click.self="closePilotRoleDialog">
      <form class="penalty-modal admin-pilot-role-modal card" @submit.prevent="savePilotRoles">
        <div class="penalty-modal-head section-header">
          <div>
            <h2>Роли пилота</h2>
            <p>{{ pilotRoleDialogUser.first_name }} {{ pilotRoleDialogUser.last_name }} · @{{ pilotRoleDialogUser.login }}</p>
          </div>
          <button class="icon-button" type="button" title="Закрыть" aria-label="Закрыть" @click="closePilotRoleDialog"><X :size="18" /></button>
        </div>
        <div v-if="pilotRoles.length" class="admin-pilot-role-options">
          <label v-for="role in pilotRoles" :key="role.id" class="admin-pilot-role-option" :class="{ selected: pilotRoleSelection.includes(role.id) }">
            <input type="checkbox" :checked="pilotRoleSelection.includes(role.id)" @change="togglePilotRole(role.id)" />
            <PilotRoles :roles="[role]" />
          </label>
        </div>
        <p v-else class="muted">Сначала создайте роль выше.</p>
        <div class="admin-timeout-actions">
          <button class="button" type="button" :disabled="pilotRoleAssignSaving" @click="closePilotRoleDialog">Отмена</button>
          <button class="button primary" type="submit" :disabled="pilotRoleAssignSaving">Сохранить</button>
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
