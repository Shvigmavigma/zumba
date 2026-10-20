<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Clock3, PencilLine, RefreshCw } from 'lucide-vue-next'
import { api } from '../api'
import AccountModerationNotice from '../components/AccountModerationNotice.vue'
import EmptyState from '../ui/EmptyState.vue'
import PilotProfileView from './profile/PilotProfileView.vue'
import { countryLabel, gameLabel, roleLabel, statusLabel } from '../i18nLabels'
import { DEFAULT_LICENSE_TIERS, formatPilotNumber, formatRating, normalizeLicenseTiers, ratingForGame, ratingLicenseTier, ratingRaceCountForGame } from '../pilotDisplay'
import { setSession, state } from '../store'
import { formatDateTime as formatDateTimeInZone } from '../timezone'

const { t } = useI18n()
const error = ref('')
const loading = ref(false)
const user = computed(() => state.user)
const licenseTiers = ref(DEFAULT_LICENSE_TIERS)
const gameList = computed(() => (user.value?.games?.length ? user.value.games.map((game) => gameLabel(t, game)).join(' / ') : t('common.none')))
const profileLicense = computed(() => ratingLicenseTier(ratingForGame(user.value, 'ACC'), licenseTiers.value))
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
    { label: t('fields.pilotNumber'), value: user.value.pilot_number !== null && user.value.pilot_number !== undefined ? `#${formatPilotNumber(user.value.pilot_number)}` : null },
    { label: t('fields.country'), value: countryLabel(t, user.value.country) },
    { label: t('fields.team'), value: user.value.team_name || t('common.none') },
    { label: t('fields.discord'), value: user.value.discord },
    { label: t('fields.games'), value: gameList.value },
    { label: t('profile.favoriteCar'), value: user.value.favorite_car },
    { label: t('common.role'), value: roleLabel(t, user.value.role) },
    { label: t('common.status'), value: statusLabel(t, user.value.status) },
    { label: 'ACC RER', value: formatRating(ratingForGame(user.value, 'ACC')) },
    { label: t('fields.license'), value: profileLicense.value?.name },
    { label: 'SR', value: Number.isFinite(Number(user.value.sr)) ? Number(user.value.sr).toFixed(1) : null },
    { label: t('fields.ratingRaces'), value: ratingRaceCountForGame(user.value, 'ACC') },
    { label: t('fields.joinedAt'), value: formatDateTime(user.value.created_at) },
    { label: t('profile.updatedAt'), value: formatDateTime(user.value.updated_at) },
    { label: t('profile.banEnd'), value: formatDateTime(user.value.ban_end) },
    { label: t('profile.timeoutStart'), value: formatDateTime(user.value.timeout_start) },
    { label: t('profile.timeoutEnd'), value: formatDateTime(user.value.timeout_end) }
  ]
})

function formatDateTime(value) {
  if (!value) return t('common.none')
  return formatDateTimeInZone(value, { dateStyle: 'medium', timeStyle: 'short' })
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
    games: t('fields.games'),
    favorite_car: t('profile.favoriteCar')
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

async function loadLicenseSettings() {
  try {
    licenseTiers.value = normalizeLicenseTiers(await api('/app-settings/licenses'))
  } catch {
    licenseTiers.value = DEFAULT_LICENSE_TIERS
  }
}

onMounted(() => {
  refreshProfile()
  loadLicenseSettings()
})
</script>

<template>
  <div class="ui-page ui-shell ui-shell--wide">
    <PilotProfileView v-if="user" :pilot="user" :tiers="licenseTiers" own>
      <template #actions>
        <RouterLink class="ui-btn ui-btn--primary ui-btn--sm" to="/profile/edit"><PencilLine :size="15" />{{ t('profilePage.actions.edit') }}</RouterLink>
        <button class="ui-btn ui-btn--outline ui-btn--sm" type="button" :disabled="loading" @click="refreshProfile">
          <RefreshCw :size="15" :class="{ 'own__spin': loading }" />{{ t('profilePage.actions.refresh') }}
        </button>
      </template>

      <template #alerts>
        <p v-if="error" class="ui-alert">{{ error }}</p>
        <AccountModerationNotice scope="profile" />
        <p v-if="pendingChanges.length" class="ui-alert ui-alert--info"><Clock3 :size="17" />{{ t('profile.pendingChanges') }}</p>
      </template>

      <template #account>
        <section class="ui-card">
          <header class="ui-card__title">
            <p class="ui-eyebrow ui-eyebrow--accent">{{ t('profilePage.tabs.account') }}</p>
            <h2>{{ t('profilePage.account.title') }}</h2>
            <p class="own__hint">{{ t('profilePage.account.hint') }}</p>
          </header>
          <dl class="ui-kv">
            <div v-for="field in profileFields" :key="field.label">
              <dt>{{ field.label }}</dt>
              <dd :title="String(field.value || t('common.none'))">{{ field.value || t('common.none') }}</dd>
            </div>
          </dl>
        </section>

        <section v-if="pendingChanges.length" class="ui-card">
          <header class="ui-card__title">
            <p class="ui-eyebrow ui-eyebrow--accent">{{ t('profile.pendingChangesTitle') }}</p>
            <h2>{{ t('profilePage.account.pendingTitle') }}</h2>
            <p class="own__hint">{{ t('profilePage.account.pendingHint') }}</p>
          </header>
          <dl class="ui-kv">
            <div v-for="change in pendingChanges" :key="change.key">
              <dt>{{ change.label }}</dt>
              <dd>{{ change.value }}</dd>
            </div>
          </dl>
        </section>
      </template>
    </PilotProfileView>

    <EmptyState v-else :title="t('nav.login')">
      <RouterLink class="ui-btn ui-btn--primary ui-btn--sm" to="/login">{{ t('nav.login') }}</RouterLink>
    </EmptyState>
  </div>
</template>

<style scoped>
.own__hint {
  margin: 0;
  color: var(--c-text-3);
  font-size: 13px;
}

.own__spin {
  animation: own-spin 900ms linear infinite;
}

@keyframes own-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
