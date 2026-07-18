<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'

const users = ref([])
const error = ref('')

async function load() {
  users.value = await api('/users/moderation/pending')
}

async function approve(user) {
  await api(`/users/${user.id}/approve`, { method: 'POST' })
  await load()
}

async function reject(user) {
  await api(`/users/${user.id}/reject`, { method: 'DELETE' })
  await load()
}

onMounted(async () => {
  try {
    await load()
  } catch (err) {
    error.value = err.message
  }
})
</script>

<template>
  <section class="section">
    <h1>UserEditModeration</h1>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="grid">
      <article v-for="user in users" :key="user.id" class="card race-item">
        <div>
          <strong>{{ user.first_name }} {{ user.last_name }} · {{ user.nickname }}</strong>
          <p class="muted">#{{ user.pilot_number }} · {{ user.email }} · Steam {{ user.steam_id }}</p>
          <p v-if="user.pending_profile_changes" class="muted">Pending profile changes: {{ user.pending_profile_changes }}</p>
        </div>
        <div class="toolbar">
          <button class="button primary" @click="approve(user)">Approve</button>
          <button class="button danger" @click="reject(user)">Reject</button>
        </div>
      </article>
    </div>
  </section>
</template>
