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
const raceAssets = ref({ tracks: [], classes: [], games: {} })
const assetGames = ['ACC', 'AC', 'iRacing', 'LMU']
const defaultWeatherChances = () => ({
  clear: 100,
  partly_cloudy: 0,
  overcast: 0,
  light_rain: 0,
  heavy_rain: 0,
  storm: 0
})
const form = ref({
  name: '',
  description: '',
  server_link: '',
  lmu_results_at: '',
  registration_start: '',
  datetime_start: '',
  datetime_end: '',
  max_pilots: 32,
  car_class: '',
  track: '',
  mods_pack: [],
  allowed_cars: [],
  weather_chances: defaultWeatherChances(),
  track_temperature: 25,
  game: 'ACC',
  has_qualification: true,
  is_team_event: false,
  is_official: false
})
const modsText = ref('')
const carsText = ref('')
const isAssetRace = computed(() => assetGames.includes(form.value.game))
const isLmuRace = computed(() => form.value.game === 'LMU')
const currentRaceAssets = computed(() => {
  if (form.value.game === 'ACC') return raceAssets.value.games?.ACC || raceAssets.value
  return raceAssets.value.games?.[form.value.game] || { tracks: [], classes: [] }
})
const trackChoices = computed(() => withCurrent(currentRaceAssets.value.tracks || [], form.value.track))
const classChoices = computed(() => {
  const current = form.value.car_class
  const classes = currentRaceAssets.value.classes || []
  if (!current || classes.some((item) => item.name === current)) return classes
  return [...classes, { name: current, cars: form.value.allowed_cars || [] }]
})
const selectedClass = computed(() => classChoices.value.find((item) => item.name === form.value.car_class) || null)
const selectedClassCars = computed(() => selectedClass.value?.cars || [])
const allClassCarsSelected = computed(() => selectedClassCars.value.length > 0 && selectedClassCars.value.every((car) => form.value.allowed_cars.includes(car)))
const weatherConditions = computed(() => [
  { key: 'clear', label: t('weather.clear') },
  { key: 'partly_cloudy', label: t('weather.partlyCloudy') },
  { key: 'overcast', label: t('weather.overcast') },
  { key: 'light_rain', label: t('weather.lightRain') },
  { key: 'heavy_rain', label: t('weather.heavyRain') },
  { key: 'storm', label: t('weather.storm') }
])

function withCurrent(items, current) {
  if (!current || items.includes(current)) return items
  return [...items, current]
}

function isKnownTrack(value) {
  return (currentRaceAssets.value.tracks || []).includes(value)
}

function isKnownClass(value) {
  return (currentRaceAssets.value.classes || []).some((item) => item.name === value)
}

function toIso(value) {
  return new Date(value).toISOString()
}

function optionalIso(value) {
  return value ? toIso(value) : null
}

function applyAssetDefaults({ forceCars = false } = {}) {
  if (!isAssetRace.value) return
  if ((!form.value.track || !isKnownTrack(form.value.track)) && currentRaceAssets.value.tracks.length) {
    form.value.track = currentRaceAssets.value.tracks[0]
  }
  if ((!form.value.car_class || !isKnownClass(form.value.car_class)) && currentRaceAssets.value.classes.length) {
    form.value.car_class = currentRaceAssets.value.classes[0].name
  }
  if (forceCars || !form.value.allowed_cars.length) {
    form.value.allowed_cars = [...selectedClassCars.value]
  } else {
    form.value.allowed_cars = form.value.allowed_cars.filter((car) => selectedClassCars.value.includes(car))
  }
  if (!form.value.allowed_cars.length && selectedClassCars.value.length) {
    form.value.allowed_cars = [...selectedClassCars.value]
  }
}

function handleGameChange() {
  form.value.track = ''
  form.value.car_class = ''
  form.value.allowed_cars = []
  if (isLmuRace.value && !form.value.lmu_results_at) {
    form.value.lmu_results_at = form.value.datetime_start
  }
  if (!isLmuRace.value) form.value.lmu_results_at = ''
  applyAssetDefaults({ forceCars: true })
}

function handleClassChange() {
  applyAssetDefaults({ forceCars: true })
}

function toggleAllClassCars() {
  form.value.allowed_cars = allClassCarsSelected.value ? [] : [...selectedClassCars.value]
}

async function submit() {
  error.value = ''
  try {
    const allowedCars = isLmuRace.value
      ? []
      : isAssetRace.value
      ? form.value.allowed_cars.filter(Boolean)
      : carsText.value.split('\n').map((item) => item.trim()).filter(Boolean)
    if (!isLmuRace.value && isAssetRace.value && !allowedCars.length) throw new Error(t('raceAssets.chooseCars'))
    const body = {
      ...form.value,
      description: isLmuRace.value ? (form.value.description || '') : form.value.description,
      registration_start: toIso(form.value.registration_start),
      datetime_start: toIso(form.value.datetime_start),
      datetime_end: toIso(form.value.datetime_end),
      lmu_results_at: isLmuRace.value ? optionalIso(form.value.lmu_results_at || form.value.datetime_start) : null,
      max_pilots: isLmuRace.value ? 1 : form.value.max_pilots,
      track: form.value.track,
      car_class: form.value.car_class,
      mods_pack: isLmuRace.value ? [] : modsText.value.split('\n').map((item) => item.trim()).filter(Boolean),
      allowed_cars: allowedCars,
      has_qualification: isLmuRace.value ? false : form.value.has_qualification
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
  raceAssets.value = await api('/race-assets')
  if (!isEdit) {
    applyAssetDefaults()
    return
  }
  const race = await api(`/races/${route.params.id}`)
  form.value = {
    ...race,
    weather_chances: { ...defaultWeatherChances(), ...(race.weather_chances || {}) },
    track_temperature: race.track_temperature ?? 25,
    registration_start: race.registration_start.slice(0, 16),
    datetime_start: race.datetime_start.slice(0, 16),
    datetime_end: race.datetime_end.slice(0, 16),
    lmu_results_at: race.lmu_results_at ? race.lmu_results_at.slice(0, 16) : ''
  }
  modsText.value = race.mods_pack?.join('\n') || ''
  carsText.value = race.allowed_cars?.join('\n') || ''
  applyAssetDefaults()
})
</script>

<template>
  <section class="section card">
    <h1>{{ pageTitle }}</h1>
    <form class="form" @submit.prevent="submit">
      <div class="form-row">
        <label class="field"><span>{{ t('fields.name') }}</span><input v-model="form.name" required /></label>
        <label class="field">
          <span>{{ t('fields.track') }}</span>
          <select v-if="isAssetRace" v-model="form.track" required>
            <option v-for="track in trackChoices" :key="track" :value="track">{{ track }}</option>
          </select>
          <input v-else v-model="form.track" required />
        </label>
      </div>
      <label v-if="!isLmuRace" class="field"><span>{{ t('fields.description') }}</span><textarea v-model="form.description" required /></label>
      <div class="form-row">
        <label class="field"><span>{{ isLmuRace ? t('fields.linkUrl') : t('fields.serverLink') }}</span><input v-model="form.server_link" required /></label>
        <label class="field">
          <span>{{ t('fields.class') }}</span>
          <select v-if="isAssetRace" v-model="form.car_class" required @change="handleClassChange">
            <option v-for="item in classChoices" :key="item.name" :value="item.name">{{ item.name }}</option>
          </select>
          <input v-else v-model="form.car_class" required />
        </label>
      </div>
      <label class="field"><span>{{ t('fields.registrationStart') }}</span><input v-model="form.registration_start" type="datetime-local" required /></label>
      <section class="race-registration-deadline-editor">
        <div class="section-header compact">
          <div>
            <h3>{{ t('raceCard.registrationCloses') }}</h3>
            <p class="muted">{{ t('fields.registrationEnd') }}</p>
          </div>
        </div>
        <label class="field">
          <span>{{ t('raceCard.registrationCloses') }}</span>
          <input v-model="form.datetime_end" type="datetime-local" required />
        </label>
      </section>
      <label class="field"><span>{{ t('fields.raceTime') }}</span><input v-model="form.datetime_start" type="datetime-local" required /></label>
      <section class="race-weather-editor">
        <div class="section-header compact">
          <div>
            <h3>{{ t('weather.title') }}</h3>
            <p class="muted">{{ t('weather.hint') }}</p>
          </div>
        </div>
        <div class="race-weather-grid">
          <label v-for="condition in weatherConditions" :key="condition.key" class="field">
            <span>{{ condition.label }}</span>
            <input v-model.number="form.weather_chances[condition.key]" type="number" min="0" max="100" step="1" />
          </label>
          <label class="field">
            <span>{{ t('weather.trackTemperature') }}</span>
            <input v-model.number="form.track_temperature" type="number" min="-50" max="80" step="0.1" />
          </label>
        </div>
      </section>
      <label v-if="isLmuRace" class="field">
        <span>{{ t('fields.lmuResultsAt') }}</span>
        <input v-model="form.lmu_results_at" type="datetime-local" required />
      </label>
      <div class="form-row">
        <label v-if="!isLmuRace" class="field"><span>{{ t('fields.maxPilots') }}</span><input v-model.number="form.max_pilots" type="number" min="1" required /></label>
        <label class="field">
          <span>{{ t('fields.game') }}</span>
          <select v-model="form.game" @change="handleGameChange">
            <option v-for="option in gameChoices" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
      </div>
      <div v-if="!isLmuRace" class="form-row">
        <label class="field"><span>{{ t('fields.modsUrls') }}</span><textarea v-model="modsText" /></label>
        <label v-if="!isAssetRace" class="field"><span>{{ t('fields.allowedCars') }}</span><textarea v-model="carsText" /></label>
      </div>
      <div v-if="isAssetRace && !isLmuRace" class="field race-car-picker is-required">
        <span>{{ t('fields.allowedCars') }}</span>
        <div class="race-car-picker-head">
          <button class="button small" type="button" :disabled="!selectedClassCars.length" @click="toggleAllClassCars">
            {{ allClassCarsSelected ? t('common.clear') : t('raceAssets.selectAll') }}
          </button>
          <span class="pill">{{ t('raceAssets.selectedCars', { count: form.allowed_cars.length, total: selectedClassCars.length }) }}</span>
        </div>
        <div class="race-car-grid">
          <label v-for="car in selectedClassCars" :key="car" class="race-car-option">
            <input v-model="form.allowed_cars" type="checkbox" :value="car" />
            <span>{{ car }}</span>
          </label>
        </div>
      </div>
      <label v-if="!isLmuRace"><input v-model="form.has_qualification" type="checkbox" /> {{ t('fields.qualification') }}</label>
      <label v-if="!isLmuRace"><input v-model="form.is_team_event" type="checkbox" /> Командная гонка</label>
      <label v-if="!isLmuRace"><input v-model="form.is_official" type="checkbox" /> {{ t('fields.officialRace') }}</label>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="button primary" type="submit">{{ t('common.save') }}</button>
    </form>
  </section>
</template>
