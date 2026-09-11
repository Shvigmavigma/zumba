<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Eye, Monitor, Trash2, X } from 'lucide-vue-next'
import { api } from '../api'
import LicenseBadge from '../components/LicenseBadge.vue'
import PaginationControls from '../components/PaginationControls.vue'
import PilotRoles from '../components/PilotRoles.vue'
import UserAvatar from '../components/UserAvatar.vue'
import { formatPilotNumber, formatRating, teamShortName } from '../pilotDisplay'
import { state } from '../store'

const { t } = useI18n()
const users = ref([])
const history = ref([])
const error = ref('')
const viewMode = ref('current')
const page = ref(1)
const selectedUser = ref(null)
const pageSize = 8
const visibleItems = computed(() => viewMode.value === 'current' ? users.value : history.value)
const totalPages = computed(() => Math.max(1, Math.ceil(visibleItems.value.length / pageSize)))
const pagedUsers = computed(() => users.value.slice((page.value - 1) * pageSize, page.value * pageSize))
const pagedHistory = computed(() => history.value.slice((page.value - 1) * pageSize, page.value * pageSize))
const isAdmin = computed(() => state.user?.role === 'admin')

function formatProfileValue(value) {
  if (Array.isArray(value)) return value.length ? value.join(' / ') : t('common.none')
  if (value === null || value === undefined || value === '') return t('common.none')
  if (typeof value === 'object') return Object.entries(value).map(([key, item]) => `${key}: ${item}`).join(', ')
  return String(value)
}

function profileFieldLabel(key) {
  const labels = {
    email: t('fields.email'),
    first_name: t('fields.firstName'),
    last_name: t('fields.lastName'),
    nickname: t('fields.nickname'),
    country: t('fields.country'),
    discord: t('fields.discord'),
    games: t('fields.games'),
    favorite_car: t('profile.favoriteCar')
  }
  return labels[key] || key.replaceAll('_', ' ')
}

function pendingChangeRows(value) {
  if (!value || typeof value !== 'object') return []
  return Object.entries(value)
    .filter(([key]) => key !== 'email')
    .map(([key, item]) => ({ key, label: profileFieldLabel(key), value: formatProfileValue(item) }))
}

function moderationFields(user) {
  const fields = [
    { label: t('fields.login'), value: user.login },
    { label: t('fields.nickname'), value: user.nickname },
    { label: t('fields.firstName'), value: user.first_name },
    { label: t('fields.lastName'), value: user.last_name },
    { label: t('fields.pilotNumber'), value: user.pilot_number === null || user.pilot_number === undefined ? null : `#${formatPilotNumber(user.pilot_number)}` },
    { label: t('fields.country'), value: user.country },
    { label: t('fields.discord'), value: user.discord },
    { label: t('fields.games'), value: formatProfileValue(user.games) },
    { label: t('profile.favoriteCar'), value: user.favorite_car },
    { label: t('fields.team'), value: user.team_name }
  ]
  if (isAdmin.value) fields.splice(7, 0, { label: t('fields.steam'), value: user.steam_id })
  if (isAdmin.value) {
    fields.push({ label: t('moderation.device'), value: user.device_label || t('common.none') })
    if (user.same_device_account_count > 1) {
      fields.push({ label: t('moderation.sameDeviceOtherAccounts'), value: user.same_device_logins?.join(', ') || t('common.none') })
    }
    fields.push({ label: t('moderation.ipId'), value: user.ip_id || t('common.none') })
    if (user.same_ip_account_count > 1) {
      fields.push({ label: t('moderation.sameIpOtherAccounts'), value: user.same_ip_logins?.join(', ') || t('common.none') })
    }
  }
  return fields
}

function hasSharedAccountSignal(user) {
  return Number(user?.same_device_account_count || 1) > 1 || Number(user?.same_ip_account_count || 1) > 1
}

function sharedAccountTooltip(user) {
  const parts = []
  if (Number(user?.same_device_account_count || 1) > 1) {
    parts.push(t('moderation.sameDeviceTooltip', { logins: user.same_device_logins?.join(', ') || t('common.none') }))
  }
  if (Number(user?.same_ip_account_count || 1) > 1) {
    parts.push(t('moderation.sameIpTooltip', { logins: user.same_ip_logins?.join(', ') || t('common.none') }))
  }
  return parts.join(' · ')
}

function openUserCard(user) {
  selectedUser.value = user
}

function closeUserCard() {
  selectedUser.value = null
}

async function loadCurrent() {
  users.value = await api('/users/moderation/pending')
}

async function loadHistory() {
  history.value = await api('/users/moderation/history')
}

async function load() {
  if (viewMode.value === 'current') {
    await loadCurrent()
  } else {
    await loadHistory()
  }
}

async function switchMode(mode) {
  if (viewMode.value === mode) return
  viewMode.value = mode
  page.value = 1
  error.value = ''
  try {
    await load()
  } catch (err) {
    error.value = err.message
  }
}

async function approve(user) {
  try {
    await api(`/users/${user.id}/approve`, { method: 'POST' })
    users.value = users.value.filter((item) => item.id !== user.id)
  } catch (err) {
    error.value = err.message
  }
}

async function reject(user) {
  try {
    await api(`/users/${user.id}/reject`, { method: 'DELETE' })
    users.value = users.value.filter((item) => item.id !== user.id)
  } catch (err) {
    error.value = err.message
  }
}

async function deleteRequest(user) {
  if (!window.confirm(t('moderation.confirmDelete'))) return
  try {
    await api(`/users/${user.id}/moderation`, { method: 'DELETE' })
    users.value = users.value.filter((item) => item.id !== user.id)
  } catch (err) {
    error.value = err.message
  }
}

function formatHistoryDate(value) {
  if (!value) return t('common.none')
  return new Intl.DateTimeFormat(state.locale === 'ru' ? 'ru-RU' : 'en-US', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone: state.timeZone
  }).format(new Date(value))
}

onMounted(async () => {
  try {
    await load()
  } catch (err) {
    error.value = err.message
  }
})

watch([users, history, viewMode], () => {
  if (page.value > totalPages.value) {
    page.value = totalPages.value
  }
})
</script>

<template>
  <section class="section">
    <h1>{{ t('nav.moderation') }}</h1>
    <div class="moderation-view-switch" role="tablist" :aria-label="t('moderation.viewAria')">
      <button type="button" :class="{ active: viewMode === 'current' }" :aria-selected="viewMode === 'current'" role="tab" @click="switchMode('current')">
        {{ t('moderation.current') }} <span>{{ users.length }}</span>
      </button>
      <button type="button" :class="{ active: viewMode === 'completed' }" :aria-selected="viewMode === 'completed'" role="tab" @click="switchMode('completed')">
        {{ t('moderation.completed') }}
      </button>
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <div v-if="viewMode === 'current'" class="grid">
      <article v-for="user in pagedUsers" :key="user.id" class="card user-moderation-card" :class="{ 'has-device-match': isAdmin && hasSharedAccountSignal(user) }">
        <div class="user-list-cell">
          <UserAvatar :src="user.avatar_url" :color="user.avatar_color" :label="user.nickname || user.login" />
          <div class="user-moderation-main">
            <span class="user-name-line">
              <strong>{{ user.first_name }} {{ user.last_name }}</strong>
              <LicenseBadge :user="user" />
              <PilotRoles :roles="user.pilot_roles" />
            </span>
            <span>{{ user.nickname }}</span>
          </div>
        </div>
        <div class="user-moderation-meta">
          <p class="muted">#{{ formatPilotNumber(user.pilot_number) }} - RER {{ formatRating(user.rating) }} - {{ teamShortName(user.team_name, user.team_abbreviation) }}<template v-if="isAdmin"> - {{ t('fields.steam') }} {{ user.steam_id }}</template></p>
          <span
            v-if="user.steam_blacklisted"
            class="status-badge status-banned moderation-blacklist-badge"
            :title="t('moderation.steamBlacklistReason', { reason: user.steam_blacklist_reason || t('moderation.steamBlacklistNoReason') })"
            :aria-label="t('moderation.steamBlacklistReason', { reason: user.steam_blacklist_reason || t('moderation.steamBlacklistNoReason') })"
          >{{ t('moderation.steamBlacklisted') }}</span>
          <div v-if="isAdmin && (user.device_label || user.ip_id || user.same_device_account_count > 1 || user.same_ip_account_count > 1)" class="moderation-device-meta">
            <span v-if="user.device_label" class="moderation-device-label"><Monitor :size="14" /> {{ t('moderation.device') }}: {{ user.device_label }}</span>
            <span
              v-if="user.same_device_account_count > 1"
              class="moderation-device-match"
              :title="sharedAccountTooltip(user)"
            >{{ t('moderation.sameDeviceAccounts', { count: user.same_device_account_count }) }}</span>
            <span v-if="user.same_ip_account_count > 1" class="moderation-device-match">{{ t('moderation.sameIpAccounts', { count: user.same_ip_account_count }) }}</span>
            <span v-if="user.ip_id" class="moderation-device-match" :title="user.same_ip_account_count > 1 ? t('moderation.sameIpTooltip', { logins: user.same_ip_logins?.join(', ') || t('common.none') }) : ''">{{ t('moderation.ipId') }}: {{ user.ip_id }}</span>
          </div>
          <button v-if="user.pending_profile_changes" class="moderation-change-preview" type="button" @click="openUserCard(user)">
            <span>
              <strong>{{ t('moderation.pendingChangesCard') }}</strong>
              <small>{{ t('moderation.pendingChangesCardHint', { count: pendingChangeRows(user.pending_profile_changes).length }) }}</small>
            </span>
            <Eye :size="17" />
          </button>
        </div>
        <div class="toolbar">
          <button
            class="icon-button"
            type="button"
            :title="t('moderation.openUserCard')"
            :aria-label="t('moderation.openUserCard')"
            @click="openUserCard(user)"
          >
            <Eye :size="16" />
          </button>
          <button
            class="button primary"
            :disabled="user.steam_blacklisted && !isAdmin"
            :title="user.steam_blacklisted && !isAdmin ? t('moderation.steamBlacklistAdminOnly') : ''"
            @click="approve(user)"
          >{{ t('common.approve') }}</button>
          <span v-if="user.steam_blacklisted && !isAdmin" class="muted moderation-blacklist-lock">{{ t('moderation.steamBlacklistAdminOnly') }}</span>
          <button class="button danger" @click="reject(user)">{{ t('common.reject') }}</button>
          <button
            v-if="isAdmin"
            class="icon-button danger-icon"
            type="button"
            :title="t('moderation.deleteRequest')"
            :aria-label="t('moderation.deleteRequest')"
            @click="deleteRequest(user)"
          >
            <Trash2 :size="16" />
          </button>
        </div>
      </article>
    </div>
    <div v-else class="grid">
      <article v-for="request in pagedHistory" :key="request.id" class="card moderation-history-card" :class="{ 'has-device-match': isAdmin && hasSharedAccountSignal(request) }">
        <div class="user-list-cell">
          <UserAvatar :label="request.nickname || request.login" />
          <div class="user-moderation-main">
            <span class="user-name-line"><strong>{{ request.first_name }} {{ request.last_name }}</strong><PilotRoles :roles="request.pilot_roles" /></span>
            <span>{{ request.nickname || request.login }}</span>
          </div>
        </div>
        <div class="user-moderation-meta">
          <p v-if="isAdmin" class="muted">#{{ formatPilotNumber(request.pilot_number) }} - {{ t('fields.steam') }} {{ request.steam_id }}</p>
          <div v-if="isAdmin && (request.device_label || request.ip_id || request.same_device_account_count > 1 || request.same_ip_account_count > 1)" class="moderation-device-meta">
            <span v-if="request.device_label" class="moderation-device-label"><Monitor :size="14" /> {{ t('moderation.device') }}: {{ request.device_label }}</span>
            <span v-if="request.same_device_account_count > 1" class="moderation-device-match">{{ t('moderation.sameDeviceAccounts', { count: request.same_device_account_count }) }}</span>
            <span v-if="request.same_ip_account_count > 1" class="moderation-device-match">{{ t('moderation.sameIpAccounts', { count: request.same_ip_account_count }) }}</span>
            <span v-if="request.ip_id" class="moderation-device-match">{{ t('moderation.ipId') }}: {{ request.ip_id }}</span>
          </div>
          <p class="muted">{{ t(`moderation.requestTypes.${request.request_type}`) }} · {{ t('moderation.resolvedAt', { date: formatHistoryDate(request.resolved_at) }) }}</p>
        </div>
        <div class="moderation-history-resolution" :class="`is-${request.resolution}`">
          {{ t(`moderation.resolutions.${request.resolution}`) }}
        </div>
      </article>
      <p v-if="!history.length" class="muted moderation-empty">{{ t('moderation.historyEmpty') }}</p>
    </div>
    <PaginationControls v-model:page="page" :page-size="pageSize" :total-items="visibleItems.length" />

    <div v-if="selectedUser" class="penalty-modal-backdrop" @click.self="closeUserCard">
      <article class="card penalty-modal moderation-user-dialog" role="dialog" aria-modal="true" :aria-label="t('moderation.userCardTitle')">
        <div class="section-header penalty-modal-head">
          <div>
            <h2>{{ t('moderation.userCardTitle') }}</h2>
            <p class="muted">{{ selectedUser.first_name }} {{ selectedUser.last_name }} · @{{ selectedUser.login }}</p>
          </div>
          <button class="icon-button" type="button" :title="t('common.close')" :aria-label="t('common.close')" @click="closeUserCard">
            <X :size="18" />
          </button>
        </div>

        <section>
          <h3>{{ t('moderation.profileData') }}</h3>
          <dl class="moderation-profile-grid">
            <div v-for="field in moderationFields(selectedUser)" :key="field.label">
              <dt>{{ field.label }}</dt>
              <dd>{{ formatProfileValue(field.value) }}</dd>
            </div>
          </dl>
        </section>

        <section class="moderation-change-list">
          <h3>{{ t('moderation.requestedChanges') }}</h3>
          <dl v-if="pendingChangeRows(selectedUser.pending_profile_changes).length" class="moderation-profile-grid">
            <div v-for="change in pendingChangeRows(selectedUser.pending_profile_changes)" :key="change.key">
              <dt>{{ change.label }}</dt>
              <dd>{{ change.value }}</dd>
            </div>
          </dl>
          <p v-else class="muted">{{ t('moderation.noRequestedChanges') }}</p>
        </section>

        <div class="toolbar moderation-dialog-actions">
          <button class="button" type="button" @click="closeUserCard">{{ t('common.close') }}</button>
        </div>
      </article>
    </div>
  </section>
</template>
