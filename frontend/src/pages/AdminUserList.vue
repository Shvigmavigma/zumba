<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Ban, Save, Timer, TimerOff, Trash2, Undo2, X } from 'lucide-vue-next'
import { api } from '../api'
import UserAvatar from '../components/UserAvatar.vue'
import { roleLabel, statusLabel } from '../i18nLabels'
import { state } from '../store'

const { t } = useI18n()
const users = ref([])
const roles = ['admin', 'moder', 'marshall', 'smm', 'pilot']
const error = ref('')
const busyUsers = ref({})
const timeoutDialogUser = ref(null)
const timeoutUntil = ref('')
const timeoutSaving = ref(false)
const teamLimit = ref(5)
const teamLimitSaving = ref(false)
const settingsSaved = ref(false)

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
    const [loadedUsers, teamConfig] = await Promise.all([
      api('/users/admin'),
      api('/teams/config')
    ])
    users.value = loadedUsers
    teamLimit.value = teamConfig.member_limit
  } catch (err) {
    error.value = err.message
  }
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
          <tr v-for="user in users" :key="user.id">
            <td>
              <div class="admin-user-cell">
                <UserAvatar mini :color="user.avatar_color" :label="user.login" />
                <div class="admin-user-info">
                  <strong>{{ user.login }}</strong>
                  <span>#{{ user.pilot_number }}</span>
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
          <tr v-if="!users.length">
            <td colspan="4">
              <div class="empty-row">{{ t('adminUsers.empty') }}</div>
            </td>
          </tr>
        </tbody>
      </table>
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
  </section>
</template>
