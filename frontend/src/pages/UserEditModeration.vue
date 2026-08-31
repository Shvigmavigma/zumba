<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Trash2 } from 'lucide-vue-next'
import { api } from '../api'
import LicenseBadge from '../components/LicenseBadge.vue'
import PaginationControls from '../components/PaginationControls.vue'
import UserAvatar from '../components/UserAvatar.vue'
import { formatPilotNumber, formatRating, teamShortName } from '../pilotDisplay'
import { state } from '../store'

const { t } = useI18n()
const users = ref([])
const history = ref([])
const error = ref('')
const viewMode = ref('current')
const page = ref(1)
const pageSize = 8
const visibleItems = computed(() => viewMode.value === 'current' ? users.value : history.value)
const totalPages = computed(() => Math.max(1, Math.ceil(visibleItems.value.length / pageSize)))
const pagedUsers = computed(() => users.value.slice((page.value - 1) * pageSize, page.value * pageSize))
const pagedHistory = computed(() => history.value.slice((page.value - 1) * pageSize, page.value * pageSize))
const isAdmin = computed(() => state.user?.role === 'admin')

function visiblePendingChanges(value) {
  if (!value || typeof value !== 'object') return String(value || '')
  return JSON.stringify(Object.fromEntries(Object.entries(value).filter(([key]) => key !== 'email')))
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
      <article v-for="user in pagedUsers" :key="user.id" class="card user-moderation-card">
        <div class="user-list-cell">
          <UserAvatar :src="user.avatar_url" :color="user.avatar_color" :label="user.nickname || user.login" />
          <div class="user-moderation-main">
            <span class="user-name-line">
              <strong>{{ user.first_name }} {{ user.last_name }}</strong>
              <LicenseBadge :user="user" />
            </span>
            <span>{{ user.nickname }}</span>
          </div>
        </div>
        <div class="user-moderation-meta">
          <p class="muted">#{{ formatPilotNumber(user.pilot_number) }} - RER {{ formatRating(user.rating) }} - {{ teamShortName(user.team_name, user.team_abbreviation) }} - {{ t('fields.steam') }} {{ user.steam_id }}</p>
          <span
            v-if="user.steam_blacklisted"
            class="status-badge status-banned moderation-blacklist-badge"
            :title="t('moderation.steamBlacklistReason', { reason: user.steam_blacklist_reason || t('moderation.steamBlacklistNoReason') })"
            :aria-label="t('moderation.steamBlacklistReason', { reason: user.steam_blacklist_reason || t('moderation.steamBlacklistNoReason') })"
          >{{ t('moderation.steamBlacklisted') }}</span>
          <p v-if="user.pending_profile_changes" class="muted">{{ t('moderation.pendingProfileChanges', { changes: visiblePendingChanges(user.pending_profile_changes) }) }}</p>
        </div>
        <div class="toolbar">
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
      <article v-for="request in pagedHistory" :key="request.id" class="card moderation-history-card">
        <div class="user-list-cell">
          <UserAvatar :label="request.nickname || request.login" />
          <div class="user-moderation-main">
            <span class="user-name-line"><strong>{{ request.first_name }} {{ request.last_name }}</strong></span>
            <span>{{ request.nickname || request.login }}</span>
          </div>
        </div>
        <div class="user-moderation-meta">
          <p class="muted">#{{ formatPilotNumber(request.pilot_number) }} - {{ t('fields.steam') }} {{ request.steam_id }}</p>
          <p class="muted">{{ t(`moderation.requestTypes.${request.request_type}`) }} · {{ t('moderation.resolvedAt', { date: formatHistoryDate(request.resolved_at) }) }}</p>
        </div>
        <div class="moderation-history-resolution" :class="`is-${request.resolution}`">
          {{ t(`moderation.resolutions.${request.resolution}`) }}
        </div>
      </article>
      <p v-if="!history.length" class="muted moderation-empty">{{ t('moderation.historyEmpty') }}</p>
    </div>
    <PaginationControls v-model:page="page" :page-size="pageSize" :total-items="visibleItems.length" />
  </section>
</template>
