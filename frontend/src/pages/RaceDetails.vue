<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import { state } from '../store'

const route = useRoute()
const race = ref(null)
const penalties = ref([])
const appeals = ref([])
const car = ref('')
const error = ref('')
const appeal = ref({ penalty_id: null, proof_link: '', description: '' })

const registered = computed(() => race.value?.registered_pilots?.some((item) => item.user_id === state.user?.id))
const myPenalties = computed(() => penalties.value.filter((penalty) => penalty.target_id === state.user?.id))

async function load() {
  try {
    race.value = await api(`/races/${route.params.id}`)
    if (state.user) {
      penalties.value = await api(`/penalties?race_id=${route.params.id}`)
      appeals.value = await api('/appeals')
    }
    car.value = race.value.allowed_cars?.[0] || ''
  } catch (err) {
    error.value = err.message
  }
}

async function register() {
  race.value = await api(`/races/${race.value.id}/register`, { method: 'POST', body: { car_model: car.value } })
}

async function unregister() {
  race.value = await api(`/races/${race.value.id}/register`, { method: 'DELETE' })
}

async function createAppeal(penalty) {
  appeal.value.penalty_id = penalty.id
  await api('/appeals', { method: 'POST', body: { ...appeal.value, race_id: race.value.id } })
  appeal.value = { penalty_id: null, proof_link: '', description: '' }
  await load()
}

function appealForPenalty(penaltyId) {
  return appeals.value.find((item) => item.penalty_id === penaltyId)
}

onMounted(load)
</script>

<template>
  <section class="section card">
    <p v-if="error" class="error">{{ error }}</p>
    <template v-if="race">
      <div class="section-header">
        <div>
          <h1>RaceDetails</h1>
          <p class="muted">{{ race.name }} · {{ race.track }} · {{ race.car_class }}</p>
        </div>
        <RouterLink v-if="['admin', 'moder'].includes(state.user?.role)" class="button" :to="`/races/${race.id}/edit`">Edit</RouterLink>
      </div>
      <p>{{ race.description }}</p>
      <p><span class="pill">{{ race.status }}</span> {{ new Date(race.datetime_start).toLocaleString(state.locale) }} - {{ new Date(race.datetime_end).toLocaleString(state.locale) }}</p>
      <p>Server: <a :href="race.server_link">{{ race.server_link }}</a></p>
      <p>Mods: {{ race.mods_pack?.join(', ') || '—' }}</p>

      <div v-if="race.status === 'registration_open' && state.user" class="card">
        <div v-if="registered" class="section-header">
          <strong>Already registered</strong>
          <button class="button danger" @click="unregister">Unregister</button>
        </div>
        <form v-else class="form" @submit.prevent="register">
          <label class="field"><span>Car</span><select v-model="car"><option v-for="item in race.allowed_cars" :key="item">{{ item }}</option></select></label>
          <button class="button primary" type="submit">Register</button>
        </form>
      </div>

      <section class="section">
        <h2>Registered pilots</h2>
        <div class="grid cols-2">
          <div v-for="item in race.registered_pilots" :key="item.user_id" class="card">#{{ item.user_id }} · {{ item.car_model }}</div>
        </div>
      </section>

      <section v-if="myPenalties.length" class="section">
        <h2>My penalties</h2>
        <article v-for="penalty in myPenalties" :key="penalty.id" class="card">
          <strong>{{ penalty.penalty_type }} · {{ penalty.penalty_value }}</strong>
          <p>{{ penalty.description }}</p>
          <p v-if="appealForPenalty(penalty.id)" class="pill">{{ appealForPenalty(penalty.id).status }}</p>
          <p v-if="appealForPenalty(penalty.id)?.rejection_reason" class="muted">{{ appealForPenalty(penalty.id).rejection_reason }}</p>
          <form v-if="penalty.status === 'active' && !appealForPenalty(penalty.id)" class="form" @submit.prevent="createAppeal(penalty)">
            <label class="field"><span>Proof link</span><input v-model="appeal.proof_link" type="url" required /></label>
            <label class="field"><span>Description</span><textarea v-model="appeal.description" required /></label>
            <button class="button" type="submit">Appeal</button>
          </form>
        </article>
      </section>
    </template>
  </section>
</template>
