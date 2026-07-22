<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { gameOptions } from '../i18nLabels'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const isEdit = route.params.id && route.path.endsWith('/edit')
const pageTitle = computed(() => t(isEdit ? 'raceEdit.editTitle' : 'raceEdit.createTitle'))
const gameChoices = computed(() => gameOptions(t))
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
  game: 'ACC',
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
    <h1>{{ pageTitle }}</h1>
    <form class="form" @submit.prevent="submit">
      <div class="form-row">
        <label class="field"><span>{{ t('fields.name') }}</span><input v-model="form.name" required /></label>
        <label class="field"><span>{{ t('fields.track') }}</span><input v-model="form.track" required /></label>
      </div>
      <label class="field"><span>{{ t('fields.description') }}</span><textarea v-model="form.description" required /></label>
      <div class="form-row">
        <label class="field"><span>{{ t('fields.serverLink') }}</span><input v-model="form.server_link" required /></label>
        <label class="field"><span>{{ t('fields.class') }}</span><input v-model="form.car_class" required /></label>
      </div>
      <div class="form-row">
        <label class="field"><span>{{ t('fields.registrationStart') }}</span><input v-model="form.datetime_start" type="datetime-local" required /></label>
        <label class="field"><span>{{ t('fields.registrationEnd') }}</span><input v-model="form.datetime_end" type="datetime-local" required /></label>
      </div>
      <div class="form-row">
        <label class="field"><span>{{ t('fields.maxPilots') }}</span><input v-model.number="form.max_pilots" type="number" min="1" required /></label>
        <label class="field">
          <span>{{ t('fields.game') }}</span>
          <select v-model="form.game">
            <option v-for="option in gameChoices" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
      </div>
      <div class="form-row">
        <label class="field"><span>{{ t('fields.modsUrls') }}</span><textarea v-model="modsText" /></label>
        <label class="field"><span>{{ t('fields.allowedCars') }}</span><textarea v-model="carsText" /></label>
      </div>
      <label><input v-model="form.is_official" type="checkbox" /> {{ t('fields.officialRace') }}</label>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="button primary" type="submit">{{ t('common.save') }}</button>
    </form>
  </section>
</template>
