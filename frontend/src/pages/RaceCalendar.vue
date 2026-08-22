<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import PaginationControls from '../components/PaginationControls.vue'
import RaceTypeFilters from '../components/RaceTypeFilters.vue'
import { gameLabel, gameOptions, isExternalRace, raceCountLabel, raceOpenHref } from '../i18nLabels'
import { appendRaceTypeFilters, defaultRaceTypeFilters } from '../raceFilters'
import { state } from '../store'
import { dateKeyInTimeZone, formatTimeOnly } from '../timezone'

const { t } = useI18n()
const races = ref([])
const championships = ref([])
const cursor = ref(new Date())
const selected = ref(dateKeyInTimeZone(new Date()))
const gameFilter = ref('all')
const statusFilter = ref('not_finished')
const myGamesOnly = ref(false)
const raceTypeFilters = ref(defaultRaceTypeFilters())
const raceSource = ref('regular')
const selectedPage = ref(1)
const selectedPageSize = 6
const gameCountMeta = [
  { value: 'AC', color: '#B32000' },
  { value: 'ACC', color: '#FF4A21' },
  { value: 'iRacing', color: '#3700EB' },
  { value: 'LMU', color: '#0095EB' }
]

function dateKey(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const days = computed(() => {
  const year = cursor.value.getFullYear()
  const month = cursor.value.getMonth()
  const first = new Date(year, month, 1)
  const start = new Date(first)
  start.setDate(first.getDate() - ((first.getDay() + 6) % 7))

  const last = new Date(year, month + 1, 0)
  const end = new Date(last)
  end.setDate(last.getDate() + (6 - ((last.getDay() + 6) % 7)))
  const totalDays = Math.round((end - start) / 86400000) + 1

  return Array.from({ length: totalDays }, (_, index) => {
    const date = new Date(start)
    date.setDate(start.getDate() + index)
    return date
  })
})

const todayKey = computed(() => dateKeyInTimeZone(new Date()))
const raceGameOptions = computed(() => gameOptions(t, true))
const canFilterMyGames = computed(() => Boolean(state.user?.games?.length))
const monthLabel = computed(() => cursor.value.toLocaleDateString(state.locale, { month: 'long', year: 'numeric' }))
const selectedLabel = computed(() => new Date(`${selected.value}T00:00:00`).toLocaleDateString(state.locale, { day: 'numeric', month: 'long', year: 'numeric' }))
const calendarSources = computed(() => [
  {
    value: 'regular',
    title: t('calendar.regularRaces'),
    meta: t('calendar.regularRacesHint')
  },
  ...championships.value.map((championship) => ({
    value: String(championship.id),
    title: championship.name,
    meta: `${gameLabel(t, championship.game)} - ${championship.classes?.join(', ') || t('common.none')}`
  }))
])
const weekdayLabels = computed(() => {
  const monday = new Date(2026, 0, 5)
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(monday)
    date.setDate(monday.getDate() + index)
    return date.toLocaleDateString(state.locale, { weekday: 'short' }).replace('.', '')
  })
})
const racesByDate = computed(() => {
  const map = new Map()
  races.value.forEach((race) => {
    const key = dateKeyInTimeZone(race.datetime_start)
    const items = map.get(key) || []
    items.push(race)
    map.set(key, items)
  })
  return map
})
const selectedRaces = computed(() => racesByDate.value.get(selected.value) || [])
const selectedGameCounts = computed(() => raceGameCounts(selectedRaces.value))
const selectedTotalPages = computed(() => Math.max(1, Math.ceil(selectedRaces.value.length / selectedPageSize)))
const pagedSelectedRaces = computed(() => selectedRaces.value.slice((selectedPage.value - 1) * selectedPageSize, selectedPage.value * selectedPageSize))

function dayRaces(day) {
  return racesByDate.value.get(dateKey(day)) || []
}

function raceGameCounts(items) {
  const counts = new Map()
  items.forEach((race) => counts.set(race.game, (counts.get(race.game) || 0) + 1))
  return gameCountMeta
    .map((item) => ({ ...item, label: gameLabel(t, item.value), count: counts.get(item.value) || 0 }))
    .filter((item) => item.count > 0)
}

function dayGameCounts(day) {
  return raceGameCounts(dayRaces(day))
}

function formatRaceTime(value) {
  return formatTimeOnly(value)
}

function shiftMonth(delta) {
  cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + delta, 1)
}

async function loadRaces() {
  const params = new URLSearchParams({ limit: '100', game_filter: gameFilter.value, status_filter: statusFilter.value })
  if (raceSource.value !== 'regular') {
    params.set('include_championship', 'true')
    params.set('championship_id', raceSource.value)
  }
  if (myGamesOnly.value && canFilterMyGames.value) {
    params.set('my_games_only', 'true')
  }
  appendRaceTypeFilters(params, raceTypeFilters.value)
  races.value = await api(`/races?${params.toString()}`)
}

async function loadChampionships() {
  championships.value = await api('/championships?limit=100')
  if (raceSource.value !== 'regular' && !championships.value.some((championship) => String(championship.id) === raceSource.value)) {
    raceSource.value = 'regular'
  }
}

onMounted(() => {
  loadChampionships()
  loadRaces()
})
watch([gameFilter, statusFilter, myGamesOnly, raceSource, raceTypeFilters], loadRaces)
watch([selected, gameFilter, statusFilter, myGamesOnly, raceSource, raceTypeFilters], () => {
  selectedPage.value = 1
})
watch(selectedRaces, () => {
  if (selectedPage.value > selectedTotalPages.value) {
    selectedPage.value = selectedTotalPages.value
  }
})
</script>

<template>
  <section class="section calendar-page">
    <div class="section-header calendar-header">
      <h1>{{ t('nav.calendar') }}</h1>
      <div class="toolbar calendar-controls">
        <button class="icon-button" type="button" :title="t('calendar.previousMonth')" @click="shiftMonth(-1)"><ChevronLeft :size="18" /></button>
        <strong>{{ monthLabel }}</strong>
        <button class="icon-button" type="button" :title="t('calendar.nextMonth')" @click="shiftMonth(1)"><ChevronRight :size="18" /></button>
      </div>
    </div>

    <div class="race-filter-bar card">
      <div class="race-status-toggle" role="group" :aria-label="t('raceFilters.statusGroup')">
        <button type="button" :class="{ active: statusFilter === 'not_finished' }" @click="statusFilter = 'not_finished'">
          {{ t('raceFilters.notFinished') }}
        </button>
        <button type="button" :class="{ active: statusFilter === 'finished' }" @click="statusFilter = 'finished'">
          {{ t('raceFilters.finished') }}
        </button>
      </div>
      <label class="field">
        <span>{{ t('fields.game') }}</span>
        <select v-model="gameFilter">
          <option v-for="option in raceGameOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
      </label>
      <label class="toggle-field">
        <input v-model="myGamesOnly" type="checkbox" :disabled="!canFilterMyGames" />
        <span>{{ t('raceFilters.myGamesOnly') }}</span>
      </label>
      <RaceTypeFilters v-model="raceTypeFilters" />
    </div>

    <div class="calendar-board-layout">
      <div class="calendar-shell card">
        <div class="calendar-weekdays">
          <span v-for="label in weekdayLabels" :key="label">{{ label }}</span>
        </div>
        <div class="calendar-grid">
          <button
            v-for="day in days"
            :key="dateKey(day)"
            class="calendar-day"
            :class="{
              active: dateKey(day) === selected,
              muted: day.getMonth() !== cursor.getMonth(),
              today: dateKey(day) === todayKey,
              'has-races': dayRaces(day).length
            }"
            type="button"
            @click="selected = dateKey(day)"
          >
            <span class="calendar-date-row">
              <strong>{{ day.getDate() }}</strong>
            </span>
            <span v-if="dayGameCounts(day).length" class="calendar-game-counts">
              <span
                v-for="item in dayGameCounts(day)"
                :key="item.value"
                class="calendar-game-count"
                :style="{ '--calendar-game-color': item.color }"
              >
                <small>{{ item.label }}</small>
                <strong>{{ item.count }}</strong>
              </span>
            </span>
            <span class="calendar-race-stack">
              <span v-for="race in dayRaces(day).slice(0, 2)" :key="race.id" class="pill calendar-race-pill">
                <small v-if="race.is_team_event" class="calendar-team-mark">{{ t('raceFilters.teamShort') }}</small>
                {{ race.name }}
              </span>
              <span v-if="dayRaces(day).length > 2" class="calendar-more">+{{ dayRaces(day).length - 2 }}</span>
            </span>
          </button>
        </div>
      </div>

      <aside class="calendar-source-panel card">
        <div class="calendar-source-head">
          <strong>{{ t('calendar.sourceTitle') }}</strong>
          <span>{{ t('calendar.sourceHint') }}</span>
        </div>
        <div class="calendar-source-list">
          <button
            v-for="source in calendarSources"
            :key="source.value"
            class="calendar-source-option"
            :class="{ active: raceSource === source.value }"
            type="button"
            @click="raceSource = source.value"
          >
            <strong>{{ source.title }}</strong>
            <span>{{ source.meta }}</span>
          </button>
        </div>
        <p v-if="!championships.length" class="muted calendar-source-empty">{{ t('calendar.noChampionships') }}</p>
      </aside>
    </div>

    <section class="section selected-races">
      <div class="section-header">
        <h2>{{ selectedLabel }}</h2>
        <div class="calendar-selection-summary">
          <span class="pill calendar-selection-count">{{ raceCountLabel(t, state.locale, selectedRaces.length) }}</span>
          <span v-if="selectedGameCounts.length" class="calendar-game-counts selected-calendar-game-counts">
            <span
              v-for="item in selectedGameCounts"
              :key="item.value"
              class="calendar-game-count"
              :style="{ '--calendar-game-color': item.color }"
            >
              <small>{{ item.label }}</small>
              <strong>{{ item.count }}</strong>
            </span>
          </span>
        </div>
      </div>
      <div class="race-list">
        <article v-for="race in pagedSelectedRaces" :key="race.id" class="card race-item">
          <div>
            <div class="race-item-title-row">
              <h3>{{ race.name }}</h3>
              <span v-if="race.is_team_event" class="status-badge race-team-badge">{{ t('raceFilters.teamBadge') }}</span>
            </div>
            <p class="muted">
              {{ race.game === 'LMU'
                ? gameLabel(t, race.game)
                : `${gameLabel(t, race.game)} - ${race.track} - ${race.car_class} - ${formatRaceTime(race.datetime_start)}` }}
            </p>
          </div>
          <a v-if="isExternalRace(race)" class="button" :href="raceOpenHref(race)">{{ t('common.open') }}</a>
          <RouterLink v-else class="button" :to="raceOpenHref(race)">{{ t('common.open') }}</RouterLink>
        </article>
        <div v-if="!selectedRaces.length" class="calendar-empty">
          <strong>{{ t('calendar.noRacesTitle') }}</strong>
          <p class="muted">{{ t('calendar.noRacesDescription') }}</p>
        </div>
      </div>
      <PaginationControls v-model:page="selectedPage" :page-size="selectedPageSize" :total-items="selectedRaces.length" />
    </section>
  </section>
</template>
