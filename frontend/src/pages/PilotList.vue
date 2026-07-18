<script setup>
import { onMounted, ref, watch } from 'vue'
import { api } from '../api'

const pilots = ref([])
const search = ref('')
const error = ref('')

async function load() {
  try {
    pilots.value = await api(`/users/pilots?search=${encodeURIComponent(search.value)}`)
  } catch (err) {
    error.value = err.message
  }
}

onMounted(load)
watch(search, load)
</script>

<template>
  <section class="section">
    <div class="section-header">
      <h1>PilotList</h1>
      <input v-model="search" placeholder="Search" />
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <table class="table card">
      <thead>
        <tr><th>#</th><th>Pilot</th><th>Country</th><th>SR</th></tr>
      </thead>
      <tbody>
        <tr v-for="pilot in pilots" :key="pilot.id">
          <td>{{ pilot.pilot_number }}</td>
          <td><RouterLink :to="`/pilots/${pilot.id}`">{{ pilot.first_name }} {{ pilot.last_name }} · {{ pilot.nickname }}</RouterLink></td>
          <td>{{ pilot.country || '—' }}</td>
          <td>{{ pilot.sr }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

