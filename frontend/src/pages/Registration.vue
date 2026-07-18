<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const router = useRouter()
const error = ref('')
const form = ref({
  login: '',
  email: '',
  password: '',
  password_confirm: '',
  first_name: '',
  last_name: '',
  nickname: '',
  pilot_number: 0,
  steam_id: '',
  country: '',
  discord: '',
  avatar_color: '#2563eb'
})

async function submit() {
  error.value = ''
  try {
    await api('/auth/register', { method: 'POST', body: form.value })
    router.push('/login')
  } catch (err) {
    error.value = err.message
  }
}
</script>

<template>
  <section class="section card">
    <h1>Registration</h1>
    <form class="form" @submit.prevent="submit">
      <div class="form-row">
        <label class="field"><span>Login</span><input v-model="form.login" required /></label>
        <label class="field"><span>Email</span><input v-model="form.email" type="email" required /></label>
      </div>
      <div class="form-row">
        <label class="field"><span>Password</span><input v-model="form.password" type="password" required minlength="8" /></label>
        <label class="field"><span>Confirm</span><input v-model="form.password_confirm" type="password" required minlength="8" /></label>
      </div>
      <div class="form-row">
        <label class="field"><span>First name</span><input v-model="form.first_name" required /></label>
        <label class="field"><span>Last name</span><input v-model="form.last_name" required /></label>
      </div>
      <div class="form-row">
        <label class="field"><span>Nickname</span><input v-model="form.nickname" required /></label>
        <label class="field"><span>Pilot number</span><input v-model.number="form.pilot_number" type="number" min="1" required /></label>
      </div>
      <div class="form-row">
        <label class="field"><span>Steam ID</span><input v-model="form.steam_id" required /></label>
        <label class="field"><span>Country</span><input v-model="form.country" /></label>
      </div>
      <div class="form-row">
        <label class="field"><span>Discord</span><input v-model="form.discord" /></label>
        <label class="field"><span>Avatar color</span><input v-model="form.avatar_color" type="color" /></label>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="button primary" type="submit">Create account</button>
    </form>
  </section>
</template>

