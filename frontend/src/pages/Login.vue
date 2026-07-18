<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { api, API_BASE } from '../api'
import { setSession, state } from '../store'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const form = ref({ login: '', password: '' })
const error = ref(route.query.steam_error || '')

async function submit() {
  error.value = ''
  try {
    const data = await api('/auth/login', { method: 'POST', body: form.value })
    setSession(data.access_token, data.user)
    router.push('/')
  } catch (err) {
    error.value = err.message
  }
}

function loginWithSteam() {
  window.location.href = `${API_BASE}/auth/steam/start`
}

onMounted(async () => {
  const token = Array.isArray(route.query.token) ? route.query.token[0] : route.query.token
  if (!token) return
  try {
    state.token = token
    localStorage.setItem('token', token)
    const user = await api('/auth/me')
    setSession(token, user)
    router.replace('/')
  } catch (err) {
    error.value = err.message
  }
})
</script>

<template>
  <section class="section card">
    <div class="section-header">
      <h1>{{ t('nav.login') }}</h1>
      <RouterLink to="/register">{{ t('auth.register') }}</RouterLink>
    </div>
    <form class="form" @submit.prevent="submit">
      <label class="field"><span>{{ t('auth.login') }}</span><input v-model="form.login" autocomplete="username" required /></label>
      <label class="field"><span>{{ t('auth.password') }}</span><input v-model="form.password" type="password" autocomplete="current-password" required /></label>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="button primary" type="submit">{{ t('auth.submit') }}</button>
      <button class="button" type="button" @click="loginWithSteam">Steam</button>
    </form>
  </section>
</template>
