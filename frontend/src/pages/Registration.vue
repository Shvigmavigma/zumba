<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { api, API_BASE } from '../api'
import CountryCombobox from '../components/CountryCombobox.vue'
import GameCheckboxGroup from '../components/GameCheckboxGroup.vue'
import { countryOptionsWithCurrent } from '../countries'
import { state } from '../store'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const error = ref('')
const steamId = ref('')
const form = ref({
  login: '',
  email: '',
  password: '',
  password_confirm: '',
  first_name: '',
  last_name: '',
  nickname: '',
  pilot_number: 0,
  steam_auth_token: '',
  country: '',
  discord: '',
  avatar_color: '#2563eb',
  games: ['ACC']
})
const steamConnected = computed(() => Boolean(form.value.steam_auth_token && steamId.value))
const countries = computed(() => countryOptionsWithCurrent(state.locale, form.value.country))

function connectSteam() {
  sessionStorage.setItem('registrationDraft', JSON.stringify(form.value))
  window.location.href = `${API_BASE}/auth/steam/start?flow=register`
}

async function submit() {
  error.value = ''
  if (!steamConnected.value) {
    error.value = t('auth.steamAuthRequired')
    return
  }
  try {
    await api('/auth/register', {
      method: 'POST',
      body: {
        ...form.value,
        country: form.value.country || null,
        discord: form.value.discord || null
      }
    })
    sessionStorage.removeItem('registrationDraft')
    sessionStorage.removeItem('registrationSteamId')
    router.push('/login')
  } catch (err) {
    error.value = err.message
  }
}

onMounted(() => {
  const draft = sessionStorage.getItem('registrationDraft')
  if (draft) {
    try {
      form.value = { ...form.value, ...JSON.parse(draft) }
    } catch {
      sessionStorage.removeItem('registrationDraft')
    }
  }
  steamId.value = sessionStorage.getItem('registrationSteamId') || ''

  if (route.query.steam_error) {
    error.value = Array.isArray(route.query.steam_error) ? route.query.steam_error[0] : route.query.steam_error
  }

  const token = Array.isArray(route.query.steam_auth_token) ? route.query.steam_auth_token[0] : route.query.steam_auth_token
  const linkedSteamId = Array.isArray(route.query.steam_id) ? route.query.steam_id[0] : route.query.steam_id
  if (token && linkedSteamId) {
    form.value.steam_auth_token = token
    steamId.value = linkedSteamId
    sessionStorage.setItem('registrationDraft', JSON.stringify(form.value))
    sessionStorage.setItem('registrationSteamId', linkedSteamId)
    router.replace('/register')
  }
})
</script>

<template>
  <section class="section card">
    <div class="section-header">
      <h1>{{ t('auth.register') }}</h1>
      <RouterLink class="button small" to="/login">{{ t('nav.login') }}</RouterLink>
    </div>
    <form class="form" @submit.prevent="submit">
      <div class="form-row">
        <label class="field"><span>{{ t('fields.login') }}</span><input v-model="form.login" autocomplete="username" required minlength="3" maxlength="50" /></label>
        <label class="field"><span>{{ t('fields.email') }}</span><input v-model="form.email" type="email" autocomplete="email" required maxlength="255" /></label>
      </div>
      <div class="form-row">
        <label class="field"><span>{{ t('fields.password') }}</span><input v-model="form.password" type="password" autocomplete="new-password" required minlength="8" maxlength="128" /></label>
        <label class="field"><span>{{ t('fields.confirm') }}</span><input v-model="form.password_confirm" type="password" autocomplete="new-password" required minlength="8" maxlength="128" /></label>
      </div>
      <div class="form-row">
        <label class="field"><span>{{ t('fields.firstName') }}</span><input v-model="form.first_name" autocomplete="given-name" required minlength="1" maxlength="50" /></label>
        <label class="field"><span>{{ t('fields.lastName') }}</span><input v-model="form.last_name" autocomplete="family-name" required minlength="1" maxlength="50" /></label>
      </div>
      <div class="form-row">
        <label class="field"><span>{{ t('fields.nickname') }}</span><input v-model="form.nickname" required minlength="1" maxlength="80" /></label>
        <label class="field"><span>{{ t('fields.pilotNumber') }}</span><input v-model.number="form.pilot_number" type="number" min="1" max="9999" required /></label>
      </div>
      <section class="steam-connect">
        <div>
          <strong>{{ t('fields.steam') }}</strong>
          <p class="muted">{{ steamConnected ? t('auth.steamConnected', { id: steamId }) : t('auth.steamRequired') }}</p>
        </div>
        <button class="button" type="button" @click="connectSteam">{{ steamConnected ? t('auth.reconnectSteam') : t('auth.connectSteam') }}</button>
      </section>
      <div class="field">
        <span>{{ t('fields.country') }}</span>
        <CountryCombobox v-model="form.country" :options="countries" />
      </div>
      <div class="field">
        <span>{{ t('fields.games') }}</span>
        <GameCheckboxGroup v-model="form.games" />
      </div>
      <div class="form-row">
        <label class="field"><span>{{ t('fields.discord') }}</span><input v-model="form.discord" maxlength="100" /></label>
        <label class="field"><span>{{ t('fields.avatarColor') }}</span><input v-model="form.avatar_color" type="color" /></label>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="button primary" type="submit" :disabled="!steamConnected">{{ t('auth.createAccount') }}</button>
    </form>
  </section>
</template>
