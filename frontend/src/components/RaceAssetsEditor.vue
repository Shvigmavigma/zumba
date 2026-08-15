<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Save, Trash2 } from 'lucide-vue-next'
import { api } from '../api'

const { t } = useI18n()
const emit = defineEmits(['error'])

const raceAssetGames = ['ACC', 'AC', 'iRacing', 'LMU']
const raceAssetGame = ref('ACC')
const raceAssetsByGame = ref(defaultRaceAssetsByGame())
const raceAssetsSaving = ref(false)
const raceAssetsSaved = ref(false)
const activeRaceAssetsDraft = computed(() => raceAssetsByGame.value[raceAssetGame.value])

function emptyRaceAssetDraft() {
  return { tracksText: '', classes: [], trackImages: {} }
}

function defaultRaceAssetsByGame() {
  return Object.fromEntries(raceAssetGames.map((game) => [game, emptyRaceAssetDraft()]))
}

function draftFromConfig(config = {}) {
  return {
    tracksText: (config.tracks || []).join('\n'),
    trackImages: { ...(config.track_images || {}) },
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

function configFromDraft(draft = emptyRaceAssetDraft()) {
  const tracks = draft.tracksText.split('\n').map((item) => item.trim()).filter(Boolean)
  const knownTracks = new Set(tracks)
  return {
    tracks,
    track_images: Object.fromEntries(Object.entries(draft.trackImages || {}).filter(([track, url]) => knownTracks.has(track) && url)),
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
    raceAssetsByGame.value = normalizeRaceAssetsDraft(await api('/race-assets'))
  } catch (err) {
    setError(err)
  }
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
        games
      }
    })
    raceAssetsByGame.value = normalizeRaceAssetsDraft(config)
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
  <form class="admin-settings-card admin-race-assets-card card" @submit.prevent="saveRaceAssets">
    <div class="admin-race-assets-head">
      <h2>{{ t('adminUsers.raceAssetsTitle') }}</h2>
      <p class="muted">{{ t('adminUsers.raceAssetsHint') }}</p>
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
    <div class="admin-race-assets-actions">
      <button class="button primary" type="submit" :disabled="raceAssetsSaving">
        <Save :size="16" />
        {{ raceAssetsSaving ? t('common.saving') : t('common.save') }}
      </button>
      <span v-if="raceAssetsSaved" class="pill">{{ t('common.saved') }}</span>
    </div>
  </form>
</template>
