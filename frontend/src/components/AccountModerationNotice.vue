<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Check, ChevronDown, Eye, Shield, ShieldAlert, Trash2, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { setSession, state } from '../store'
import { formatDateTime as formatDateTimeInZone } from '../timezone'

const { t } = useI18n()
const props = defineProps({
  scope: { type: String, default: 'global' }
})
const detailsOpen = ref(false)
const resubmitting = ref(false)
const dismissing = ref(false)
const resubmitted = ref(false)
const error = ref('')
const now = ref(Date.now())
let clockInterval

const rejection = computed(() => state.user?.last_rejection || null)
const isRejectedRegistration = computed(() => state.user?.status === 'rejected' && rejection.value?.request_type === 'registration')
const isRejectedProfile = computed(() => rejection.value?.request_type === 'profile')
const isUnderReview = computed(() => state.user?.status === 'unapproved')
const showNotice = computed(() => props.scope === 'profile'
  ? isRejectedProfile.value
  : isUnderReview.value || isRejectedRegistration.value)
const resubmitAfter = computed(() => rejection.value?.resubmit_after ? new Date(rejection.value.resubmit_after) : null)
const canResubmit = computed(() => isRejectedRegistration.value && resubmitAfter.value && now.value >= resubmitAfter.value.getTime())

const fieldLabels = computed(() => ({
  login: t('fields.login'),
  email: t('fields.email'),
  first_name: t('fields.firstName'),
  last_name: t('fields.lastName'),
  nickname: t('fields.nickname'),
  pilot_number: t('fields.pilotNumber'),
  country: t('fields.country'),
  discord: t('fields.discord'),
  games: t('fields.games'),
  favorite_car: t('profile.favoriteCar'),
  avatar_color: t('fields.avatarColor'),
  show_pilot_roles: t('profile.showRoles')
}))

const requestRows = computed(() => Object.entries(rejection.value?.request_snapshot || {}).map(([key, value]) => ({
  key,
  label: fieldLabels.value[key] || key.replaceAll('_', ' '),
  value: Array.isArray(value) ? value.join(' / ') : value === null || value === '' ? t('common.none') : String(value)
})))

function formatDate(value) {
  if (!value) return t('common.none')
  return formatDateTimeInZone(value, {
    dateStyle: 'medium',
    timeStyle: 'short'
  })
}

async function resubmitRegistration() {
  if (!canResubmit.value || resubmitting.value) return
  error.value = ''
  resubmitted.value = false
  resubmitting.value = true
  try {
    const user = await api('/users/me/resubmit-registration', { method: 'POST' })
    setSession(state.token, user)
    resubmitted.value = true
  } catch {
    error.value = t('profile.resubmitError')
  } finally {
    resubmitting.value = false
  }
}

async function dismissProfileRejection() {
  if (!isRejectedProfile.value || dismissing.value) return
  error.value = ''
  dismissing.value = true
  try {
    await api('/users/me/rejection', { method: 'DELETE' })
    setSession(state.token, { ...state.user, last_rejection: null })
    detailsOpen.value = false
  } catch {
    error.value = t('profile.dismissRejectionError')
  } finally {
    dismissing.value = false
  }
}

onMounted(() => {
  clockInterval = window.setInterval(() => { now.value = Date.now() }, 30000)
})

onBeforeUnmount(() => window.clearInterval(clockInterval))
</script>

<template>
  <section v-if="showNotice" class="mod-notice" :class="{ 'is-rejected': rejection }" role="status">
    <component :is="rejection ? ShieldAlert : Shield" class="mod-notice__icon" :size="19" />
    <div class="mod-notice__content">
      <strong class="mod-notice__title">
        {{ isUnderReview ? t('profile.waitingApproval') : isRejectedRegistration ? t('profile.registrationRejected') : t('profile.profileRequestRejected') }}
      </strong>
      <p v-if="rejection" class="mod-notice__reason">
        <b>{{ t('profile.rejectionReasonLabel') }}:</b> {{ rejection.reason }}
      </p>
      <p v-else>{{ t('profile.accountUnderReview') }}</p>
      <p v-if="rejection" class="mod-notice__meta">{{ t('profile.requestSubmittedAt', { date: formatDate(rejection.rejected_at) }) }}</p>

      <div v-if="rejection" class="mod-notice__actions">
        <button class="ui-btn ui-btn--ghost ui-btn--sm" type="button" :aria-expanded="detailsOpen" @click="detailsOpen = !detailsOpen">
          <Eye v-if="!detailsOpen" :size="15" />
          <ChevronDown v-else :size="15" />
          {{ detailsOpen ? t('profile.closeRejectedRequest') : t('profile.openRejectedRequest') }}
        </button>
        <button v-if="isRejectedRegistration" class="ui-btn ui-btn--primary ui-btn--sm" type="button" :disabled="!canResubmit || resubmitting" @click="resubmitRegistration">
          <Check :size="15" />
          {{ resubmitting ? t('common.loading') : t('profile.resubmitRegistration') }}
        </button>
        <span v-if="isRejectedRegistration && !canResubmit && resubmitAfter" class="mod-notice__meta">
          {{ t('profile.resubmitAvailableAt', { date: formatDate(resubmitAfter) }) }}
        </span>
        <span v-if="resubmitted" class="mod-notice__success">{{ t('profile.registrationResubmitted') }}</span>
        <span v-if="error" class="mod-notice__error" role="alert">{{ error }}</span>
        <button v-if="props.scope === 'profile' && isRejectedProfile" class="ui-btn ui-btn--danger ui-btn--sm" type="button" :disabled="dismissing" @click="dismissProfileRejection">
          <Trash2 :size="15" />
          {{ dismissing ? t('common.loading') : t('profile.dismissRejection') }}
        </button>
      </div>

      <div v-if="detailsOpen && rejection" class="mod-notice__card">
        <div class="mod-notice__card-head">
          <h2>{{ t('profile.rejectedRequestCard') }}</h2>
          <button class="ui-btn ui-btn--ghost ui-btn--icon ui-btn--sm" type="button" :aria-label="t('common.close')" @click="detailsOpen = false"><X :size="16" /></button>
        </div>
        <p class="mod-notice__meta">{{ t(`moderation.requestTypes.${rejection.request_type}`) }}</p>
        <dl v-if="requestRows.length" class="mod-notice__fields">
          <div v-for="row in requestRows" :key="row.key">
            <dt>{{ row.label }}</dt>
            <dd>{{ row.value }}</dd>
          </div>
        </dl>
      </div>
    </div>
  </section>
</template>

<style scoped>
.mod-notice {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--c-blue-line);
  border-radius: var(--r-md);
  background: var(--c-blue-soft);
  color: var(--c-text);
  font-size: 14px;
  line-height: 1.45;
}

.mod-notice.is-rejected {
  border-color: color-mix(in srgb, var(--bm-red) 34%, transparent);
  background: color-mix(in srgb, var(--bm-red) 8%, transparent);
}

.mod-notice__icon {
  flex: none;
  margin-top: 1px;
  color: var(--c-accent-text);
}

.is-rejected .mod-notice__icon {
  color: var(--bm-red);
}

.mod-notice__content {
  display: grid;
  flex: 1;
  gap: 4px;
  min-width: 0;
}

.mod-notice__content p {
  margin: 0;
}

.mod-notice__title {
  font-size: 15px;
}

.mod-notice__reason {
  overflow-wrap: anywhere;
}

.mod-notice__meta {
  color: var(--c-text-2);
  font-size: 13px;
}

.mod-notice__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.mod-notice__success {
  color: var(--bm-green);
  font-weight: 700;
}

.mod-notice__error {
  color: var(--bm-red);
  font-weight: 600;
}

.mod-notice__card {
  display: grid;
  gap: 6px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--c-line);
}

.mod-notice__card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.mod-notice__card-head h2 {
  margin: 0;
  font-size: 16px;
}

.mod-notice__fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
  gap: 8px 18px;
  margin: 6px 0 0;
}

.mod-notice__fields > div {
  min-width: 0;
}

.mod-notice__fields dt {
  color: var(--c-text-3);
  font-size: 12px;
}

.mod-notice__fields dd {
  margin: 2px 0 0;
  font-weight: 600;
  overflow-wrap: anywhere;
}

@media (max-width: 600px) {
  .mod-notice__actions {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
