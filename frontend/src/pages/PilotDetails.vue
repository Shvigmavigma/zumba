<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'

const route = useRoute()
const pilot = ref(null)
const error = ref('')

onMounted(async () => {
  try {
    pilot.value = await api(`/users/${route.params.id}`)
  } catch (err) {
    error.value = err.message
  }
})
</script>

<template>
  <section class="section card">
    <p v-if="error" class="error">{{ error }}</p>
    <template v-if="pilot">
      <div class="section-header">
        <h1>{{ pilot.first_name }} {{ pilot.last_name }}</h1>
        <span class="pill">SR {{ pilot.sr }}</span>
      </div>
      <p class="muted">{{ pilot.nickname }} · #{{ pilot.pilot_number }} · {{ pilot.country || 'Global' }}</p>
      <p>Steam: {{ pilot.steam_id }}</p>
      <p>Discord: {{ pilot.discord || '—' }}</p>
    </template>
  </section>
</template>

