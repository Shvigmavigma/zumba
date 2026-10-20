<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ArrowLeft, ArrowRight, AtSign, BadgeCheck, Eye, EyeOff, Hash, KeyRound, LoaderCircle, Mail, MessageCircle, ShieldCheck, UserRound } from 'lucide-vue-next'
import { api, API_BASE } from '../api'
import { friendlyAuthError } from '../authErrors'
import CountryCombobox from '../components/CountryCombobox.vue'
import GameCheckboxGroup from '../components/GameCheckboxGroup.vue'
import { countryOptionsWithCurrent } from '../countries'
import { registrationDraft } from '../registrationDraft'
import { state } from '../store'
import FormField from '../ui/FormField.vue'
import { prefersReducedMotion } from '../ui/motion/env'
import AuthLayout from './auth/AuthLayout.vue'
import LicensePreview from './auth/LicensePreview.vue'
import WizardSteps from './auth/WizardSteps.vue'

const { t, tm } = useI18n()
const route = useRoute()
const router = useRouter()

// The browser draft survives the Steam redirect; registrationDraft() keeps the
// passwords and the single-use Steam token out of it.
const DRAFT_KEY = 'registrationDraft'
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/
const STEP_KEYS = ['steam', 'account', 'pilot', 'extra']

const formEl = ref(null)
const stepsRef = ref(null)
const error = ref('')
const submitting = ref(false)
const step = ref(0)
const direction = ref('forward')
const showPassword = ref(false)
const attempted = ref(new Set())
const touched = ref(new Set())
const visited = ref(new Set(['steam']))
const form = ref({
  login: '',
  email: '',
  password: '',
  password_confirm: '',
  first_name: '',
  last_name: '',
  nickname: '',
  pilot_number: '',
  steam_auth_token: '',
  country: '',
  discord: '',
  avatar_color: '#2563eb',
  games: ['ACC'],
  terms_accepted: false,
  data_processing_consent: false
})

const steamConnected = computed(() => Boolean(form.value.steam_auth_token))
const countries = computed(() => countryOptionsWithCurrent(state.locale, form.value.country))

const fieldErrors = computed(() => {
  const f = form.value
  const login = f.login.trim()
  return {
    steam: steamConnected.value ? '' : t('authPage.register.errors.steam'),
    login: !login ? t('authPage.register.errors.required') : login.length < 3 || login.length > 50 ? t('authPage.register.errors.loginLength') : '',
    email: !f.email.trim() ? t('authPage.register.errors.required') : EMAIL_RE.test(f.email.trim()) ? '' : t('authPage.register.errors.email'),
    password: !f.password ? t('authPage.register.errors.required') : f.password.length < 8 ? t('authPage.register.errors.passwordLength') : '',
    password_confirm: !f.password_confirm ? t('authPage.register.errors.required') : f.password_confirm !== f.password ? t('authPage.register.errors.passwordMatch') : '',
    first_name: f.first_name.trim() ? '' : t('authPage.register.errors.required'),
    last_name: f.last_name.trim() ? '' : t('authPage.register.errors.required'),
    nickname: f.nickname.trim() ? '' : t('authPage.register.errors.required'),
    pilot_number: /^\d{3}$/.test(String(f.pilot_number)) ? '' : t('authPage.register.errors.number'),
    games: f.games?.length ? '' : t('authPage.register.errors.games'),
    terms_accepted: f.terms_accepted ? '' : t('authPage.register.errors.terms'),
    data_processing_consent: f.data_processing_consent ? '' : t('authPage.register.errors.consent')
  }
})

const CONSENTS = [
  { field: 'terms_accepted', key: 'terms', to: '/terms' },
  { field: 'data_processing_consent', key: 'privacy', to: '/privacy-policy' }
]

const STEP_FIELDS = {
  steam: ['steam'],
  account: ['login', 'email', 'password', 'password_confirm'],
  pilot: ['first_name', 'last_name', 'nickname', 'pilot_number'],
  extra: ['games', 'terms_accepted', 'data_processing_consent']
}

function stepValid(key) {
  return STEP_FIELDS[key].every((field) => !fieldErrors.value[field])
}

const steps = computed(() => STEP_KEYS.map((key) => ({
  key,
  title: t(`authPage.register.steps.${key}.title`),
  text: t(`authPage.register.steps.${key}.text`),
  // A step counts as done only once the pilot has been there and it is valid.
  done: visited.value.has(key) && stepValid(key)
})))
const currentKey = computed(() => STEP_KEYS[step.value])
const isLast = computed(() => step.value === STEP_KEYS.length - 1)

/** Show a field's error once it was left or its step was submitted. */
function errorFor(field) {
  const visible = touched.value.has(field) || attempted.value.has(currentKey.value)
  return visible ? fieldErrors.value[field] : ''
}

function touch(field) {
  touched.value = new Set([...touched.value, field])
}

/** "7" means car #007, exactly as the licence preview already shows it. */
function padPilotNumber() {
  const value = String(form.value.pilot_number)
  if (/^\d{1,2}$/.test(value)) form.value.pilot_number = value.padStart(3, '0')
  touch('pilot_number')
}

const passwordScore = computed(() => {
  const value = form.value.password
  if (!value) return -1
  const classes = [/[a-zа-я]/, /[A-ZА-Я]/, /\d/, /[^\p{L}\d]/u].filter((re) => re.test(value)).length
  if (value.length < 8 || classes < 2) return 0
  return value.length >= 10 && classes >= 3 ? 2 : 1
})
const strengthLabels = computed(() => tm('authPage.register.account.strength'))

function saveDraft() {
  sessionStorage.setItem(DRAFT_KEY, JSON.stringify(registrationDraft(form.value)))
}

function goTo(index) {
  if (index === step.value || index < 0 || index >= STEP_KEYS.length) return
  direction.value = index > step.value ? 'forward' : 'back'
  step.value = index
  visited.value = new Set([...visited.value, STEP_KEYS[index]])
  error.value = ''
  revealSteps()
}

/** A pilot scrolled down to the Next button must still see the new step from its start. */
function revealSteps() {
  const el = stepsRef.value?.$el
  if (!el) return
  const headerHeight = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--header-h')) || 76
  if (el.getBoundingClientRect().top < headerHeight) {
    el.scrollIntoView({ block: 'start', behavior: prefersReducedMotion() ? 'auto' : 'smooth' })
  }
}

/** Focuses the first field that needs fixing, otherwise the first field of the step. */
function focusStep(el) {
  const target = el.querySelector('[aria-invalid="true"]') || el.querySelector('input, button')
  target?.focus({ preventScroll: true })
}

async function focusFirstInvalid() {
  await nextTick()
  formEl.value?.querySelector('[aria-invalid="true"]')?.focus()
}

function next() {
  attempted.value = new Set([...attempted.value, currentKey.value])
  if (!stepValid(currentKey.value)) {
    focusFirstInvalid()
    return
  }
  goTo(step.value + 1)
}

function connectSteam() {
  form.value.steam_auth_token = ''
  saveDraft()
  window.location.href = `${API_BASE}/auth/steam/start?flow=register`
}

async function submit() {
  attempted.value = new Set(STEP_KEYS)
  const firstInvalid = STEP_KEYS.findIndex((key) => !stepValid(key))
  if (firstInvalid >= 0) {
    goTo(firstInvalid)
    return
  }
  error.value = ''
  submitting.value = true
  try {
    await api('/auth/register', {
      method: 'POST',
      body: {
        ...form.value,
        login: form.value.login.trim(),
        email: form.value.email.trim(),
        country: form.value.country || null,
        discord: form.value.discord || null
      }
    })
    sessionStorage.removeItem(DRAFT_KEY)
    router.push({ path: '/login', query: { registered: '1' } })
  } catch (err) {
    const friendly = friendlyAuthError(t, err.message)
    error.value = friendly.text
    if (friendly.resetSteam) {
      // The Steam confirmation is single-use: ask for a fresh one.
      form.value.steam_auth_token = ''
      saveDraft()
      goTo(0)
    }
  } finally {
    submitting.value = false
  }
}

function onSubmit() {
  if (isLast.value) submit()
  else next()
}

watch(form, saveDraft, { deep: true })

onMounted(() => {
  // Remove the legacy raw Steam ID cache. Registration now uses an opaque
  // server-side token and never needs to keep the identifier in the browser.
  sessionStorage.removeItem('registrationSteamId')
  const draft = sessionStorage.getItem(DRAFT_KEY)
  if (draft) {
    try {
      form.value = { ...form.value, ...registrationDraft(JSON.parse(draft)) }
    } catch {
      sessionStorage.removeItem(DRAFT_KEY)
    }
  }
  if (route.query.steam_error) {
    const raw = Array.isArray(route.query.steam_error) ? route.query.steam_error[0] : route.query.steam_error
    error.value = friendlyAuthError(t, raw).text
  }

  const token = Array.isArray(route.query.steam_auth_token) ? route.query.steam_auth_token[0] : route.query.steam_auth_token
  if (token) {
    form.value.steam_auth_token = token
    router.replace('/register')
  }
  // Continue where the pilot left off: the first step that still needs input.
  if (steamConnected.value) {
    const pending = STEP_KEYS.findIndex((key) => !stepValid(key))
    step.value = pending >= 0 ? pending : STEP_KEYS.length - 1
    visited.value = new Set(STEP_KEYS.slice(0, step.value + 1))
  }
})
</script>

<template>
  <AuthLayout>
    <header class="reg__head">
      <p class="ui-eyebrow ui-eyebrow--accent">{{ t('authPage.register.eyebrow') }}</p>
      <h1 v-split class="ui-display reg__title">{{ t('authPage.register.title') }}</h1>
      <p class="reg__lead">{{ t('authPage.register.lead') }}</p>
    </header>

    <WizardSteps ref="stepsRef" :steps="steps" :current="step" @select="goTo" />

    <form ref="formEl" class="reg__form" novalidate @submit.prevent="onSubmit">
      <Transition :name="`reg-${direction}`" mode="out-in" @after-enter="focusStep">
        <!-- 1. Steam -->
        <section v-if="currentKey === 'steam'" key="steam" class="reg__step">
          <div class="reg__step-head">
            <h2>{{ t('authPage.register.steam.title') }}</h2>
            <p>{{ t('authPage.register.steam.text') }}</p>
          </div>
          <div class="reg__steam" :class="{ 'is-ok': steamConnected }">
            <span class="reg__steam-icon">
              <BadgeCheck v-if="steamConnected" :size="26" />
              <ShieldCheck v-else :size="26" />
            </span>
            <div class="reg__steam-text">
              <strong>{{ steamConnected ? t('authPage.register.steam.connected') : t('authPage.register.steam.missing') }}</strong>
              <span>{{ steamConnected ? t('authPage.register.steam.connectedHint') : t('authPage.register.steam.rule') }}</span>
            </div>
            <button class="ui-btn" :class="steamConnected ? 'ui-btn--outline' : 'ui-btn--primary'" type="button" @click="connectSteam">
              {{ steamConnected ? t('authPage.register.steam.reconnect') : t('authPage.register.steam.connect') }}
            </button>
          </div>
          <p v-if="attempted.has('steam') && !steamConnected" class="ui-alert" role="alert">{{ t('authPage.register.errors.steam') }}</p>
        </section>

        <!-- 2. Account -->
        <section v-else-if="currentKey === 'account'" key="account" class="reg__step">
          <div class="reg__step-head">
            <h2>{{ t('authPage.register.account.title') }}</h2>
            <p>{{ t('authPage.register.account.text') }}</p>
          </div>
          <div class="ui-form-row">
            <FormField v-slot="{ id, describedBy, invalid }" :label="t('fields.login')" :hint="t('authPage.register.account.loginHint')" :error="errorFor('login')" :icon="AtSign" required :count="form.login.length" :max="50">
              <input :id="id" v-model="form.login" class="ui-input" autocomplete="username" maxlength="50" :aria-describedby="describedBy" :aria-invalid="invalid" @blur="touch('login')" />
            </FormField>
            <FormField v-slot="{ id, describedBy, invalid }" :label="t('fields.email')" :hint="t('authPage.register.account.emailHint')" :error="errorFor('email')" :success="touched.has('email') && !fieldErrors.email ? t('authPage.register.ok.email') : ''" :icon="Mail" required>
              <input :id="id" v-model="form.email" class="ui-input" type="email" autocomplete="email" maxlength="255" :aria-describedby="describedBy" :aria-invalid="invalid" @blur="touch('email')" />
            </FormField>
          </div>
          <div class="ui-form-row">
            <FormField v-slot="{ id, describedBy, invalid }" :label="t('fields.password')" :hint="t('authPage.register.account.passwordHint')" :error="errorFor('password')" :icon="KeyRound" required>
              <div class="reg__password">
                <input :id="id" v-model="form.password" class="ui-input" :type="showPassword ? 'text' : 'password'" autocomplete="new-password" maxlength="128" :aria-describedby="describedBy" :aria-invalid="invalid" @blur="touch('password')" />
                <button class="reg__eye" type="button" :aria-label="showPassword ? t('authPage.login.hide') : t('authPage.login.show')" @click="showPassword = !showPassword">
                  <EyeOff v-if="showPassword" :size="18" />
                  <Eye v-else :size="18" />
                </button>
              </div>
              <span v-if="passwordScore >= 0" class="reg__strength" :class="`is-${passwordScore}`">
                <span class="reg__strength-bars"><i></i><i></i><i></i></span>
                {{ strengthLabels[passwordScore] }}
              </span>
            </FormField>
            <FormField v-slot="{ id, describedBy, invalid }" :label="t('fields.confirm')" :hint="t('authPage.register.account.confirmHint')" :error="errorFor('password_confirm')" :success="form.password_confirm && !fieldErrors.password_confirm ? t('authPage.register.ok.passwordMatch') : ''" :icon="KeyRound" required>
              <input :id="id" v-model="form.password_confirm" class="ui-input" :type="showPassword ? 'text' : 'password'" autocomplete="new-password" maxlength="128" :aria-describedby="describedBy" :aria-invalid="invalid" @blur="touch('password_confirm')" />
            </FormField>
          </div>
        </section>

        <!-- 3. Pilot -->
        <section v-else-if="currentKey === 'pilot'" key="pilot" class="reg__step">
          <div class="reg__step-head">
            <h2>{{ t('authPage.register.pilot.title') }}</h2>
            <p>{{ t('authPage.register.pilot.text') }}</p>
          </div>
          <div class="ui-form-row">
            <FormField v-slot="{ id, describedBy, invalid }" :label="t('fields.firstName')" :hint="t('authPage.register.pilot.firstNameHint')" :error="errorFor('first_name')" :icon="UserRound" required>
              <input :id="id" v-model="form.first_name" class="ui-input" autocomplete="given-name" maxlength="50" :aria-describedby="describedBy" :aria-invalid="invalid" @blur="touch('first_name')" />
            </FormField>
            <FormField v-slot="{ id, describedBy, invalid }" :label="t('fields.lastName')" :hint="t('authPage.register.pilot.lastNameHint')" :error="errorFor('last_name')" :icon="UserRound" required>
              <input :id="id" v-model="form.last_name" class="ui-input" autocomplete="family-name" maxlength="50" :aria-describedby="describedBy" :aria-invalid="invalid" @blur="touch('last_name')" />
            </FormField>
          </div>
          <div class="ui-form-row">
            <FormField v-slot="{ id, describedBy, invalid }" :label="t('fields.nickname')" :hint="t('authPage.register.pilot.nicknameHint')" :error="errorFor('nickname')" :icon="AtSign" required :count="form.nickname.length" :max="80">
              <input :id="id" v-model="form.nickname" class="ui-input" maxlength="80" :aria-describedby="describedBy" :aria-invalid="invalid" @blur="touch('nickname')" />
            </FormField>
            <FormField v-slot="{ id, describedBy, invalid }" :label="t('fields.pilotNumber')" :hint="t('authPage.register.pilot.numberHint')" :error="errorFor('pilot_number')" :icon="Hash" required>
              <input :id="id" v-model="form.pilot_number" class="ui-input reg__number" inputmode="numeric" maxlength="3" placeholder="000" :aria-describedby="describedBy" :aria-invalid="invalid" @input="form.pilot_number = form.pilot_number.replace(/\D/g, '')" @blur="padPilotNumber" />
            </FormField>
          </div>
        </section>

        <!-- 4. Simulators & contact -->
        <section v-else key="extra" class="reg__step">
          <div class="reg__step-head">
            <h2>{{ t('authPage.register.extra.title') }}</h2>
            <p>{{ t('authPage.register.extra.text') }}</p>
          </div>
          <FormField v-slot="{ describedBy }" :label="t('fields.games')" :hint="t('authPage.register.extra.gamesHint')" :error="errorFor('games')" required>
            <GameCheckboxGroup v-model="form.games" :aria-describedby="describedBy" />
          </FormField>
          <div class="ui-form-row">
            <FormField v-slot="{ id, describedBy }" :label="t('fields.country')" :hint="t('authPage.register.extra.countryHint')" :optional-label="t('authPage.register.optional')">
              <CountryCombobox v-model="form.country" :options="countries" :trigger-id="id" :described-by="describedBy" />
            </FormField>
            <FormField v-slot="{ id, describedBy }" :label="t('fields.discord')" :hint="t('authPage.register.extra.discordHint')" :optional-label="t('authPage.register.optional')" :icon="MessageCircle">
              <input :id="id" v-model="form.discord" class="ui-input" maxlength="100" placeholder="nickname" :aria-describedby="describedBy" />
            </FormField>
          </div>
          <!-- The documents open in a new tab: leaving the page would drop the Steam confirmation. -->
          <fieldset class="reg__consents">
            <legend class="ui-sr">{{ t('authPage.register.consents.legend') }}</legend>
            <div v-for="consent in CONSENTS" :key="consent.field" class="reg__consent" :class="{ 'is-invalid': errorFor(consent.field) }">
              <label class="ui-check">
                <input v-model="form[consent.field]" type="checkbox" required :aria-invalid="Boolean(errorFor(consent.field))" :aria-describedby="errorFor(consent.field) ? `reg-${consent.field}-error` : undefined" @change="touch(consent.field)" />
                <span>
                  {{ t(`authPage.register.consents.${consent.key}.before`) }}
                  <RouterLink class="reg__consent-link" :to="consent.to" target="_blank" rel="noopener">{{ t(`authPage.register.consents.${consent.key}.link`) }}</RouterLink>{{ t(`authPage.register.consents.${consent.key}.after`) }}
                </span>
              </label>
              <p v-if="errorFor(consent.field)" :id="`reg-${consent.field}-error`" class="reg__consent-error" role="alert">{{ errorFor(consent.field) }}</p>
            </div>
          </fieldset>
        </section>
      </Transition>

      <p v-if="error" class="ui-alert" role="alert">{{ error }}</p>

      <footer class="reg__nav">
        <button v-if="step > 0" class="ui-btn ui-btn--ghost" type="button" @click="goTo(step - 1)"><ArrowLeft :size="17" />{{ t('authPage.register.back') }}</button>
        <span class="reg__progress ui-mono">{{ t('authPage.register.stepOf', { current: step + 1, total: STEP_KEYS.length }) }}</span>
        <button v-if="!isLast" class="ui-btn ui-btn--primary" type="submit" :disabled="currentKey === 'steam' && !steamConnected">
          {{ t('authPage.register.next') }}<ArrowRight :size="17" />
        </button>
        <button v-else v-spark class="ui-btn ui-btn--primary" type="submit" :disabled="submitting || !steamConnected">
          <LoaderCircle v-if="submitting" class="reg__spin" :size="17" />
          {{ submitting ? t('authPage.register.submitting') : t('authPage.register.submit') }}
        </button>
      </footer>
    </form>

    <p class="reg__switch">
      {{ t('authPage.register.haveAccount') }}
      <RouterLink class="ui-link" to="/login">{{ t('authPage.register.loginLink') }}</RouterLink>
    </p>

    <template #aside>
      <LicensePreview :form="form" :steam-connected="steamConnected" />
      <div class="reg__after">
        <p class="ui-eyebrow">{{ t('authPage.register.after.title') }}</p>
        <ol>
          <li v-for="(item, index) in tm('authPage.register.after.items')" :key="index">
            <span class="ui-num">{{ index + 1 }}</span>{{ item }}
          </li>
        </ol>
      </div>
    </template>
  </AuthLayout>
</template>

<style scoped>
.reg__head {
  display: grid;
  gap: 10px;
}

.reg__title {
  font-size: clamp(30px, 4vw, 48px);
}

.reg__lead {
  margin: 0;
  color: var(--c-text-2);
}

.reg__form {
  display: grid;
  gap: 20px;
}

.reg__step {
  display: grid;
  gap: 18px;
}

.reg__step-head {
  display: grid;
  gap: 6px;
}

.reg__step-head h2 {
  margin: 0;
  font-size: 18px;
}

.reg__step-head p {
  margin: 0;
  color: var(--c-text-2);
  font-size: 14px;
  line-height: 1.55;
}

.reg__consents {
  display: grid;
  gap: 10px;
  min-width: 0;
  margin: 0;
  padding: 14px 16px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  background: var(--c-sunken);
}

.reg__consent {
  display: grid;
  gap: 4px;
}

.reg__consent .ui-check {
  align-items: flex-start;
  line-height: 1.45;
}

.reg__consent .ui-check input {
  flex: none;
  margin-top: 1px;
}

.reg__consent-link {
  color: var(--c-accent-text);
  font-weight: 600;
  text-underline-offset: 3px;
}

.reg__consent-error {
  margin: 0 0 0 30px;
  color: var(--bm-red);
  font-size: 12.5px;
}

.reg__steam {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 16px;
  padding: 18px;
  border: 1px dashed var(--c-line-strong);
  border-radius: var(--r-lg);
  background: var(--c-sunken);
  transition: border-color var(--dur-3), background-color var(--dur-3);
}

.reg__steam.is-ok {
  border-style: solid;
  border-color: color-mix(in srgb, var(--bm-green) 45%, transparent);
  background: color-mix(in srgb, var(--bm-green) 8%, var(--c-sunken));
}

.reg__steam-icon {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  border-radius: 16px;
  background: linear-gradient(135deg, #1b2838, #2a475e);
  color: #c7d5e0;
}

.reg__steam.is-ok .reg__steam-icon {
  background: color-mix(in srgb, var(--bm-green) 22%, transparent);
  color: var(--bm-green);
}

.reg__steam-text {
  display: grid;
  gap: 4px;
}

.reg__steam-text span {
  color: var(--c-text-2);
  font-size: 13px;
}

.reg__password {
  position: relative;
  display: grid;
}

.reg__password .ui-input {
  padding-right: 48px;
}

.reg__eye {
  position: absolute;
  top: 50%;
  right: 6px;
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--c-text-3);
  cursor: pointer;
  transform: translateY(-50%);
}

.reg__eye:hover {
  background: var(--c-blue-soft);
  color: var(--c-text);
}

.reg__strength {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
  color: var(--c-text-2);
  font-size: 12.5px;
}

.reg__strength-bars {
  display: inline-grid;
  grid-template-columns: repeat(3, 26px);
  gap: 4px;
}

.reg__strength-bars i {
  height: 4px;
  border-radius: 4px;
  background: color-mix(in srgb, var(--c-text) 14%, transparent);
  transition: background-color var(--dur-3);
}

.reg__strength.is-0 .reg__strength-bars i:nth-child(-n + 1) {
  background: var(--bm-red);
}

.reg__strength.is-1 .reg__strength-bars i:nth-child(-n + 2) {
  background: var(--bm-amber);
}

.reg__strength.is-2 .reg__strength-bars i {
  background: var(--bm-green);
}

.reg__number {
  font-family: var(--font-mono);
  font-size: 18px;
  letter-spacing: 0.3em;
}

.reg__nav {
  display: flex;
  align-items: center;
  gap: 12px;
}

.reg__progress {
  margin-left: auto;
  color: var(--c-text-3);
  font-size: 12px;
}

.reg__nav .ui-btn--primary {
  min-width: 170px;
}

.reg__spin {
  animation: reg-spin 900ms linear infinite;
}

@keyframes reg-spin {
  to {
    transform: rotate(360deg);
  }
}

.reg__switch {
  margin: 0;
  color: var(--c-text-2);
  font-size: 14px;
}

.reg__after {
  display: grid;
  gap: 12px;
  max-width: 460px;
}

.reg__after ol {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.reg__after li {
  display: flex;
  gap: 12px;
  color: var(--c-text-2);
  font-size: 14px;
  line-height: 1.5;
}

.reg__after .ui-num {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  width: 24px;
  height: 24px;
  border: 1px solid var(--c-blue-line);
  border-radius: 50%;
  color: var(--c-accent-text);
  font-size: 11px;
}

/* Direction-aware step transitions. */
.reg-forward-enter-active,
.reg-forward-leave-active,
.reg-back-enter-active,
.reg-back-leave-active {
  transition: opacity 260ms var(--ease-out), transform 420ms var(--ease-ios), filter 260ms var(--ease-out);
}

.reg-forward-enter-from,
.reg-back-leave-to {
  opacity: 0;
  filter: blur(6px);
  transform: translateX(28px);
}

.reg-forward-leave-to,
.reg-back-enter-from {
  opacity: 0;
  filter: blur(6px);
  transform: translateX(-28px);
}

@media (max-width: 560px) {
  .reg__steam {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .reg__steam .ui-btn {
    grid-column: 1 / -1;
  }

  .reg__progress {
    display: none;
  }

  .reg__nav .ui-btn--primary {
    flex: 1 1 auto;
    min-width: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .reg-forward-enter-active,
  .reg-forward-leave-active,
  .reg-back-enter-active,
  .reg-back-leave-active {
    transition: none;
  }
}
</style>
