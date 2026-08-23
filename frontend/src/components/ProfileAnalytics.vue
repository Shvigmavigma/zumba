<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { RATING_GAMES, formatRating } from '../pilotDisplay'
import { formatDateTime as formatDateTimeInZone } from '../timezone'

const props = defineProps({
  userId: { type: [Number, String], required: true },
  favoriteCar: { type: String, default: '' },
  user: { type: Object, default: null }
})

const { t } = useI18n()
const loading = ref(false)
const error = ref('')
const analytics = ref({ best_laps: [], recent_results: [], rating_history: [] })
const activeTab = ref('laps')
const selectedGame = ref('all')
const tabs = computed(() => [
  { key: 'laps', label: t('profile.statsBestLaps') },
  { key: 'results', label: t('profile.statsRecentResults') },
  { key: 'rating', label: t('profile.statsRatingChart') }
])
const gameOptions = computed(() => {
  const games = new Set([...RATING_GAMES, ...analytics.value.best_laps.map((item) => item.game), ...analytics.value.recent_results.map((item) => item.game)])
  return ['all', ...[...games].filter((game) => RATING_GAMES.includes(game))]
})
const activeFavoriteCar = computed(() => props.favoriteCar || analytics.value.favorite_car || '')
const bestLaps = computed(() => analytics.value.best_laps.filter((item) => selectedGame.value === 'all' || item.game === selectedGame.value))
const recentResults = computed(() => analytics.value.recent_results.filter((item) => selectedGame.value === 'all' || item.game === selectedGame.value).slice(0, 12))
const ratingHistory = computed(() => analytics.value.rating_history.filter((item) => selectedGame.value === 'all' || item.game === selectedGame.value).slice(-30))
const chartPoints = computed(() => {
  const points = ratingHistory.value
  if (!points.length) return []
  const width = 560
  const height = 180
  const values = points.map((item) => Number(item.rating) || 0)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const spread = Math.max(20, max - min)
  return points.map((item, index) => ({
    ...item,
    x: points.length === 1 ? width / 2 : (index / (points.length - 1)) * width,
    y: height - ((Number(item.rating) - (min - spread * 0.15)) / (spread * 1.3)) * height
  }))
})
function smoothChartPath(points) {
  if (!points.length) return ''
  if (points.length === 1) return `M ${points[0].x.toFixed(2)} ${points[0].y.toFixed(2)}`
  let path = `M ${points[0].x.toFixed(2)} ${points[0].y.toFixed(2)}`
  for (let index = 0; index < points.length - 1; index += 1) {
    const previous = points[index - 1] || points[index]
    const current = points[index]
    const next = points[index + 1]
    const following = points[index + 2] || next
    const controlOne = {
      x: current.x + (next.x - previous.x) / 6,
      y: current.y + (next.y - previous.y) / 6
    }
    const controlTwo = {
      x: next.x - (following.x - current.x) / 6,
      y: next.y - (following.y - current.y) / 6
    }
    path += ` C ${controlOne.x.toFixed(2)} ${controlOne.y.toFixed(2)}, ${controlTwo.x.toFixed(2)} ${controlTwo.y.toFixed(2)}, ${next.x.toFixed(2)} ${next.y.toFixed(2)}`
  }
  return path
}

const chartPath = computed(() => smoothChartPath(chartPoints.value))
const chartAreaPath = computed(() => {
  const points = chartPoints.value
  if (!points.length) return ''
  return `${chartPath.value} L ${points[points.length - 1].x.toFixed(2)} 180 L ${points[0].x.toFixed(2)} 180 Z`
})
const chartMin = computed(() => chartPoints.value.length ? Math.min(...chartPoints.value.map((item) => item.rating)) : 0)
const chartMax = computed(() => chartPoints.value.length ? Math.max(...chartPoints.value.map((item) => item.rating)) : 0)

function gameLabel(game) {
  return t(`games.${game}`, game)
}

function formatLap(ms) {
  if (!Number.isFinite(Number(ms)) || Number(ms) <= 0) return t('common.none')
  const total = Math.round(Number(ms))
  const minutes = Math.floor(total / 60000)
  const seconds = Math.floor((total % 60000) / 1000).toString().padStart(2, '0')
  const milliseconds = (total % 1000).toString().padStart(3, '0')
  return `${minutes}:${seconds}.${milliseconds}`
}

function formatFinish(ms) {
  if (!Number.isFinite(Number(ms)) || Number(ms) <= 0) return t('common.none')
  const total = Math.round(Number(ms))
  const hours = Math.floor(total / 3600000)
  const minutes = Math.floor((total % 3600000) / 60000).toString().padStart(2, '0')
  const seconds = Math.floor((total % 60000) / 1000).toString().padStart(2, '0')
  return hours ? `${hours}:${minutes}:${seconds}` : `${minutes}:${seconds}`
}

function formatDate(value) {
  return value ? formatDateTimeInZone(value, { dateStyle: 'medium', timeStyle: 'short' }) : t('common.none')
}

function signedChange(value) {
  const amount = Number(value)
  if (!Number.isFinite(amount) || amount === 0) return '0'
  return `${amount > 0 ? '+' : ''}${amount}`
}

function changeClass(value) {
  return Number(value) > 0 ? 'is-positive' : Number(value) < 0 ? 'is-negative' : ''
}

async function load() {
  if (!props.userId) return
  loading.value = true
  error.value = ''
  try {
    analytics.value = await api(`/users/${props.userId}/analytics`)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.userId, load)
</script>

<template>
  <section class="profile-analytics card">
    <div class="profile-analytics-head">
      <div>
        <p class="eyebrow">{{ t('profile.statsEyebrow') }}</p>
        <h2>{{ t('profile.statsTitle') }}</h2>
      </div>
      <div class="profile-analytics-controls">
        <span v-if="activeFavoriteCar" class="pill profile-favorite-car">{{ t('profile.favoriteCar') }}: {{ activeFavoriteCar }}</span>
        <label class="profile-game-filter">
          <span class="sr-only">{{ t('fields.game') }}</span>
          <select v-model="selectedGame">
            <option v-for="game in gameOptions" :key="game" :value="game">{{ game === 'all' ? t('profile.allSimulators') : gameLabel(game) }}</option>
          </select>
        </label>
      </div>
    </div>
    <div class="profile-analytics-tabs" role="tablist">
      <button v-for="tab in tabs" :key="tab.key" class="button small" :class="{ primary: activeTab === tab.key }" type="button" role="tab" :aria-selected="activeTab === tab.key" @click="activeTab = tab.key">
        {{ tab.label }}
      </button>
    </div>
    <p v-if="loading" class="muted">{{ t('common.loading') }}...</p>
    <p v-else-if="error" class="error">{{ error }}</p>
    <template v-else>
      <div v-if="activeTab === 'laps'" class="profile-stat-panel">
        <div v-if="bestLaps.length" class="profile-lap-list">
          <RouterLink v-for="item in bestLaps" :key="`${item.game}-${item.track}`" class="profile-lap-row" :to="`/races/${item.race_id}`">
            <div>
              <strong>{{ item.track }}</strong>
              <span class="muted">{{ gameLabel(item.game) }} · {{ item.car_model || t('common.none') }}</span>
            </div>
            <div class="profile-lap-value">
              <strong>{{ formatLap(item.best_lap_ms) }}</strong>
              <span class="pill">{{ item.session === 'qualification' ? t('profile.qualificationLap') : t('profile.raceLap') }}</span>
            </div>
          </RouterLink>
        </div>
        <p v-else class="muted">{{ t('profile.noBestLaps') }}</p>
      </div>

      <div v-else-if="activeTab === 'results'" class="profile-stat-panel">
        <div v-if="recentResults.length" class="profile-results-list">
          <RouterLink v-for="item in recentResults" :key="`${item.race_id}-${item.recorded_at}`" class="profile-result-row" :to="`/races/${item.race_id}`">
            <div class="profile-result-main">
              <strong>{{ item.race_name }}</strong>
              <span class="muted">{{ item.track }} · {{ formatDate(item.recorded_at) }} · {{ gameLabel(item.game) }}</span>
            </div>
            <span class="profile-result-position">{{ item.position ? `P${item.position}` : '—' }}</span>
            <div class="profile-result-meta">
              <span>{{ item.car_model || t('common.none') }}</span>
              <span>{{ formatFinish(item.finish_ms) }}</span>
              <span :class="['profile-rating-change', changeClass(item.rating_change)]">RER {{ item.rating_change === null ? '—' : signedChange(item.rating_change) }}</span>
            </div>
          </RouterLink>
        </div>
        <p v-else class="muted">{{ t('profile.noRecentResults') }}</p>
      </div>

      <div v-else class="profile-stat-panel profile-rating-panel">
        <div v-if="chartPoints.length" class="profile-rating-chart-wrap">
          <div class="profile-rating-chart-labels"><span>{{ chartMax }}</span><span>{{ chartMin }}</span></div>
          <svg class="profile-rating-chart" viewBox="0 0 560 180" role="img" :aria-label="t('profile.statsRatingChart')">
            <defs>
              <linearGradient id="profile-rating-fill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="var(--primary)" stop-opacity="0.22" />
                <stop offset="100%" stop-color="var(--primary)" stop-opacity="0" />
              </linearGradient>
            </defs>
            <line v-for="line in [0, 45, 90, 135, 180]" :key="line" x1="0" :y1="line" x2="560" :y2="line" />
            <path class="profile-rating-chart-area" :d="chartAreaPath" />
            <path class="profile-rating-chart-line" :d="chartPath" />
            <circle v-for="point in chartPoints" :key="`${point.race_id}-${point.recorded_at}`" :cx="point.x" :cy="point.y" r="3.5">
              <title>{{ point.race_name || t('profile.currentRating') }}: {{ formatRating(point.rating) }} ({{ signedChange(point.change) }})</title>
            </circle>
          </svg>
        </div>
        <p v-else class="muted">{{ t('profile.noRatingHistory') }}</p>
        <div v-if="chartPoints.length" class="profile-rating-history">
          <div v-for="point in chartPoints.slice(-6).reverse()" :key="`${point.race_id}-${point.recorded_at}-label`">
            <span>{{ point.race_name || t('profile.currentRating') }}</span>
            <strong>{{ formatRating(point.rating) }}</strong>
            <em :class="changeClass(point.change)">{{ signedChange(point.change) }}</em>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>
