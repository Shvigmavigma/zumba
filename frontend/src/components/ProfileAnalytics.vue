<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { animate, createDrawable } from 'animejs'
import { Car, ChevronRight, Flag, LineChart, Timer } from 'lucide-vue-next'
import { api } from '../api'
import EmptyState from '../ui/EmptyState.vue'
import SegmentedControl from '../ui/SegmentedControl.vue'
import { prefersReducedMotion } from '../ui/motion/env'
import { RATING_GAMES, formatRating } from '../pilotDisplay'
import { formatDateTime as formatDateTimeInZone } from '../timezone'

const props = defineProps({
  userId: { type: [Number, String], required: true },
  favoriteCar: { type: String, default: '' },
  user: { type: Object, default: null }
})
const emit = defineEmits(['loaded'])

const { t } = useI18n()
const CHART_W = 560
const CHART_H = 180
const loading = ref(false)
const error = ref('')
const analytics = ref({ best_laps: [], recent_results: [], rating_history: [] })
const activeTab = ref('laps')
const selectedGame = ref('all')
const hoveredPoint = ref(null)
const chartLine = ref(null)

const tabs = computed(() => [
  { value: 'laps', label: t('statsPanel.laps'), icon: Timer },
  { value: 'results', label: t('statsPanel.results'), icon: Flag },
  { value: 'rating', label: t('statsPanel.rating'), icon: LineChart }
])
const gameChoices = computed(() => {
  const games = new Set([...analytics.value.best_laps.map((item) => item.game), ...analytics.value.recent_results.map((item) => item.game), ...analytics.value.rating_history.map((item) => item.game)])
  return [{ value: 'all', label: t('statsPanel.allGames') }, ...RATING_GAMES.filter((game) => games.has(game)).map((game) => ({ value: game, label: gameLabel(game) }))]
})
const activeFavoriteCar = computed(() => props.favoriteCar || analytics.value.favorite_car || '')
const bestLaps = computed(() => analytics.value.best_laps.filter((item) => selectedGame.value === 'all' || item.game === selectedGame.value))
const recentResults = computed(() => analytics.value.recent_results.filter((item) => selectedGame.value === 'all' || item.game === selectedGame.value).slice(0, 12))
const ratingHistory = computed(() => analytics.value.rating_history.filter((item) => selectedGame.value === 'all' || item.game === selectedGame.value).slice(-30))
const chartPoints = computed(() => {
  const points = ratingHistory.value
  if (!points.length) return []
  const values = points.map((item) => Number(item.rating) || 0)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const spread = Math.max(20, max - min)
  return points.map((item, index) => ({
    ...item,
    x: points.length === 1 ? CHART_W / 2 : (index / (points.length - 1)) * CHART_W,
    y: CHART_H - ((Number(item.rating) - (min - spread * 0.15)) / (spread * 1.3)) * CHART_H
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
    const controlOne = { x: current.x + (next.x - previous.x) / 6, y: current.y + (next.y - previous.y) / 6 }
    const controlTwo = { x: next.x - (following.x - current.x) / 6, y: next.y - (following.y - current.y) / 6 }
    path += ` C ${controlOne.x.toFixed(2)} ${controlOne.y.toFixed(2)}, ${controlTwo.x.toFixed(2)} ${controlTwo.y.toFixed(2)}, ${next.x.toFixed(2)} ${next.y.toFixed(2)}`
  }
  return path
}

const chartPath = computed(() => smoothChartPath(chartPoints.value))
const chartAreaPath = computed(() => {
  const points = chartPoints.value
  if (!points.length) return ''
  return `${chartPath.value} L ${points[points.length - 1].x.toFixed(2)} ${CHART_H} L ${points[0].x.toFixed(2)} ${CHART_H} Z`
})
const chartMin = computed(() => (chartPoints.value.length ? Math.min(...chartPoints.value.map((item) => item.rating)) : 0))
const chartMax = computed(() => (chartPoints.value.length ? Math.max(...chartPoints.value.map((item) => item.rating)) : 0))

function chartTooltipStyle(point) {
  const left = Math.min(92, Math.max(8, (point.x / CHART_W) * 100))
  const top = Math.min(80, Math.max(8, (point.y / CHART_H) * 100))
  return { left: `${left}%`, top: `${top}%` }
}

function chartPointLabel(point) {
  return `${point.race_name || t('profile.currentRating')}: ${formatRating(point.rating)} (${signedChange(point.change)})`
}

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

/** Draws the rating line from left to right whenever the chart is shown. */
async function drawChart() {
  if (activeTab.value !== 'rating' || prefersReducedMotion()) return
  await nextTick()
  if (!chartLine.value) return
  const [line] = createDrawable(chartLine.value)
  animate(line, { draw: ['0 0', '0 1'], duration: 1400, ease: 'inOutCubic' })
}

async function load() {
  if (!props.userId) return
  loading.value = true
  error.value = ''
  try {
    analytics.value = await api(`/users/${props.userId}/analytics`)
    emit('loaded', analytics.value)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.userId, load)
watch([activeTab, selectedGame], drawChart)
</script>

<template>
  <section class="stats ui-card">
    <header class="stats__head">
      <div class="ui-card__title">
        <p class="ui-eyebrow ui-eyebrow--accent">{{ t('statsPanel.eyebrow') }}</p>
        <h2>{{ t('statsPanel.title') }}</h2>
      </div>
      <span v-if="activeFavoriteCar" class="ui-chip ui-chip--blue stats__car"><Car :size="13" />{{ activeFavoriteCar }}</span>
    </header>

    <div class="stats__controls">
      <SegmentedControl v-model="activeTab" :options="tabs" :aria-label="t('statsPanel.title')" />
      <SegmentedControl v-if="gameChoices.length > 2" v-model="selectedGame" :options="gameChoices" size="sm" :aria-label="t('fields.game')" />
    </div>

    <EmptyState v-if="loading" loading :title="t('ui.common.loading')" compact />
    <p v-else-if="error" class="ui-alert">{{ error }}</p>
    <Transition v-else name="ui-fade" mode="out-in">
      <div v-if="activeTab === 'laps'" key="laps" class="stats__panel">
        <ul v-if="bestLaps.length" class="laps">
          <li v-for="(item, index) in bestLaps" :key="`${item.game}-${item.track}`" v-reveal="{ delay: index * 50, y: 10, blur: 0 }">
            <RouterLink class="laps__row" :to="`/races/${item.race_id}`">
              <span class="laps__track">
                <strong>{{ item.track }}</strong>
                <small>{{ gameLabel(item.game) }} · {{ item.car_model || t('common.none') }}</small>
              </span>
              <span class="ui-chip" :class="item.session === 'qualification' ? 'ui-chip--amber' : 'ui-chip--blue'">{{ item.session === 'qualification' ? t('statsPanel.qualification') : t('statsPanel.race') }}</span>
              <span class="laps__time ui-num">{{ formatLap(item.best_lap_ms) }}</span>
              <ChevronRight class="laps__go" :size="16" />
            </RouterLink>
          </li>
        </ul>
        <EmptyState v-else :icon="Timer" :title="t('profile.noBestLaps')" compact />
      </div>

      <div v-else-if="activeTab === 'results'" key="results" class="stats__panel">
        <ul v-if="recentResults.length" class="results">
          <li v-for="(item, index) in recentResults" :key="`${item.race_id}-${item.recorded_at}`" v-reveal="{ delay: index * 50, y: 10, blur: 0 }">
            <RouterLink class="results__row" :to="`/races/${item.race_id}`">
              <span class="ui-pos" :class="item.position && item.position <= 3 ? `ui-pos--${item.position}` : ''">{{ item.position ? `P${item.position}` : '—' }}</span>
              <span class="results__main">
                <strong>{{ item.race_name }}</strong>
                <small>{{ item.track }} · {{ formatDate(item.recorded_at) }} · {{ gameLabel(item.game) }}</small>
              </span>
              <span class="results__car">{{ item.car_model || t('common.none') }}</span>
              <span class="results__finish ui-num">{{ formatFinish(item.finish_ms) }}</span>
              <span class="results__delta ui-num" :class="changeClass(item.rating_change)">{{ item.rating_change === null ? '—' : signedChange(item.rating_change) }}</span>
            </RouterLink>
          </li>
        </ul>
        <EmptyState v-else :icon="Flag" :title="t('profile.noRecentResults')" compact />
      </div>

      <div v-else key="rating" class="stats__panel">
        <template v-if="chartPoints.length">
          <div class="chart">
            <div class="chart__scale ui-num"><span>{{ chartMax }}</span><span>{{ chartMin }}</span></div>
            <div class="chart__canvas">
              <svg class="chart__svg" :viewBox="`0 0 ${CHART_W} ${CHART_H}`" preserveAspectRatio="none" role="img" :aria-label="t('profile.statsRatingChart')">
                <defs>
                  <linearGradient id="stats-rating-fill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#1652d8" stop-opacity="0.38" />
                    <stop offset="100%" stop-color="#1652d8" stop-opacity="0" />
                  </linearGradient>
                  <linearGradient id="stats-rating-line" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stop-color="#3c74f6" />
                    <stop offset="100%" stop-color="#4fd8ea" />
                  </linearGradient>
                </defs>
                <line v-for="line in [0, 45, 90, 135, 180]" :key="line" class="chart__grid" x1="0" :y1="line" :x2="CHART_W" :y2="line" />
                <path class="chart__area" :d="chartAreaPath" />
                <path ref="chartLine" class="chart__line" :d="chartPath" />
              </svg>
              <button
                v-for="point in chartPoints"
                :key="`${point.race_id}-${point.recorded_at}`"
                class="chart__point"
                :class="{ 'is-active': hoveredPoint === point }"
                type="button"
                :style="{ left: `${(point.x / CHART_W) * 100}%`, top: `${(point.y / CHART_H) * 100}%` }"
                :aria-label="chartPointLabel(point)"
                @mouseenter="hoveredPoint = point"
                @mouseleave="hoveredPoint = null"
                @focus="hoveredPoint = point"
                @blur="hoveredPoint = null"
              ></button>
              <Transition name="ui-pop">
                <div v-if="hoveredPoint" class="chart__tip" :style="chartTooltipStyle(hoveredPoint)" role="status">
                  <strong class="ui-num">{{ formatRating(hoveredPoint.rating) }}</strong>
                  <span>{{ hoveredPoint.race_name || t('profile.currentRating') }}</span>
                  <em class="ui-num" :class="changeClass(hoveredPoint.change)">{{ signedChange(hoveredPoint.change) }}</em>
                </div>
              </Transition>
            </div>
          </div>
          <p class="stats__hint">{{ t('statsPanel.chartHint') }}</p>
          <div class="history">
            <p class="ui-eyebrow">{{ t('statsPanel.lastRaces') }}</p>
            <div v-for="point in chartPoints.slice(-6).reverse()" :key="`${point.race_id}-${point.recorded_at}-label`" class="history__row">
              <span>{{ point.race_name || t('profile.currentRating') }}</span>
              <strong class="ui-num">{{ formatRating(point.rating) }}</strong>
              <em class="ui-num" :class="changeClass(point.change)">{{ signedChange(point.change) }}</em>
            </div>
          </div>
        </template>
        <EmptyState v-else :icon="LineChart" :title="t('profile.noRatingHistory')" compact />
      </div>
    </Transition>
  </section>
</template>

<style scoped>
.stats__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
}

.stats__car {
  text-transform: none;
  letter-spacing: 0;
}

.stats__controls {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 10px;
}

.stats__panel {
  display: grid;
  gap: 14px;
}

.stats__hint {
  margin: 0;
  color: var(--c-text-3);
  font-size: 12.5px;
}

.laps,
.results {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.laps__row,
.results__row {
  display: grid;
  align-items: center;
  gap: 14px;
  padding: 12px 14px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  background: var(--c-sunken);
  color: var(--c-text);
  text-decoration: none;
  transition: border-color var(--dur-2), transform var(--dur-3) var(--ease-ios), background-color var(--dur-2);
}

.laps__row:hover,
.results__row:hover {
  border-color: var(--c-blue-line);
  background: var(--c-blue-soft);
  transform: translateX(3px);
}

.laps__row {
  grid-template-columns: minmax(0, 1fr) auto 110px 18px;
}

.laps__track,
.results__main {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.laps__track strong,
.results__main strong {
  overflow: hidden;
  font-size: 14.5px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.laps__track small,
.results__main small {
  overflow: hidden;
  color: var(--c-text-3);
  font-size: 12.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.laps__time {
  color: #c79bff;
  font-size: 17px;
  font-weight: 600;
  text-align: right;
}

.laps__go {
  color: var(--c-text-3);
}

.results__row {
  grid-template-columns: 44px minmax(0, 1fr) minmax(0, 180px) 80px 56px;
}

.results__car {
  overflow: hidden;
  color: var(--c-text-2);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.results__finish {
  color: var(--c-text);
  text-align: right;
}

.results__delta {
  padding: 3px 6px;
  border-radius: 7px;
  color: var(--c-text-3);
  font-size: 13px;
  text-align: center;
}

.is-positive {
  background: color-mix(in srgb, var(--bm-green) 14%, transparent);
  color: color-mix(in srgb, var(--bm-green) 85%, var(--c-text));
}

.is-negative {
  background: color-mix(in srgb, var(--bm-red) 14%, transparent);
  color: color-mix(in srgb, var(--bm-red) 85%, var(--c-text));
}

.chart {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 12px;
}

.chart__scale {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  color: var(--c-text-3);
  font-size: 11px;
}

.chart__canvas {
  position: relative;
  height: 220px;
}

.chart__svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}

.chart__grid {
  stroke: var(--c-line);
  stroke-dasharray: 3 5;
  vector-effect: non-scaling-stroke;
}

.chart__area {
  fill: url(#stats-rating-fill);
}

.chart__line {
  fill: none;
  stroke: url(#stats-rating-line);
  stroke-linecap: round;
  stroke-width: 3;
  vector-effect: non-scaling-stroke;
  filter: drop-shadow(0 4px 10px rgba(22, 82, 216, 0.5));
}

.chart__point {
  position: absolute;
  width: 12px;
  height: 12px;
  margin: -6px 0 0 -6px;
  padding: 0;
  border: 2px solid var(--c-bg);
  border-radius: 50%;
  background: var(--bm-cyan);
  cursor: pointer;
  transition: transform var(--dur-2) var(--ease-spring), box-shadow var(--dur-2);
}

.chart__point:hover,
.chart__point.is-active,
.chart__point:focus-visible {
  box-shadow: 0 0 0 6px color-mix(in srgb, var(--bm-cyan) 30%, transparent);
  transform: scale(1.35);
}

.chart__tip {
  position: absolute;
  z-index: 2;
  display: grid;
  gap: 2px;
  min-width: 150px;
  padding: 10px 12px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-md);
  background: var(--c-surface-2);
  box-shadow: var(--shadow-2);
  pointer-events: none;
  transform: translate(-50%, calc(-100% - 14px));
  -webkit-backdrop-filter: var(--glass-filter);
  backdrop-filter: var(--glass-filter);
}

.chart__tip strong {
  font-size: 18px;
}

.chart__tip span {
  color: var(--c-text-2);
  font-size: 12px;
}

.chart__tip em {
  justify-self: start;
  padding: 1px 6px;
  border-radius: 6px;
  font-size: 12px;
  font-style: normal;
}

.history {
  display: grid;
  gap: 6px;
}

.history__row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto 52px;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--c-line);
  font-size: 13.5px;
}

.history__row span {
  overflow: hidden;
  color: var(--c-text-2);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history__row em {
  padding: 2px 6px;
  border-radius: 6px;
  font-style: normal;
  text-align: center;
}

@media (max-width: 760px) {
  .laps__row {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .laps__row .ui-chip,
  .laps__go {
    display: none;
  }

  .results__row {
    grid-template-columns: 40px minmax(0, 1fr) 50px;
  }

  .results__car,
  .results__finish {
    display: none;
  }
}
</style>
