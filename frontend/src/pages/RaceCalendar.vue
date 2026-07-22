<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { gameLabel, gameOptions, raceCountLabel } from '../i18nLabels'
import { state } from '../store'

const { t } = useI18n()
const races = ref([])
const cursor = ref(new Date())
const selected = ref(dateKey(new Date()))
const gameFilter = ref('all')
const myGamesOnly = ref(false)

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

const todayKey = dateKey(new Date())
const raceGameOptions = computed(() => gameOptions(t, true))
const canFilterMyGames = computed(() => Boolean(state.user?.games?.length))
const monthLabel = computed(() => cursor.value.toLocaleDateString(state.locale, { month: 'long', year: 'numeric' }))
const selectedLabel = computed(() => new Date(`${selected.value}T00:00:00`).toLocaleDateString(state.locale, { day: 'numeric', month: 'long', year: 'numeric' }))
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
    const key = race.datetime_start.slice(0, 10)
    const items = map.get(key) || []
    items.push(race)
    map.set(key, items)
  })
  return map
})
const selectedRaces = computed(() => racesByDate.value.get(selected.value) || [])

function dayRaces(day) {
  return racesByDate.value.get(dateKey(day)) || []
}

function shiftMonth(delta) {
  cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + delta, 1)
}

async function loadRaces() {
  const params = new URLSearchParams({ limit: '100', game_filter: gameFilter.value })
  if (myGamesOnly.value && canFilterMyGames.value) {
    params.set('my_games_only', 'true')
  }
  races.value = await api(`/races?${params.toString()}`)
}

onMounted(loadRaces)
watch([gameFilter, myGamesOnly], loadRaces)
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
    </div>

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
            <span v-if="dayRaces(day).length" class="calendar-count">{{ dayRaces(day).length }}</span>
          </span>
          <span class="calendar-race-stack">
            <span v-for="race in dayRaces(day).slice(0, 2)" :key="race.id" class="pill calendar-race-pill">{{ race.name }}</span>
            <span v-if="dayRaces(day).length > 2" class="calendar-more">+{{ dayRaces(day).length - 2 }}</span>
          </span>
        </button>
      </div>
    </div>

    <section class="section selected-races">
      <div class="section-header">
        <h2>{{ selectedLabel }}</h2>
        <span class="pill calendar-selection-count">{{ raceCountLabel(t, state.locale, selectedRaces.length) }}</span>
      </div>
      <div class="race-list">
        <article v-for="race in selectedRaces" :key="race.id" class="card race-item">
          <div>
            <h3>{{ race.name }}</h3>
            <p class="muted">{{ gameLabel(t, race.game) }} - {{ race.track }} - {{ race.car_class }} - {{ new Date(race.datetime_start).toLocaleTimeString(state.locale, { hour: '2-digit', minute: '2-digit' }) }}</p>
          </div>
          <RouterLink class="button" :to="`/races/${race.id}`">{{ t('common.open') }}</RouterLink>
        </article>
        <div v-if="!selectedRaces.length" class="calendar-empty">
          <strong>{{ t('calendar.noRacesTitle') }}</strong>
          <p class="muted">{{ t('calendar.noRacesDescription') }}</p>
        </div>
      </div>
    </section>
  </section>
</template>
