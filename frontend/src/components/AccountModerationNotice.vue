<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Check, ChevronDown, Eye, Shield, Trash2, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { setSession, state } from '../store'

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
  return new Intl.DateTimeFormat(state.locale === 'ru' ? 'ru-RU' : 'en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: state.timeZone
  }).format(new Date(value))
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
  <section v-if="showNotice" class="account-moderation-notice" :class="{ 'is-rejected': rejection }" role="status">
    <Shield :size="19" />
    <div class="account-moderation-content">
      <strong>
        {{ isUnderReview ? t('profile.waitingApproval') : isRejectedRegistration ? t('profile.registrationRejected') : t('profile.profileRequestRejected') }}
      </strong>
      <p v-if="rejection" class="account-rejection-reason">
        <span>{{ t('profile.rejectionReasonLabel') }}:</span> {{ rejection.reason }}
      </p>
      <p v-else>{{ t('profile.accountUnderReview') }}</p>
      <p v-if="rejection" class="account-rejection-date">{{ t('profile.requestSubmittedAt', { date: formatDate(rejection.rejected_at) }) }}</p>

      <div class="account-moderation-actions">
        <button v-if="rejection" class="button small" type="button" :aria-expanded="detailsOpen" @click="detailsOpen = !detailsOpen">
          <Eye v-if="!detailsOpen" :size="15" />
          <ChevronDown v-else :size="15" />
          {{ detailsOpen ? t('profile.closeRejectedRequest') : t('profile.openRejectedRequest') }}
        </button>
        <button v-if="isRejectedRegistration" class="button small primary" type="button" :disabled="!canResubmit || resubmitting" @click="resubmitRegistration">
          <Check :size="15" />
          {{ resubmitting ? t('common.loading') : t('profile.resubmitRegistration') }}
        </button>
        <span v-if="isRejectedRegistration && !canResubmit && resubmitAfter" class="muted account-resubmit-time">
          {{ t('profile.resubmitAvailableAt', { date: formatDate(resubmitAfter) }) }}
        </span>
        <span v-if="resubmitted" class="account-resubmit-success">{{ t('profile.registrationResubmitted') }}</span>
        <span v-if="error" class="error">{{ error }}</span>
        <button v-if="props.scope === 'profile' && isRejectedProfile" class="button small danger" type="button" :disabled="dismissing" @click="dismissProfileRejection">
          <Trash2 :size="15" />
          {{ dismissing ? t('common.loading') : t('profile.dismissRejection') }}
        </button>
      </div>

      <div v-if="detailsOpen && rejection" class="account-request-card">
        <div class="account-request-card-heading">
          <h2>{{ t('profile.rejectedRequestCard') }}</h2>
          <button class="icon-button" type="button" :aria-label="t('common.close')" @click="detailsOpen = false"><X :size="16" /></button>
        </div>
        <p class="account-request-type">{{ t(`moderation.requestTypes.${rejection.request_type}`) }}</p>
        <dl v-if="requestRows.length" class="account-request-fields">
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
.account-moderation-notice {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  margin-bottom: 16px;
  padding: 14px 16px;
  border: 1px solid color-mix(in srgb, var(--primary) 30%, var(--border));
  border-radius: var(--control-radius);
  background: color-mix(in srgb, var(--primary) 8%, var(--panel));
  color: var(--text);
}

.account-moderation-notice > svg {
  flex: 0 0 auto;
  margin-top: 2px;
  color: var(--primary);
}

.account-moderation-notice.is-rejected {
  border-color: color-mix(in srgb, var(--danger) 38%, var(--border));
  background: color-mix(in srgb, var(--danger) 6%, var(--panel));
}

.account-moderation-notice.is-rejected > svg {
  color: var(--danger);
}

.account-moderation-content { min-width: 0; flex: 1; }
.account-moderation-content > strong { display: block; margin-bottom: 4px; }
.account-moderation-content p { margin: 4px 0; }
.account-rejection-reason span { font-weight: 700; }
.account-rejection-date, .account-resubmit-time { font-size: 13px; }
.account-moderation-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.account-resubmit-success { color: var(--success); font-weight: 700; }
.account-request-card { margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--border); }
.account-request-card-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.account-request-card-heading h2 { margin: 0; font-size: 17px; }
.account-request-type { color: var(--muted); font-size: 13px; }
.account-request-fields { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr)); gap: 8px 18px; margin: 12px 0 0; }
.account-request-fields > div { min-width: 0; }
.account-request-fields dt { color: var(--muted); font-size: 12px; }
.account-request-fields dd { margin: 2px 0 0; overflow-wrap: anywhere; font-weight: 600; }

@media (max-width: 600px) {
  .account-moderation-notice { padding: 12px; }
  .account-moderation-actions { align-items: flex-start; flex-direction: column; }
}
</style>
