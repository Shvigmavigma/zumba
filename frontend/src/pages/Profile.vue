<script setup>
import { computed, onMounted, ref } from 'vue'
import { Edit3, RefreshCw } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import UserAvatar from '../components/UserAvatar.vue'
import { countryLabel, gameLabel, roleLabel, statusLabel } from '../i18nLabels'
import { formatRating, pilotName, teamShortName } from '../pilotDisplay'
import { setSession, state } from '../store'

const { t } = useI18n()
const error = ref('')
const loading = ref(false)
const user = computed(() => state.user)
const displayName = computed(() => pilotName(user.value, user.value?.login))
const gameList = computed(() => user.value?.games?.length ? user.value.games.map((game) => gameLabel(t, game)).join(' / ') : t('common.none'))
const pendingChanges = computed(() => {
  const changes = user.value?.pending_profile_changes
  if (!changes || typeof changes !== 'object') return []
  return Object.entries(changes).map(([key, value]) => ({
    key,
    label: profileFieldLabel(key),
    value: formatProfileValue(value)
  }))
})
const profileFields = computed(() => {
  if (!user.value) return []
  return [
    { label: t('fields.email'), value: user.value.email },
    { label: t('fields.login'), value: user.value.login },
    { label: t('fields.nickname'), value: user.value.nickname },
    { label: t('fields.firstName'), value: user.value.first_name },
    { label: t('fields.lastName'), value: user.value.last_name },
    { label: t('fields.pilotNumber'), value: user.value.pilot_number ? `#${user.value.pilot_number}` : null },
    { label: t('fields.country'), value: countryLabel(t, user.value.country) },
    { label: t('fields.team'), value: user.value.team_name || t('common.none') },
    { label: t('fields.steam'), value: user.value.steam_id },
    { label: t('fields.discord'), value: user.value.discord },
    { label: t('fields.games'), value: gameList.value },
    { label: t('common.role'), value: roleLabel(t, user.value.role) },
    { label: t('common.status'), value: statusLabel(t, user.value.status) },
    { label: 'RER', value: formatRating(user.value.rating) },
    { label: 'SR', value: Number.isFinite(Number(user.value.sr)) ? Number(user.value.sr).toFixed(1) : null },
    { label: t('fields.ratingRaces'), value: user.value.rating_race_count ?? 0 },
    { label: t('fields.avatarColor'), value: user.value.avatar_color },
    { label: t('fields.joinedAt'), value: formatDateTime(user.value.created_at) },
    { label: t('profile.updatedAt'), value: formatDateTime(user.value.updated_at) },
    { label: t('profile.banEnd'), value: formatDateTime(user.value.ban_end) },
    { label: t('profile.timeoutStart'), value: formatDateTime(user.value.timeout_start) },
    { label: t('profile.timeoutEnd'), value: formatDateTime(user.value.timeout_end) }
  ]
})

function formatDateTime(value) {
  if (!value) return t('common.none')
  return new Intl.DateTimeFormat(state.locale === 'ru' ? 'ru-RU' : 'en-US', {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(value))
}

function formatProfileValue(value) {
  if (Array.isArray(value)) return value.length ? value.join(' / ') : t('common.none')
  if (value === null || value === undefined || value === '') return t('common.none')
  if (typeof value === 'object') return JSON.stringify(value)
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
    avatar_color: t('fields.avatarColor'),
    games: t('fields.games')
  }
  return labels[key] || key.replaceAll('_', ' ')
}

async function refreshProfile() {
  if (!state.token) return
  loading.value = true
  error.value = ''
  try {
    const freshUser = await api('/auth/me')
    setSession(state.token, freshUser)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(refreshProfile)
</script>

<template>
  <section class="section pilot-profile-page profile-overview-page">
    <div class="section-header profile-overview-header">
      <div>
        <h1>{{ t('nav.profile') }}</h1>
        <p v-if="user" class="muted">{{ displayName }} - {{ user.email }}</p>
      </div>
      <div class="toolbar">
        <button class="icon-button" type="button" :title="t('common.reload')" :disabled="loading" @click="refreshProfile">
          <RefreshCw :size="18" />
        </button>
        <RouterLink v-if="user" class="button primary" to="/profile/edit">
          <Edit3 :size="16" />
          {{ t('common.edit') }}
        </RouterLink>
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <article v-if="user" class="card pilot-profile-card profile-overview-card">
      <UserAvatar class="pilot-profile-avatar" :color="user.avatar_color" :label="displayName" />
      <div class="pilot-profile-main">
        <div class="pilot-profile-head">
          <h1>{{ displayName }}</h1>
          <p class="muted">@{{ user.login }} - ID {{ user.id }}</p>
        </div>

        <div class="pilot-profile-badges">
          <span class="pill">RER {{ formatRating(user.rating) }}</span>
          <span class="pill">SR {{ Number(user.sr).toFixed(1) }}</span>
          <span class="pill">#{{ user.pilot_number }}</span>
          <span class="team-mini-chip" :title="user.team_name || t('common.none')">{{ teamShortName(user.team_name) }}</span>
          <span class="status-badge" :class="`status-${user.status}`">{{ statusLabel(t, user.status) }}</span>
          <span class="pill">{{ roleLabel(t, user.role) }}</span>
        </div>

        <div class="profile-alerts">
          <p v-if="user.status === 'unapproved'" class="pill">{{ t('profile.waitingApproval') }}</p>
          <p v-if="pendingChanges.length" class="pill">{{ t('profile.pendingChanges') }}</p>
        </div>

        <dl class="pilot-public-grid profile-info-grid">
          <div v-for="field in profileFields" :key="field.label">
            <dt>{{ field.label }}</dt>
            <dd :title="String(field.value || t('common.none'))">{{ field.value || t('common.none') }}</dd>
          </div>
        </dl>

        <div v-if="pendingChanges.length" class="pilot-games profile-pending-changes">
          <span>{{ t('profile.pendingChangesTitle') }}</span>
          <div>
            <span v-for="change in pendingChanges" :key="change.key" class="pill">{{ change.label }}: {{ change.value }}</span>
          </div>
        </div>
      </div>
    </article>

    <RouterLink v-else class="button" to="/login">{{ t('nav.login') }}</RouterLink>
  </section>
</template>
