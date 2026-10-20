<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { CalendarCheck, CalendarX2, ChevronLeft, ChevronRight, Flag, Plus, SlidersHorizontal } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import PaginationControls from '../components/PaginationControls.vue'
import RaceRow from '../components/RaceRow.vue'
import RaceTypeFilters from '../components/RaceTypeFilters.vue'
import EmptyState from '../ui/EmptyState.vue'
import PageHeader from '../ui/PageHeader.vue'
import Popover from '../ui/Popover.vue'
import SegmentedControl from '../ui/SegmentedControl.vue'
import SwitchToggle from '../ui/SwitchToggle.vue'
import { gameLabel, gameOptions, raceCountLabel } from '../i18nLabels'
import { loadRaceAssets } from '../raceDisplay'
import { appendRaceTypeFilters, defaultRaceTypeFilters } from '../raceFilters'
import { state } from '../store'
import { dateKeyInTimeZone } from '../timezone'

const { t } = useI18n()
const races = ref([])
const weatherSettings = ref({})
const assets = ref(null)
const championships = ref([])
const loading = ref(true)
const error = ref('')
const canManageRaces = computed(() => ['admin', 'moder'].includes(state.user?.role))
const cursor = ref(new Date())
const monthDirection = ref('next')
const selected = ref(dateKeyInTimeZone(new Date()))
const gameFilter = ref('all')
const statusFilter = ref('not_finished')
const myGamesOnly = ref(false)
const raceTypeFilters = ref(defaultRaceTypeFilters())
const filtersOpen = ref(false)
const raceSource = ref('regular')
const calendarDisplayModes = ['registration_start', 'registration_end', 'race_time']
const storedCalendarDisplayMode = localStorage.getItem('bmrl.calendarDisplayMode')
const calendarDisplayMode = ref(calendarDisplayModes.includes(storedCalendarDisplayMode) ? storedCalendarDisplayMode : 'race_time')
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
const statusOptions = computed(() => [
  { value: 'not_finished', label: t('raceFilters.notFinished') },
  { value: 'finished', label: t('raceFilters.finished') }
])
const gameChoices = computed(() => gameOptions(t, true).map((option) => ({ ...option, label: option.value === 'all' ? t('ui.common.all') : option.label })))
const displayModeOptions = computed(() => [
  { value: 'registration_start', label: t('calendar.displayRegistrationStart') },
  { value: 'registration_end', label: t('calendar.displayRegistrationEnd') },
  { value: 'race_time', label: t('calendar.displayRaceTime') }
])
const canFilterMyGames = computed(() => Boolean(state.user?.games?.length))
const activeTypeFilters = computed(() => Object.values(raceTypeFilters.value).filter(Boolean).length)
const monthKey = computed(() => `${cursor.value.getFullYear()}-${cursor.value.getMonth()}`)
const monthLabel = computed(() => cursor.value.toLocaleDateString(state.locale, { month: 'long', year: 'numeric' }))
const selectedDate = computed(() => new Date(`${selected.value}T00:00:00`))
const selectedLabel = computed(() => selectedDate.value.toLocaleDateString(state.locale, { day: 'numeric', month: 'long' }))
const selectedWeekday = computed(() => selectedDate.value.toLocaleDateString(state.locale, { weekday: 'long', year: 'numeric' }))
const calendarDateField = computed(() => ({
  registration_start: 'registration_start',
  registration_end: 'datetime_end',
  race_time: 'datetime_start'
}[calendarDisplayMode.value] || 'datetime_start'))
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
    const key = dateKeyInTimeZone(race[calendarDateField.value] || race.datetime_start)
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

function shiftMonth(delta) {
  monthDirection.value = delta > 0 ? 'next' : 'prev'
  cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + delta, 1)
}

function goToday() {
  const now = new Date()
  monthDirection.value = now > cursor.value ? 'next' : 'prev'
  cursor.value = new Date(now.getFullYear(), now.getMonth(), 1)
  selected.value = todayKey.value
}

function selectDay(day) {
  selected.value = dateKey(day)
  if (day.getMonth() !== cursor.value.getMonth()) shiftMonth(day < cursor.value ? -1 : 1)
}

async function loadRaces() {
  loading.value = true
  try {
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
    error.value = ''
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function loadChampionships() {
  try {
    championships.value = await api('/championships?limit=100')
  } catch {
    championships.value = []
  }
  if (raceSource.value !== 'regular' && !championships.value.some((championship) => String(championship.id) === raceSource.value)) {
    raceSource.value = 'regular'
  }
}

async function loadWeatherSettings() {
  weatherSettings.value = await api('/app-settings/weather').catch(() => ({}))
}

onMounted(() => {
  loadChampionships()
  loadRaces()
  loadWeatherSettings()
  loadRaceAssets().then((value) => { assets.value = value }).catch(() => {})
})
watch([gameFilter, statusFilter, myGamesOnly, raceSource, raceTypeFilters], loadRaces, { deep: true })
watch([selected, gameFilter, statusFilter, myGamesOnly, raceSource, raceTypeFilters], () => {
  selectedPage.value = 1
}, { deep: true })
watch(calendarDisplayMode, (value) => {
  localStorage.setItem('bmrl.calendarDisplayMode', value)
  selectedPage.value = 1
})
watch(selectedRaces, () => {
  if (selectedPage.value > selectedTotalPages.value) {
    selectedPage.value = selectedTotalPages.value
  }
})
</script>

<template>
  <div class="ui-page ui-shell ui-shell--wide cal">
    <PageHeader :eyebrow="t('calendarPage.eyebrow')" :title="t('nav.calendar')" :lead="t('calendarPage.lead')">
      <template #actions>
        <div class="cal__month" role="group" :aria-label="monthLabel">
          <button class="ui-btn ui-btn--outline ui-btn--icon ui-btn--sm" type="button" :aria-label="t('calendar.previousMonth')" @click="shiftMonth(-1)"><ChevronLeft :size="18" /></button>
          <Transition :name="`cal-label-${monthDirection}`" mode="out-in">
            <strong :key="monthKey" class="cal__month-label">{{ monthLabel }}</strong>
          </Transition>
          <button class="ui-btn ui-btn--outline ui-btn--icon ui-btn--sm" type="button" :aria-label="t('calendar.nextMonth')" @click="shiftMonth(1)"><ChevronRight :size="18" /></button>
          <button class="ui-btn ui-btn--ghost ui-btn--sm" type="button" @click="goToday"><CalendarCheck :size="16" />{{ t('calendarPage.today') }}</button>
        </div>
      </template>
    </PageHeader>

    <div class="cal__filters">
      <SegmentedControl v-model="statusFilter" :options="statusOptions" :aria-label="t('raceFilters.statusGroup')" />
      <SegmentedControl v-model="gameFilter" :options="gameChoices" size="sm" :aria-label="t('fields.game')" />
      <SwitchToggle v-model="myGamesOnly" :label="t('raceFilters.myGamesOnly')" :disabled="!canFilterMyGames" />
      <Popover v-model:open="filtersOpen" width="320px" :label="t('raceFilters.moreFilters')">
        <template #trigger="{ toggle }">
          <button class="ui-btn ui-btn--outline ui-btn--sm" :class="{ 'is-on': activeTypeFilters }" type="button" :aria-expanded="filtersOpen" @click="toggle">
            <SlidersHorizontal :size="15" />
            {{ activeTypeFilters ? t('calendarPage.filtersActive', { count: activeTypeFilters }) : t('calendarPage.filters') }}
          </button>
        </template>
        <div class="cal__type-filters"><RaceTypeFilters v-model="raceTypeFilters" /></div>
      </Popover>
      <div class="cal__mode">
        <span class="ui-eyebrow">{{ t('calendarPage.placeBy') }}</span>
        <SegmentedControl v-model="calendarDisplayMode" :options="displayModeOptions" size="sm" :aria-label="t('calendar.displayModeLabel')" />
      </div>
    </div>

    <p v-if="error" class="ui-alert">{{ error }}</p>

    <div class="cal__board">
      <section class="cal__grid-card ui-card" :class="{ 'is-loading': loading }">
        <div class="cal__weekdays" aria-hidden="true">
          <span v-for="label in weekdayLabels" :key="label">{{ label }}</span>
        </div>
        <Transition :name="`cal-${monthDirection}`" mode="out-in">
          <div :key="monthKey" class="cal__grid">
            <button
              v-for="(day, index) in days"
              :key="dateKey(day)"
              class="day"
              :class="{
                'is-selected': dateKey(day) === selected,
                'is-outside': day.getMonth() !== cursor.getMonth(),
                'is-today': dateKey(day) === todayKey,
                'has-races': dayRaces(day).length
              }"
              :style="{ '--i': index }"
              type="button"
              :aria-pressed="dateKey(day) === selected"
              :aria-label="`${day.toLocaleDateString(state.locale, { day: 'numeric', month: 'long' })}: ${raceCountLabel(t, state.locale, dayRaces(day).length)}`"
              @click="selectDay(day)"
            >
              <span class="day__num ui-num">{{ day.getDate() }}</span>
              <span v-if="dayGameCounts(day).length" class="day__dots">
                <span v-for="item in dayGameCounts(day)" :key="item.value" class="day__dot" :style="{ '--game': item.color }" :title="`${item.label}: ${item.count}`">
                  <i></i><small>{{ item.label }}</small><b class="ui-num">{{ item.count }}</b>
                </span>
              </span>
              <span class="day__races">
                <span v-for="race in dayRaces(day).slice(0, 2)" :key="race.id" class="day__race">
                  <small v-if="race.is_team_event">{{ t('raceFilters.teamShort') }}</small>{{ race.name }}
                </span>
                <span v-if="dayRaces(day).length > 2" class="day__more">{{ t('calendarPage.more', { count: dayRaces(day).length - 2 }) }}</span>
              </span>
            </button>
          </div>
        </Transition>
      </section>

      <aside class="cal__sources ui-card">
        <header class="ui-card__title">
          <h2>{{ t('calendar.sourceTitle') }}</h2>
          <p class="cal__hint">{{ t('calendar.sourceHint') }}</p>
        </header>
        <div class="cal__source-list">
          <button
            v-for="source in calendarSources"
            :key="source.value"
            class="source"
            :class="{ 'is-active': raceSource === source.value }"
            type="button"
            :aria-pressed="raceSource === source.value"
            @click="raceSource = source.value"
          >
            <span class="source__icon"><Flag :size="15" /></span>
            <span class="source__text">
              <strong>{{ source.title }}</strong>
              <small>{{ source.meta }}</small>
            </span>
          </button>
        </div>
        <p v-if="!championships.length" class="cal__hint">{{ t('calendar.noChampionships') }}</p>
      </aside>
    </div>

    <section class="cal__day ui-card" aria-live="polite">
      <header class="cal__day-head">
        <div>
          <p class="ui-eyebrow ui-eyebrow--accent">{{ t('calendarPage.dayEyebrow') }}</p>
          <Transition name="ui-fade" mode="out-in">
            <h2 :key="selected" class="cal__day-title ui-display">{{ selectedLabel }}<small>{{ selectedWeekday }}</small></h2>
          </Transition>
        </div>
        <div class="cal__day-meta">
          <RouterLink v-if="canManageRaces" class="ui-btn ui-btn--outline ui-btn--sm" to="/races/new"><Plus :size="15" />{{ t('calendarPage.addRace') }}</RouterLink>
          <span class="ui-chip ui-chip--blue">{{ raceCountLabel(t, state.locale, selectedRaces.length) }}</span>
          <span v-for="item in selectedGameCounts" :key="item.value" class="ui-chip cal__game-chip" :style="{ '--game': item.color }">
            <i></i>{{ item.label }} · {{ item.count }}
          </span>
        </div>
      </header>

      <Transition name="ui-fade" mode="out-in">
        <div v-if="pagedSelectedRaces.length" :key="`${selected}-${selectedPage}`" class="cal__list">
          <RaceRow v-for="(race, index) in pagedSelectedRaces" :key="race.id" v-reveal="{ delay: index * 60, y: 12, blur: 0 }" :race="race" :assets="assets" :weather-settings="weatherSettings" />
        </div>
        <EmptyState v-else-if="loading" key="loading" loading :title="t('ui.common.loading')" compact />
        <EmptyState v-else key="empty" :icon="CalendarX2" :title="t('calendar.noRacesTitle')" :text="t('calendar.noRacesDescription')" compact />
      </Transition>
      <PaginationControls v-model:page="selectedPage" :page-size="selectedPageSize" :total-items="selectedRaces.length" />
    </section>
  </div>
</template>

<style scoped>
.cal__month {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cal__month-label {
  min-width: 150px;
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 700;
  text-align: center;
  text-transform: uppercase;
}

.cal__filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
}

.cal__filters .is-on {
  border-color: var(--c-blue-line);
  color: var(--c-accent-text);
}

.cal__type-filters {
  padding: 6px;
}

.cal__mode {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-left: auto;
}

.cal__board {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 320px);
  gap: clamp(14px, 1.6vw, 20px);
  align-items: start;
}

.cal__grid-card {
  gap: 10px;
  overflow: hidden;
  transition: opacity var(--dur-2);
}

.cal__grid-card.is-loading {
  opacity: 0.6;
}

.cal__weekdays,
.cal__grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 6px;
}

.cal__weekdays span {
  padding: 0 8px;
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.day {
  position: relative;
  display: grid;
  align-content: start;
  gap: 6px;
  min-width: 0;
  min-height: 104px;
  padding: 8px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  background: var(--c-sunken);
  color: var(--c-text);
  cursor: pointer;
  text-align: left;
  animation: day-in 420ms var(--ease-out) both;
  animation-delay: calc(var(--i) * 8ms);
  transition: border-color var(--dur-2), background-color var(--dur-2), transform var(--dur-3) var(--ease-ios);
}

@keyframes day-in {
  from {
    opacity: 0;
    transform: scale(0.96);
  }
}

.day:hover {
  border-color: var(--c-blue-line);
  transform: translateY(-2px);
}

.day.is-outside {
  opacity: 0.4;
}

.day.has-races {
  background: color-mix(in srgb, var(--bm-blue) 8%, var(--c-sunken));
}

.day.is-selected {
  border-color: var(--bm-blue);
  background: color-mix(in srgb, var(--bm-blue) 18%, var(--c-sunken));
  box-shadow: 0 0 0 1px var(--bm-blue), var(--shadow-blue);
}

.day__num {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-size: 13.5px;
  font-weight: 600;
}

.day.is-today .day__num {
  background: var(--bm-blue);
  color: #fff;
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--bm-blue) 25%, transparent);
}

.day__dots {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.day__dot {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px 2px 4px;
  border-radius: var(--r-pill);
  background: color-mix(in srgb, var(--game) 16%, transparent);
  font-size: 10px;
}

.day__dot i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--game);
}

.day__dot small {
  color: var(--c-text-2);
  font-family: var(--font-mono);
  font-size: 9.5px;
}

.day__dot b {
  font-size: 10px;
}

.day__races {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.day__race {
  overflow: hidden;
  padding: 3px 6px;
  border-radius: 6px;
  background: color-mix(in srgb, var(--c-text) 7%, transparent);
  font-size: 11px;
  font-weight: 550;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.day__race small {
  margin-right: 4px;
  color: var(--c-accent-text);
  font-family: var(--font-mono);
  font-size: 9px;
}

.day__more {
  color: var(--c-text-3);
  font-size: 11px;
}

.cal__sources {
  position: sticky;
  top: calc(var(--header-h) + 20px);
}

.cal__hint {
  margin: 0;
  color: var(--c-text-3);
  font-size: 12.5px;
}

.cal__source-list {
  display: grid;
  gap: 6px;
  max-height: 460px;
  overflow-y: auto;
}

.source {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  background: var(--c-sunken);
  color: var(--c-text);
  cursor: pointer;
  text-align: left;
  transition: border-color var(--dur-2), background-color var(--dur-2);
}

.source:hover {
  border-color: var(--c-blue-line);
}

.source.is-active {
  border-color: var(--bm-blue);
  background: var(--c-blue-soft);
}

.source__icon {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--c-text) 7%, transparent);
  color: var(--c-text-2);
}

.source.is-active .source__icon {
  background: var(--bm-blue);
  color: #fff;
}

.source__text {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.source__text strong {
  overflow: hidden;
  font-size: 13.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source__text small {
  overflow: hidden;
  color: var(--c-text-3);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cal__day-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
}

.cal__day-head > div:first-child {
  display: grid;
  gap: 8px;
}

.cal__day-title {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 14px;
  color: var(--c-text);
  font-size: clamp(22px, 2.6vw, 32px);
}

.cal__day-title small {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.12em;
}

.cal__day-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.cal__game-chip i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--game);
}

.cal__list {
  display: grid;
  gap: 10px;
}

/* Month change: the grid slides in from the side you navigated to. */
.cal-next-enter-active,
.cal-prev-enter-active,
.cal-next-leave-active,
.cal-prev-leave-active,
.cal-label-next-enter-active,
.cal-label-prev-enter-active,
.cal-label-next-leave-active,
.cal-label-prev-leave-active {
  transition: opacity 220ms var(--ease-out), transform 360ms var(--ease-ios), filter 220ms;
}

.cal-next-enter-from,
.cal-prev-leave-to,
.cal-label-next-enter-from,
.cal-label-prev-leave-to {
  opacity: 0;
  filter: blur(4px);
  transform: translateX(24px);
}

.cal-next-leave-to,
.cal-prev-enter-from,
.cal-label-next-leave-to,
.cal-label-prev-enter-from {
  opacity: 0;
  filter: blur(4px);
  transform: translateX(-24px);
}

@media (max-width: 1100px) {
  .cal__board {
    grid-template-columns: minmax(0, 1fr);
  }

  .cal__sources {
    position: static;
  }

  .cal__mode {
    margin-left: 0;
  }
}

@media (max-width: 760px) {
  .cal__grid-card {
    padding: 10px;
  }

  .cal__weekdays,
  .cal__grid {
    gap: 3px;
  }

  .cal__weekdays span {
    padding: 0;
    font-size: 9.5px;
    letter-spacing: 0.04em;
    text-align: center;
  }

  .day {
    justify-items: center;
    min-height: 54px;
    padding: 4px 2px;
    border-radius: 12px;
  }

  .day__races,
  .day__dot small,
  .day__dot b {
    display: none;
  }

  .day__dot {
    padding: 0;
    background: none;
  }

  .cal__month-label {
    min-width: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .day {
    animation: none;
  }

  .cal-next-enter-active,
  .cal-prev-enter-active,
  .cal-next-leave-active,
  .cal-prev-leave-active,
  .cal-label-next-enter-active,
  .cal-label-prev-enter-active,
  .cal-label-next-leave-active,
  .cal-label-prev-leave-active {
    transition: none;
  }
}
</style>
