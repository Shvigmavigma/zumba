<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'

const route = useRoute()
const router = useRouter()
const isEdit = route.params.id && route.path.endsWith('/edit')
const error = ref('')
const form = ref({
  name: '',
  description: '',
  server_link: '',
  datetime_start: '',
  datetime_end: '',
  max_pilots: 32,
  car_class: '',
  track: '',
  mods_pack: [],
  allowed_cars: [],
  game: 'Assetto Corsa',
  is_official: false
})
const modsText = ref('')
const carsText = ref('')

function toIso(value) {
  return new Date(value).toISOString()
}

async function submit() {
  error.value = ''
  try {
    const body = {
      ...form.value,
      datetime_start: toIso(form.value.datetime_start),
      datetime_end: toIso(form.value.datetime_end),
      mods_pack: modsText.value.split('\n').map((item) => item.trim()).filter(Boolean),
      allowed_cars: carsText.value.split('\n').map((item) => item.trim()).filter(Boolean)
    }
    const race = isEdit
      ? await api(`/races/${route.params.id}`, { method: 'PATCH', body })
      : await api('/races', { method: 'POST', body })
    router.push(`/races/${race.id}`)
  } catch (err) {
    error.value = err.message
  }
}

onMounted(async () => {
  if (!isEdit) return
  const race = await api(`/races/${route.params.id}`)
  form.value = {
    ...race,
    datetime_start: race.datetime_start.slice(0, 16),
    datetime_end: race.datetime_end.slice(0, 16)
  }
  modsText.value = race.mods_pack?.join('\n') || ''
  carsText.value = race.allowed_cars?.join('\n') || ''
})
</script>

<template>
  <section class="section card">
    <h1>RaceEdit</h1>
    <form class="form" @submit.prevent="submit">
      <div class="form-row">
        <label class="field"><span>Name</span><input v-model="form.name" required /></label>
        <label class="field"><span>Track</span><input v-model="form.track" required /></label>
      </div>
      <label class="field"><span>Description</span><textarea v-model="form.description" required /></label>
      <div class="form-row">
        <label class="field"><span>Server link</span><input v-model="form.server_link" required /></label>
        <label class="field"><span>Class</span><input v-model="form.car_class" required /></label>
      </div>
      <div class="form-row">
        <label class="field"><span>Registration start</span><input v-model="form.datetime_start" type="datetime-local" required /></label>
        <label class="field"><span>Registration end</span><input v-model="form.datetime_end" type="datetime-local" required /></label>
      </div>
      <div class="form-row">
        <label class="field"><span>Max pilots</span><input v-model.number="form.max_pilots" type="number" min="1" required /></label>
        <label class="field"><span>Game</span><input v-model="form.game" /></label>
      </div>
      <div class="form-row">
        <label class="field"><span>Mods URLs, one per line</span><textarea v-model="modsText" /></label>
        <label class="field"><span>Allowed cars, one per line</span><textarea v-model="carsText" /></label>
      </div>
      <label><input v-model="form.is_official" type="checkbox" /> Official race</label>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="button primary" type="submit">Save</button>
    </form>
  </section>
</template>

