<script setup>
import { ref } from 'vue'
import { api } from '../api'
import { setSession, state } from '../store'

const form = ref({ ...state.user })
const error = ref('')
const saved = ref(false)

async function submit() {
  error.value = ''
  saved.value = false
  try {
    const user = await api('/users/me', { method: 'PATCH', body: form.value })
    setSession(state.token, user)
    saved.value = true
  } catch (err) {
    error.value = err.message
  }
}
</script>

<template>
  <section class="section card">
    <h1>UserProfile</h1>
    <p v-if="state.user?.status === 'unapproved'" class="pill">Waiting for approval</p>
    <p v-if="state.user?.pending_profile_changes" class="pill">Profile changes are waiting for moderation</p>
    <form v-if="state.user" class="form" @submit.prevent="submit">
      <div class="form-row">
        <label class="field"><span>Email</span><input v-model="form.email" type="email" /></label>
        <label class="field"><span>Nickname</span><input v-model="form.nickname" /></label>
      </div>
      <div class="form-row">
        <label class="field"><span>First name</span><input v-model="form.first_name" /></label>
        <label class="field"><span>Last name</span><input v-model="form.last_name" /></label>
      </div>
      <div class="form-row">
        <label class="field"><span>Country</span><input v-model="form.country" /></label>
        <label class="field"><span>Discord</span><input v-model="form.discord" /></label>
      </div>
      <label class="field"><span>Avatar color</span><input v-model="form.avatar_color" type="color" /></label>
      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="saved" class="pill">Saved</p>
      <p v-if="saved && state.user?.role !== 'admin'" class="muted">Changes will appear after moderation.</p>
      <button class="button primary" type="submit">Save</button>
    </form>
    <RouterLink v-else class="button" to="/login">Login</RouterLink>
  </section>
</template>
