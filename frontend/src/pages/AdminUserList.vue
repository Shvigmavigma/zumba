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
import { formatRating, teamShortName } from '../pilotDisplay'
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
const userSearch = ref('')
const userSort = ref('rating_desc')
const page = ref(1)
const pageSize = 25
const visibleUsers = computed(() => users.value)
const hasNextPage = computed(() => users.value.length === pageSize)
const editCountries = computed(() => countryOptionsWithCurrent(state.locale, editForm.value.country || ''))

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
    const [loadedUsers, teamConfig] = await Promise.all([
      api(`/users/admin?${params.toString()}`),
      api('/teams/config')
    ])
    users.value = loadedUsers
    teamLimit.value = teamConfig.member_limit
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
    pilot_number: user.pilot_number || 1,
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
                  <span>#{{ user.pilot_number }} · RER {{ formatRating(user.rating) }} · {{ teamShortName(user.team_name) }}</span>
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
            <p>{{ editDialogUser.login }} · #{{ editDialogUser.pilot_number }}</p>
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
            <input v-model.number="editForm.pilot_number" type="number" min="1" max="9999" required />
          </label>
          <div class="field">
            <span>{{ t('fields.country') }}</span>
            <CountryCombobox v-model="editForm.country" :options="editCountries" />
          </div>
          <label class="field">
            <span>{{ t('fields.discord') }}</span>
            <input v-model="editForm.discord" maxlength="100" />
          </label>
          <div class="field admin-profile-games">
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
