<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { AtSign, Eye, EyeOff, KeyRound, LoaderCircle, LogIn } from 'lucide-vue-next'
import { api, API_BASE } from '../api'
import { friendlyAuthError } from '../authErrors'
import { setSession, state } from '../store'
import FormField from '../ui/FormField.vue'
import FloatingNumbers from '../ui/fx/FloatingNumbers.vue'
import StartLights from '../ui/fx/StartLights.vue'
import AuthLayout from './auth/AuthLayout.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const form = ref({ login: '', password: '' })
const error = ref(route.query.steam_error ? friendlyAuthError(t, route.query.steam_error).text : '')
const submitting = ref(false)
const showPassword = ref(false)
const justRegistered = computed(() => route.query.registered === '1')

async function submit() {
  error.value = ''
  submitting.value = true
  try {
    const data = await api('/auth/login', { method: 'POST', body: form.value })
    setSession(data.access_token, data.user)
    // The app may have been opened anonymously before login. Associate the
    // now-authenticated account with the already-issued browser marker.
    api('/auth/device').catch(() => {})
    router.push('/')
  } catch (err) {
    error.value = friendlyAuthError(t, err.message).text
  } finally {
    submitting.value = false
  }
}

function loginWithSteam() {
  window.location.href = `${API_BASE}/auth/steam/start?flow=login`
}

onMounted(async () => {
  const token = Array.isArray(route.query.token) ? route.query.token[0] : route.query.token
  if (!token) return
  try {
    state.token = token
    localStorage.setItem('token', token)
    const user = await api('/auth/me')
    setSession(token, user)
    api('/auth/device').catch(() => {})
    router.replace('/')
  } catch (err) {
    error.value = friendlyAuthError(t, err.message).text
  }
})
</script>

<template>
  <AuthLayout>
    <header class="login__head">
      <p class="ui-eyebrow ui-eyebrow--accent">{{ t('authPage.login.eyebrow') }}</p>
      <h1 v-split class="ui-display login__title">{{ t('authPage.login.title') }}</h1>
      <p class="login__lead">{{ t('authPage.login.lead') }}</p>
    </header>

    <p v-if="justRegistered" class="ui-alert ui-alert--success" role="status">{{ t('authPage.login.registered') }}</p>

    <form class="ui-form" @submit.prevent="submit">
      <FormField v-slot="{ id, describedBy }" :label="t('authPage.login.loginLabel')" :hint="t('authPage.login.loginHint')" :icon="AtSign">
        <input :id="id" v-model="form.login" class="ui-input" autocomplete="username" required :aria-describedby="describedBy" />
      </FormField>
      <FormField v-slot="{ id }" :label="t('authPage.login.passwordLabel')" :icon="KeyRound">
        <div class="login__password">
          <input :id="id" v-model="form.password" class="ui-input" :type="showPassword ? 'text' : 'password'" autocomplete="current-password" required />
          <button class="login__eye" type="button" :aria-label="showPassword ? t('authPage.login.hide') : t('authPage.login.show')" @click="showPassword = !showPassword">
            <EyeOff v-if="showPassword" :size="18" />
            <Eye v-else :size="18" />
          </button>
        </div>
      </FormField>

      <Transition name="ui-fade">
        <p v-if="error" class="ui-alert" role="alert">{{ error }}</p>
      </Transition>

      <button v-magnet="4" class="ui-btn ui-btn--primary ui-btn--lg ui-btn--block" type="submit" :disabled="submitting">
        <LoaderCircle v-if="submitting" class="login__spin" :size="18" />
        <LogIn v-else :size="18" />
        {{ submitting ? t('authPage.login.submitting') : t('authPage.login.submit') }}
      </button>
    </form>

    <div class="login__or"><span>{{ t('authPage.login.or') }}</span></div>

    <div class="login__steam">
      <button class="ui-btn ui-btn--outline ui-btn--lg ui-btn--block login__steam-btn" type="button" @click="loginWithSteam">
        <svg class="login__steam-logo" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M11.98 0C5.7 0 .55 4.84.06 11l6.43 2.66a3.38 3.38 0 0 1 1.92-.6h.19l2.86-4.15v-.06a4.52 4.52 0 1 1 4.52 4.52h-.1l-4.08 2.91v.16a3.4 3.4 0 0 1-6.73.67L.48 15.56A12 12 0 1 0 11.98 0Zm-4.5 18.2-1.47-.61a2.55 2.55 0 1 0 1.4-3.47l1.52.63a1.88 1.88 0 1 1-1.45 3.46Zm11.4-9.3a3.01 3.01 0 1 0-3.02 3 3.01 3.01 0 0 0 3.02-3Zm-5.27 0a2.26 2.26 0 1 1 2.26 2.26 2.26 2.26 0 0 1-2.26-2.26Z" /></svg>
        {{ t('authPage.login.steam') }}
      </button>
      <small>{{ t('authPage.login.steamHint') }}</small>
    </div>

    <p class="login__switch">
      {{ t('authPage.login.noAccount') }}
      <RouterLink class="ui-link" to="/register">{{ t('authPage.login.register') }}</RouterLink>
    </p>

    <template #backdrop>
      <FloatingNumbers class="login__numbers" />
    </template>

    <template #aside>
      <div class="login__aside">
        <StartLights size="lg" double :lit="5" :label="t('authPage.login.asideTitle')" />
        <h2 class="ui-display login__aside-title">{{ t('authPage.login.asideTitle') }}</h2>
        <p>{{ t('authPage.login.asideText') }}</p>
      </div>
    </template>
  </AuthLayout>
</template>

<style scoped>
.login__head {
  display: grid;
  gap: 10px;
  container-type: inline-size;
}

/* Sized by the column, not the viewport: "ВОЗВРАЩЕНИЕМ" (~11.5em) must fit on one line. */
.login__title {
  font-size: clamp(22px, 8.2cqi, 44px);
}

.login__lead {
  margin: 0;
  color: var(--c-text-2);
}

.login__password {
  position: relative;
  display: grid;
}

.login__password .ui-input {
  padding-right: 48px;
}

.login__eye {
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

.login__eye:hover {
  background: var(--c-blue-soft);
  color: var(--c-text);
}

.login__spin {
  animation: login-spin 900ms linear infinite;
}

@keyframes login-spin {
  to {
    transform: rotate(360deg);
  }
}

.login__or {
  display: flex;
  align-items: center;
  gap: 14px;
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.login__or::before,
.login__or::after {
  flex: 1 1 auto;
  height: 1px;
  background: var(--c-line-strong);
  content: '';
}

.login__steam {
  display: grid;
  gap: 8px;
}

.login__steam small {
  color: var(--c-text-3);
  font-size: 12.5px;
  text-align: center;
}

.login__steam-btn {
  --btn-bg: linear-gradient(135deg, #171a21, #1b2838);
}

.login__steam-logo {
  width: 20px;
  height: 20px;
}

.login__switch {
  margin: 0;
  color: var(--c-text-2);
  font-size: 14px;
  text-align: center;
}

/* The numbers thin out behind the lights and headline so the text stays crisp. */
.login__numbers {
  -webkit-mask-image: radial-gradient(ellipse 58% 24% at 38% 52%, rgba(0, 0, 0, 0.18) 35%, #000 100%);
  mask-image: radial-gradient(ellipse 58% 24% at 38% 52%, rgba(0, 0, 0, 0.18) 35%, #000 100%);
}

.login__aside {
  display: grid;
  justify-items: start;
  gap: 18px;
  max-width: 440px;
}

.login__aside-title {
  color: var(--c-text);
  line-height: 1.18;
  font-size: clamp(28px, 3.4vw, 46px);
}

.login__aside p {
  margin: 0;
  color: var(--c-text-2);
  font-size: 16px;
  line-height: 1.55;
}
</style>
