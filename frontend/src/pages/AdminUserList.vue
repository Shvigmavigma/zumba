<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Ban, Edit3, Save, Timer, TimerOff, Trash2, Undo2, Upload, X } from 'lucide-vue-next'
import { api } from '../api'
import AvatarViewer from '../components/AvatarViewer.vue'
import CountryCombobox from '../components/CountryCombobox.vue'
import GameCheckboxGroup from '../components/GameCheckboxGroup.vue'
import PaginationControls from '../components/PaginationControls.vue'
import UserAvatar from '../components/UserAvatar.vue'
import { countryOptionsWithCurrent } from '../countries'
import { roleLabel, statusLabel } from '../i18nLabels'
import { formatPilotNumber, formatRating, teamShortName } from '../pilotDisplay'
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
const raceAssetGames = ['ACC', 'AC', 'iRacing']
const raceAssetGame = ref('ACC')
const raceAssetsByGame = ref(defaultRaceAssetsByGame())
const raceAssetsSaving = ref(false)
const raceAssetsSaved = ref(false)
const dangerDialog = ref(null)
const dangerForm = ref({ confirmation: '', confirmation_repeat: '', password: '' })
const dangerSaving = ref(false)
const dangerResult = ref('')
const userSearch = ref('')
const userSort = ref('rating_desc')
const page = ref(1)
const pageSize = 25
const visibleUsers = computed(() => users.value)
const hasNextPage = computed(() => users.value.length === pageSize)
const editCountries = computed(() => countryOptionsWithCurrent(state.locale, editForm.value.country || ''))
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
const activeRaceAssetsDraft = computed(() => raceAssetsByGame.value[raceAssetGame.value])
const dangerFormValid = computed(() => {
  const action = activeDangerAction.value
  if (!action) return false
  return (
    dangerForm.value.confirmation.trim() === action.code &&
    dangerForm.value.confirmation_repeat.trim() === action.code &&
    dangerForm.value.password.length > 0
  )
})

function emptyRaceAssetDraft() {
  return { tracksText: '', classes: [] }
}

function defaultRaceAssetsByGame() {
  return Object.fromEntries(raceAssetGames.map((game) => [game, emptyRaceAssetDraft()]))
}

function draftFromConfig(config = {}) {
  return {
    tracksText: (config.tracks || []).join('\n'),
    classes: (config.classes || []).map((item) => ({
      name: item.name,
      carsText: (item.cars || []).join('\n')
    }))
  }
}

function normalizeRaceAssetsDraft(config = {}) {
  const games = config.games || {}
  return {
    ACC: draftFromConfig(games.ACC || config),
    AC: draftFromConfig(games.AC),
    iRacing: draftFromConfig(games.iRacing)
  }
}

function configFromDraft(draft = emptyRaceAssetDraft()) {
  return {
    tracks: draft.tracksText.split('\n').map((item) => item.trim()).filter(Boolean),
    classes: draft.classes
      .map((item) => ({
        name: item.name.trim(),
        cars: item.carsText.split('\n').map((car) => car.trim()).filter(Boolean)
      }))
      .filter((item) => item.name)
  }
}

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
    timeStyle: 'short'
  }).format(new Date(value))
}

async function load() {
  try {
    const params = new URLSearchParams({
      limit: String(pageSize),
      offset: String((page.value - 1) * pageSize),
      sort: userSort.value
    })
    if (userSearch.value.trim()) params.set('search', userSearch.value.trim())
    const [loadedUsers, teamConfig, fanVoteConfig, loadedTwitchConfig, loadedRaceAssets] = await Promise.all([
      api(`/users/admin?${params.toString()}`),
      api('/teams/config'),
      api('/races/fan-vote/config'),
      api('/twitch/config'),
      api('/race-assets')
    ])
    users.value = loadedUsers
    teamLimit.value = teamConfig.member_limit
    fanVoteDurationHours.value = fanVoteConfig.duration_hours
    twitchConfig.value = {
      fallback_video_url: loadedTwitchConfig.fallback_video_url || '',
      fallback_video_title: loadedTwitchConfig.fallback_video_title || ''
    }
    raceAssetsByGame.value = normalizeRaceAssetsDraft(loadedRaceAssets)
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

function addRaceAssetClass() {
  activeRaceAssetsDraft.value.classes = [...activeRaceAssetsDraft.value.classes, { name: '', carsText: '' }]
}

function removeRaceAssetClass(index) {
  activeRaceAssetsDraft.value.classes = activeRaceAssetsDraft.value.classes.filter((_, itemIndex) => itemIndex !== index)
}

async function saveRaceAssets() {
  raceAssetsSaving.value = true
  raceAssetsSaved.value = false
  error.value = ''
  try {
    const games = Object.fromEntries(raceAssetGames.map((game) => [game, configFromDraft(raceAssetsByGame.value[game])]))
    const config = await api('/race-assets', {
      method: 'PATCH',
      body: {
        ...games.ACC,
        games
      }
    })
    raceAssetsByGame.value = normalizeRaceAssetsDraft(config)
    raceAssetsSaved.value = true
  } catch (err) {
    error.value = err.message
  } finally {
    raceAssetsSaving.value = false
  }
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
  if (user.role === 'admin') return
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
  if (user.role === 'admin') return
  timeoutDialogUser.value = user
  timeoutUntil.value = user.timeout_end ? datetimeLocalValue(new Date(user.timeout_end)) : defaultTimeoutUntil()
}

function closeTimeoutDialog() {
  if (timeoutSaving.value) return
  timeoutDialogUser.value = null
  timeoutUntil.value = ''
}

function openEditDialog(user) {
  editDialogUser.value = user
  editForm.value = {
    login: user.login || '',
    email: user.email || '',
    first_name: user.first_name || '',
    last_name: user.last_name || '',
    nickname: user.nickname || '',
    pilot_number: formatPilotNumber(user.pilot_number),
    country: user.country || '',
    discord: user.discord || '',
    games: user.games?.length ? [...user.games] : ['ACC']
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
        games: editForm.value.games
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
  if (!editDialogUser.value || !editAvatarFile.value) return
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
  if (user.status !== 'timeout') return
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
  if (user.id === state.user?.id) return
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
watch(page, load)
watch([userSearch, userSort], resetUserPageAndLoad)
</script>

<template>
  <section class="section admin-users-page">
    <div class="section-header">
      <h1>{{ t('nav.admin') }}</h1>
    </div>
    <p v-if="error" class="error">{{ error }}</p>

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

    <form class="admin-settings-card admin-race-assets-card card" @submit.prevent="saveRaceAssets">
      <div class="admin-race-assets-head">
        <h2>{{ t('adminUsers.raceAssetsTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.raceAssetsHint') }}</p>
      </div>
      <div class="admin-race-assets-tabs">
        <button
          v-for="game in raceAssetGames"
          :key="game"
          class="button small"
          :class="{ primary: raceAssetGame === game }"
          type="button"
          @click="raceAssetGame = game"
        >
          {{ game }}
        </button>
      </div>
      <label class="field admin-race-assets-tracks">
        <span>{{ t('adminUsers.raceAssetsTracks') }}</span>
        <textarea v-model="activeRaceAssetsDraft.tracksText" required></textarea>
      </label>
      <div class="admin-race-assets-classes">
        <div class="section-header">
          <h3>{{ t('adminUsers.raceAssetsClasses') }}</h3>
          <button class="button small" type="button" @click="addRaceAssetClass">{{ t('adminUsers.addRaceClass') }}</button>
        </div>
        <article v-for="(item, index) in activeRaceAssetsDraft.classes" :key="index" class="admin-race-class-row">
          <label class="field">
            <span>{{ t('fields.class') }}</span>
            <input v-model="item.name" required />
          </label>
          <label class="field">
            <span>{{ t('fields.allowedCars') }}</span>
            <textarea v-model="item.carsText" required></textarea>
          </label>
          <button class="icon-button danger-icon" type="button" :title="t('common.delete')" :aria-label="t('common.delete')" @click="removeRaceAssetClass(index)">
            <Trash2 :size="16" />
          </button>
        </article>
      </div>
      <div class="admin-race-assets-actions">
        <button class="button primary" type="submit" :disabled="raceAssetsSaving">
          <Save :size="16" />
          {{ t('common.save') }}
        </button>
        <span v-if="raceAssetsSaved" class="pill">{{ t('common.saved') }}</span>
      </div>
    </form>

    <section class="admin-danger-card card">
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
                  <strong>{{ user.login }}</strong>
                  <span>#{{ formatPilotNumber(user.pilot_number) }} · RER {{ formatRating(user.rating) }} · {{ teamShortName(user.team_name, user.team_abbreviation) }}</span>
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
                  :disabled="busyUsers[user.id]"
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
                  :disabled="busyUsers[user.id]"
                  @click="openEditDialog(user)"
                >
                  <Edit3 :size="16" />
                </button>
                <button
                  class="icon-button danger-icon"
                  type="button"
                  :title="t('common.ban')"
                  :aria-label="t('common.ban')"
                  :disabled="user.role === 'admin' || busyUsers[user.id]"
                  @click="ban(user)"
                >
                  <Ban :size="16" />
                </button>
                <button
                  class="icon-button"
                  type="button"
                  :title="t('adminUsers.issueTimeout')"
                  :aria-label="t('adminUsers.issueTimeout')"
                  :disabled="user.role === 'admin' || busyUsers[user.id]"
                  @click="openTimeoutDialog(user)"
                >
                  <Timer :size="16" />
                </button>
                <button
                  class="icon-button"
                  type="button"
                  :title="t('adminUsers.endTimeout')"
                  :aria-label="t('adminUsers.endTimeout')"
                  :disabled="user.status !== 'timeout' || busyUsers[user.id]"
                  @click="endTimeout(user)"
                >
                  <TimerOff :size="16" />
                </button>
                <button
                  class="icon-button"
                  type="button"
                  :title="t('common.unban')"
                  :aria-label="t('common.unban')"
                  :disabled="busyUsers[user.id]"
                  @click="unban(user)"
                >
                  <Undo2 :size="16" />
                </button>
                <button
                  class="icon-button danger-icon"
                  type="button"
                  :title="t('common.delete')"
                  :aria-label="t('common.delete')"
                  :disabled="user.id === state.user?.id || busyUsers[user.id]"
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
          <span>{{ t('fields.password') }}</span>
          <input v-model="dangerForm.password" type="password" autocomplete="current-password" required />
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
