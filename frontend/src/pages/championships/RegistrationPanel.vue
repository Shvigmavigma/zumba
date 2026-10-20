<script setup>
// The registration "ticket": where registration stands, a countdown to the
// next deadline, and the one thing the pilot can do now — apply, wait for a
// decision, change the car, or sign in.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { AlertCircle, ArrowRight, CheckCircle2, Clock3, LogIn, Lock, Send, Users, XCircle } from 'lucide-vue-next'
import Countdown from '../../ui/fx/Countdown.vue'
import FormField from '../../ui/FormField.vue'
import { formatPilotNumber } from '../../pilotDisplay'
import { state } from '../../store'
import { formatInTimeZone } from '../../timezone'
import { registrationPhase } from './helpers'

const props = defineProps({
  championship: { type: Object, required: true },
  allowedCars: { type: Array, default: () => [] },
  myRegistration: { type: Object, default: null },
  canChangeMyCar: { type: Boolean, default: false }
})
const emit = defineEmits(['apply', 'change-car'])
const pilotNumber = defineModel('pilotNumber', { type: String, default: '' })
const car = defineModel('car', { type: String, default: '' })
const myCar = defineModel('myCar', { type: String, default: '' })

const { t } = useI18n()

const phase = computed(() => registrationPhase(props.championship))
const status = computed(() => props.championship.my_registration_status || '')

const PHASE_CHIPS = {
  open: { tone: 'green', key: 'champPage.reg.phase.open', live: true },
  soon: { tone: 'amber', key: 'champPage.reg.phase.soon' },
  closed: { tone: '', key: 'champPage.reg.phase.closed' },
  draft: { tone: 'amber', key: 'champPage.reg.phase.draft' }
}
const chip = computed(() => PHASE_CHIPS[phase.value])

const countdown = computed(() => {
  if (phase.value === 'open') return { target: props.championship.registration_end, label: t('champPage.reg.toClose') }
  if (phase.value === 'soon') return { target: props.championship.registration_start, label: t('champPage.reg.toOpen') }
  return null
})

/** Status card shown instead of (or above) the form. */
const notice = computed(() => {
  const mine = props.myRegistration
  if (status.value === 'approved') {
    const details = mine ? t('champPage.reg.approvedText', { number: formatPilotNumber(mine.pilot_number), car: mine.car_model || '—' }) : ''
    return { tone: 'green', icon: CheckCircle2, title: t('championships.requestApproved'), text: details }
  }
  if (status.value === 'pending') return { tone: 'amber', icon: Clock3, title: t('championships.requestPending'), text: t('champPage.reg.pendingText') }
  if (status.value === 'rejected') return { tone: 'red', icon: XCircle, title: t('championships.requestRejected'), text: t('champPage.reg.rejectedText') }
  if (props.championship.can_apply) return null
  if (phase.value === 'draft') return { tone: 'amber', icon: AlertCircle, title: t('champPage.reg.draftTitle'), text: t('champPage.reg.draftText') }
  if (phase.value === 'soon') return { tone: 'blue', icon: Clock3, title: t('champPage.reg.soonTitle', { date: longDate(props.championship.registration_start) }), text: t('champPage.reg.soonText') }
  if (phase.value === 'closed') return { tone: '', icon: Lock, title: t('champPage.reg.closedTitle'), text: t('champPage.reg.closedText') }
  if (props.championship.is_team_event) return { tone: 'blue', icon: Users, title: t('champPage.reg.teamTitle'), text: t('champPage.reg.teamText') }
  if (!state.user) return { tone: 'blue', icon: LogIn, title: t('champPage.reg.loginTitle'), text: t('champPage.reg.loginText'), login: true }
  return { tone: '', icon: Lock, title: t('champPage.reg.unavailableTitle'), text: t('champPage.reg.unavailableText') }
})

const carHint = computed(() => {
  const classes = (props.championship.classes || []).join(', ')
  const base = props.allowedCars.length ? t('champPage.reg.carHint', { classes }) : t('champPage.reg.carHintFree')
  const rule = props.championship.car_change_allowed ? t('champPage.reg.carChangeAllowed') : t('champPage.reg.carChangeLocked')
  return `${base} ${rule}`
})

function longDate(value) {
  return formatInTimeZone(value, { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })
}

function shortDate(value) {
  return formatInTimeZone(value, { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <section class="reg ui-glass ui-glass--strong" :class="`is-${phase}`" :aria-label="t('championships.registration')">
    <header class="reg__head">
      <span class="ui-eyebrow">{{ t('championships.registration') }}</span>
      <span class="ui-chip" :class="chip.tone ? `ui-chip--${chip.tone}` : ''">
        <span class="ui-dot" :class="[chip.tone ? `ui-dot--${chip.tone}` : '', { 'ui-dot--live': chip.live }]"></span>
        {{ t(chip.key) }}
      </span>
    </header>

    <p class="reg__window ui-num">
      <span>{{ shortDate(championship.registration_start) }}</span>
      <ArrowRight :size="14" aria-hidden="true" />
      <span>{{ shortDate(championship.registration_end) }}</span>
    </p>

    <div v-if="countdown" class="reg__clock">
      <span class="reg__clock-label">{{ countdown.label }}</span>
      <Countdown :target="countdown.target" size="sm" />
    </div>

    <div v-if="notice" class="reg__notice" :class="notice.tone ? `is-${notice.tone}` : ''" role="status">
      <component :is="notice.icon" class="reg__notice-icon" :size="20" aria-hidden="true" />
      <div>
        <strong>{{ notice.title }}</strong>
        <p v-if="notice.text">{{ notice.text }}</p>
      </div>
    </div>

    <RouterLink v-if="notice?.login" v-magnet class="ui-btn ui-btn--primary ui-btn--lg ui-btn--block" to="/login">
      <LogIn :size="17" />{{ t('champPage.reg.loginCta') }}
    </RouterLink>

    <form v-if="championship.can_apply" class="reg__form" @submit.prevent="emit('apply')">
      <FormField :label="t('fields.pilotNumber')" :hint="t('champPage.reg.numberHint')" required>
        <template #default="{ id, describedBy }">
          <input
            :id="id"
            v-model="pilotNumber"
            class="ui-input reg__number ui-num"
            inputmode="numeric"
            pattern="[0-9]{3}"
            minlength="3"
            maxlength="3"
            placeholder="000"
            autocomplete="off"
            required
            :aria-describedby="describedBy"
          />
        </template>
      </FormField>

      <FormField :label="t('championships.car')" :hint="carHint" required>
        <template #default="{ id, describedBy }">
          <select v-if="allowedCars.length" :id="id" v-model="car" class="ui-select" required :aria-describedby="describedBy">
            <option value="" disabled>{{ t('championships.chooseCar') }}</option>
            <option v-for="item in allowedCars" :key="item" :value="item">{{ item }}</option>
          </select>
          <input v-else :id="id" v-model="car" class="ui-input" maxlength="80" required :placeholder="t('champPage.reg.carPlaceholder')" :aria-describedby="describedBy" />
        </template>
      </FormField>

      <button v-magnet v-spark class="ui-btn ui-btn--primary ui-btn--lg ui-btn--block" type="submit">
        <Send :size="17" />{{ t('championships.submitRequest') }}
      </button>
      <p class="reg__note">{{ t('champPage.reg.reviewNote') }}</p>
    </form>

    <form v-if="canChangeMyCar" class="reg__form reg__form--car" @submit.prevent="emit('change-car')">
      <FormField :label="t('championships.myCar')" :hint="t('champPage.reg.myCarHint')">
        <template #default="{ id, describedBy }">
          <select v-if="allowedCars.length" :id="id" v-model="myCar" class="ui-select" required :aria-describedby="describedBy">
            <option value="" disabled>{{ t('championships.chooseCar') }}</option>
            <option v-for="item in allowedCars" :key="item" :value="item">{{ item }}</option>
          </select>
          <input v-else :id="id" v-model="myCar" class="ui-input" maxlength="80" required :aria-describedby="describedBy" />
        </template>
      </FormField>
      <button class="ui-btn ui-btn--outline ui-btn--block" type="submit">{{ t('championships.change') }}</button>
    </form>
  </section>
</template>

<style scoped>
.reg {
  display: grid;
  gap: 16px;
  padding: clamp(18px, 2vw, 24px);
  border-radius: var(--r-xl);
  box-shadow: var(--shadow-2);
}

.reg.is-open {
  border-color: color-mix(in srgb, var(--bm-blue) 40%, var(--c-line));
}

.reg__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.reg__window {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: 0;
  color: var(--c-text-2);
  font-size: 13px;
}

.reg__window svg {
  color: var(--c-text-3);
}

.reg__clock {
  display: grid;
  gap: 8px;
  padding: 14px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-lg);
  background: var(--c-sunken);
}

.reg__clock-label {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.reg__clock :deep(.countdown) {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.reg__clock :deep(.countdown__tile) {
  min-width: 0;
}

.reg__notice {
  --tone: var(--c-text-3);
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 12px;
  padding: 14px;
  border: 1px solid color-mix(in srgb, var(--tone) 34%, transparent);
  border-radius: var(--r-lg);
  background: color-mix(in srgb, var(--tone) 10%, transparent);
  animation: reg-in 520ms var(--ease-out) both;
}

.reg__notice.is-green {
  --tone: var(--bm-green);
}

.reg__notice.is-amber {
  --tone: var(--bm-amber);
}

.reg__notice.is-red {
  --tone: var(--bm-red);
}

.reg__notice.is-blue {
  --tone: var(--bm-blue-bright);
}

.reg__notice-icon {
  margin-top: 1px;
  color: color-mix(in srgb, var(--tone) 85%, var(--c-text));
}

.reg__notice strong {
  display: block;
  color: var(--c-text);
  font-size: 14.5px;
  font-weight: 650;
  line-height: 1.35;
}

.reg__notice p {
  margin: 4px 0 0;
  color: var(--c-text-2);
  font-size: 13px;
  line-height: 1.45;
}

.reg__form {
  display: grid;
  gap: 14px;
}

.reg__form--car {
  padding-top: 16px;
  border-top: 1px solid var(--c-line);
}

.reg__number {
  max-width: 140px;
  font-size: 20px;
  letter-spacing: 0.3em;
}

.reg__note {
  margin: 0;
  color: var(--c-text-3);
  font-size: 12.5px;
  line-height: 1.45;
  text-align: center;
}

@keyframes reg-in {
  from {
    opacity: 0;
    transform: translateY(6px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .reg__notice {
    animation: none;
  }
}
</style>
