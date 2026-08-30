<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronDown, Plus, Save, Trash2 } from 'lucide-vue-next'
import { api } from '../api'

const { t } = useI18n()
const emit = defineEmits(['error'])

const raceAssetGames = ['ACC', 'AC', 'iRacing', 'LMU']
const raceAssetGame = ref('ACC')
const raceAssetsByGame = ref(defaultRaceAssetsByGame())
const raceAssetsSaving = ref(false)
const raceAssetsSaved = ref(false)
const isCollapsed = ref(false)
const accCarModelMappings = ref([])
const activeRaceAssetsDraft = computed(() => raceAssetsByGame.value[raceAssetGame.value])

function emptyRaceAssetDraft() {
  return { tracksText: '', classes: [], trackImages: {}, trackExpectedLaps: {} }
}

function defaultRaceAssetsByGame() {
  return Object.fromEntries(raceAssetGames.map((game) => [game, emptyRaceAssetDraft()]))
}

function draftFromConfig(config = {}) {
  return {
    tracksText: (config.tracks || []).join('\n'),
    trackImages: { ...(config.track_images || {}) },
    trackExpectedLaps: Object.fromEntries(
      Object.entries(config.expected_average_lap_ms || {}).map(([track, lapMs]) => [track, formatLapDuration(lapMs)])
    ),
    classes: (config.classes || []).map((item) => ({
      name: item.name,
      carsText: (item.cars || []).join('\n')
    }))
  }
}

function normalizeRaceAssetsDraft(config = {}) {
  const games = config.games || {}
  return {
    ACC: draftFromConfig(games.ACC || config),
    AC: draftFromConfig(games.AC),
    iRacing: draftFromConfig(games.iRacing),
    LMU: draftFromConfig(games.LMU)
  }
}

function trackNames(draft = emptyRaceAssetDraft()) {
  return draft.tracksText.split('\n').map((item) => item.trim()).filter(Boolean)
}

const activeTrackNames = computed(() => trackNames(activeRaceAssetsDraft.value))

function formatLapDuration(value) {
  if (!Number.isFinite(Number(value))) return ''
  const totalMs = Math.max(0, Math.round(Number(value)))
  const minutes = Math.floor(totalMs / 60000)
  const seconds = Math.floor((totalMs % 60000) / 1000)
  const millis = totalMs % 1000
  return `${minutes}:${String(seconds).padStart(2, '0')}.${String(millis).padStart(3, '0')}`
}

function parseLapDuration(value) {
  const raw = String(value || '').trim()
  if (!raw) return null
  const parts = raw.split(':').map((part) => Number(part.replace(',', '.')))
  if (parts.length > 3 || parts.some((part) => !Number.isFinite(part))) throw new Error(t('adminUsers.raceAssetsInvalidLap'))
  const seconds = parts.length === 1
    ? parts[0]
    : parts.length === 2
      ? parts[0] * 60 + parts[1]
      : parts[0] * 3600 + parts[1] * 60 + parts[2]
  if (seconds <= 0) throw new Error(t('adminUsers.raceAssetsInvalidLap'))
  return Math.round(seconds * 1000)
}

function carModelMappingsFromConfig(config = {}) {
  return Object.entries(config.car_model_ids || {}).map(([name, id]) => ({
    name,
    id: Number(id)
  }))
}

function configFromDraft(draft = emptyRaceAssetDraft()) {
  const tracks = trackNames(draft)
  const knownTracks = new Set(tracks)
  const expected_average_lap_ms = Object.fromEntries(
    tracks
      .map((track) => [track, parseLapDuration(draft.trackExpectedLaps?.[track])])
      .filter(([, lapMs]) => lapMs !== null)
  )
  return {
    tracks,
    track_images: Object.fromEntries(Object.entries(draft.trackImages || {}).filter(([track, url]) => knownTracks.has(track) && url)),
    expected_average_lap_ms,
    classes: draft.classes
      .map((item) => ({
        name: item.name.trim(),
        cars: item.carsText.split('\n').map((car) => car.trim()).filter(Boolean)
      }))
      .filter((item) => item.name)
  }
}

function setError(err) {
  emit('error', err?.message || String(err || ''))
}

async function loadRaceAssets() {
  try {
    emit('error', '')
    const config = await api('/race-assets')
    raceAssetsByGame.value = normalizeRaceAssetsDraft(config)
    accCarModelMappings.value = carModelMappingsFromConfig(config)
  } catch (err) {
    setError(err)
  }
}

function addCarModelMapping() {
  accCarModelMappings.value = [...accCarModelMappings.value, { id: 0, name: '' }]
}

function removeCarModelMapping(index) {
  accCarModelMappings.value = accCarModelMappings.value.filter((_, itemIndex) => itemIndex !== index)
}

function addRaceAssetClass() {
  activeRaceAssetsDraft.value.classes = [...activeRaceAssetsDraft.value.classes, { name: '', carsText: '' }]
}

function removeRaceAssetClass(index) {
  activeRaceAssetsDraft.value.classes = activeRaceAssetsDraft.value.classes.filter((_, itemIndex) => itemIndex !== index)
}

async function saveRaceAssets() {
  raceAssetsSaving.value = true
  raceAssetsSaved.value = false
  emit('error', '')
  try {
    const games = Object.fromEntries(raceAssetGames.map((game) => [game, configFromDraft(raceAssetsByGame.value[game])]))
    const config = await api('/race-assets', {
      method: 'PATCH',
      body: {
        ...games.ACC,
        games,
        car_model_ids: Object.fromEntries(
          accCarModelMappings.value
            .map((item) => [String(item.name || '').trim(), Number(item.id)])
            .filter(([name, id]) => name && Number.isInteger(id) && id >= 0 && id <= 100)
        )
      }
    })
    raceAssetsByGame.value = normalizeRaceAssetsDraft(config)
    accCarModelMappings.value = carModelMappingsFromConfig(config)
    raceAssetsSaved.value = true
  } catch (err) {
    setError(err)
  } finally {
    raceAssetsSaving.value = false
  }
}

onMounted(loadRaceAssets)
</script>

<template>
  <form class="admin-settings-card admin-race-assets-card card" :class="{ 'is-collapsed': isCollapsed }" @submit.prevent="saveRaceAssets">
    <div class="admin-race-assets-head admin-zone-head">
      <h2>{{ t('adminUsers.raceAssetsTitle') }}</h2>
      <p class="muted">{{ t('adminUsers.raceAssetsHint') }}</p>
      <button class="icon-button admin-zone-toggle" type="button" :aria-expanded="!isCollapsed" :aria-label="isCollapsed ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" :title="isCollapsed ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" @click="isCollapsed = !isCollapsed">
        <ChevronDown :size="18" />
      </button>
    </div>
    <div class="admin-race-assets-tabs">
      <button
        v-for="game in raceAssetGames"
        :key="game"
        class="button small"
        :class="{ primary: raceAssetGame === game }"
        type="button"
        @click="raceAssetGame = game"
      >
        {{ game }}
      </button>
    </div>
    <label class="field admin-race-assets-tracks">
      <span>{{ t('adminUsers.raceAssetsTracks') }}</span>
      <textarea v-model="activeRaceAssetsDraft.tracksText" required></textarea>
    </label>
    <section class="admin-race-assets-laps" aria-labelledby="expected-average-lap-title">
      <div class="section-header compact">
        <div>
          <h3 id="expected-average-lap-title">{{ t('adminUsers.expectedAverageLap') }}</h3>
          <p class="muted">{{ t('adminUsers.expectedAverageLapHint') }}</p>
        </div>
      </div>
      <div v-if="activeTrackNames.length" class="admin-race-assets-laps-list">
        <label v-for="track in activeTrackNames" :key="track" class="field admin-race-assets-lap-row">
          <span>{{ track }}</span>
          <input
            v-model="activeRaceAssetsDraft.trackExpectedLaps[track]"
            type="text"
            inputmode="decimal"
            placeholder="1:48.500"
            :aria-label="`${t('adminUsers.expectedAverageLap')}: ${track}`"
          />
        </label>
      </div>
      <p v-else class="muted">{{ t('adminUsers.expectedAverageLapEmpty') }}</p>
    </section>
    <div class="admin-race-assets-classes">
      <div class="section-header compact">
        <h3>{{ t('adminUsers.raceAssetsClasses') }}</h3>
        <button class="button small" type="button" @click="addRaceAssetClass"><Plus :size="15" />{{ t('adminUsers.addRaceClass') }}</button>
      </div>
      <article v-for="(item, index) in activeRaceAssetsDraft.classes" :key="index" class="admin-race-class-row">
        <label class="field">
          <span>{{ t('fields.class') }}</span>
          <input v-model="item.name" required />
        </label>
        <label class="field">
          <span>{{ t('fields.allowedCars') }}</span>
          <textarea v-model="item.carsText" required></textarea>
        </label>
        <button class="icon-button danger-icon" type="button" :title="t('common.delete')" :aria-label="t('common.delete')" @click="removeRaceAssetClass(index)">
          <Trash2 :size="16" />
        </button>
      </article>
    </div>
    <div v-if="raceAssetGame === 'ACC'" class="admin-car-model-mapping">
      <div class="section-header compact">
        <div>
          <h3>{{ t('adminUsers.raceAssetsCarModelMap') }}</h3>
          <p class="muted">{{ t('adminUsers.raceAssetsCarModelMapHint') }}</p>
        </div>
        <button class="button small" type="button" @click="addCarModelMapping"><Plus :size="15" />{{ t('adminUsers.addCarModel') }}</button>
      </div>
      <div class="admin-car-model-mapping-list">
        <article v-for="(item, index) in accCarModelMappings" :key="`${index}-${item.name}`" class="admin-car-model-mapping-row">
          <label class="field">
            <span>{{ t('adminUsers.carModelId') }}</span>
            <input v-model.number="item.id" type="number" min="0" max="100" required />
          </label>
          <label class="field">
            <span>{{ t('adminUsers.carModelName') }}</span>
            <input v-model="item.name" required />
          </label>
          <button class="icon-button danger-icon" type="button" :title="t('common.delete')" :aria-label="t('common.delete')" @click="removeCarModelMapping(index)">
            <Trash2 :size="16" />
          </button>
        </article>
      </div>
    </div>
    <div class="admin-race-assets-actions">
      <button class="button primary" type="submit" :disabled="raceAssetsSaving">
        <Save :size="16" />
        {{ raceAssetsSaving ? t('common.saving') : t('common.save') }}
      </button>
      <span v-if="raceAssetsSaved" class="pill">{{ t('common.saved') }}</span>
    </div>
  </form>
</template>
