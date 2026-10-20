<script setup>
// Race schedule on the home page with the original filters: status, game,
// "my games only" and the six race-property checkboxes. Upcoming races are
// listed soonest first; finished races newest first.
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { CalendarSearch, Plus, SlidersHorizontal } from 'lucide-vue-next'
import { api } from '../../api'
import PaginationControls from '../../components/PaginationControls.vue'
import RaceRow from '../../components/RaceRow.vue'
import RaceTypeFilters from '../../components/RaceTypeFilters.vue'
import EmptyState from '../../ui/EmptyState.vue'
import Popover from '../../ui/Popover.vue'
import SegmentedControl from '../../ui/SegmentedControl.vue'
import SwitchToggle from '../../ui/SwitchToggle.vue'
import { gameOptions } from '../../i18nLabels'
import { loadRaceAssets } from '../../raceDisplay'
import { appendRaceTypeFilters, defaultRaceTypeFilters } from '../../raceFilters'
import { state } from '../../store'

defineProps({
  weatherSettings: { type: Object, default: () => ({}) }
})

const { t } = useI18n()
const PAGE_SIZE = 5
const UPCOMING_LIMIT = 100

const status = ref('not_finished')
const game = ref('all')
const myGamesOnly = ref(false)
const typeFilters = ref(defaultRaceTypeFilters())
const page = ref(1)
const races = ref([])
const assets = ref(null)
const loading = ref(true)
const error = ref('')
const filtersOpen = ref(false)

const canFilterMyGames = computed(() => Boolean(state.user?.games?.length))
const canCreate = computed(() => ['admin', 'moder'].includes(state.user?.role))
const isUpcoming = computed(() => status.value === 'not_finished')
const statusOptions = computed(() => [
  { value: 'not_finished', label: t('home.calendar.upcoming') },
  { value: 'finished', label: t('home.calendar.finished') }
])
const gameChoices = computed(() => gameOptions(t, true).map((option) => ({ ...option, label: option.value === 'all' ? t('ui.common.all') : option.label })))
const activeTypeFilters = computed(() => Object.values(typeFilters.value).filter(Boolean).length)
const visibleRaces = computed(() => (isUpcoming.value ? races.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE) : races.value))
const hasNext = computed(() => (isUpcoming.value ? page.value * PAGE_SIZE < races.value.length : races.value.length === PAGE_SIZE))
const hasFilters = computed(() => game.value !== 'all' || myGamesOnly.value || activeTypeFilters.value > 0)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params = new URLSearchParams({
      game_filter: game.value,
      status_filter: status.value,
      limit: String(isUpcoming.value ? UPCOMING_LIMIT : PAGE_SIZE),
      offset: String(isUpcoming.value ? 0 : (page.value - 1) * PAGE_SIZE)
    })
    if (myGamesOnly.value && canFilterMyGames.value) params.set('my_games_only', 'true')
    appendRaceTypeFilters(params, typeFilters.value)
    const list = await api(`/races?${params.toString()}`)
    races.value = isUpcoming.value
      ? [...list].sort((a, b) => new Date(a.datetime_start) - new Date(b.datetime_start))
      : list
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  game.value = 'all'
  myGamesOnly.value = false
  typeFilters.value = defaultRaceTypeFilters()
}

onMounted(() => {
  load()
  loadRaceAssets().then((value) => { assets.value = value }).catch(() => {})
})

watch(page, () => {
  if (!isUpcoming.value) load()
})

watch([status, game, myGamesOnly, typeFilters], () => {
  if (page.value !== 1) {
    page.value = 1
    // Finished races are paged on the server: the page watcher reloads them.
    if (!isUpcoming.value) return
  }
  load()
}, { deep: true })
</script>

<template>
  <section class="races" aria-labelledby="home-races-title">
    <header class="races__head">
      <div class="races__title">
        <p class="ui-eyebrow ui-eyebrow--accent">{{ t('home.calendar.eyebrow') }}</p>
        <h2 id="home-races-title" v-split class="ui-title">{{ t('home.calendar.title') }}</h2>
      </div>
      <div class="races__actions">
        <RouterLink class="ui-btn ui-btn--ghost ui-btn--sm" to="/calendar"><CalendarSearch :size="16" />{{ t('home.calendar.openCalendar') }}</RouterLink>
        <RouterLink v-if="canCreate" class="ui-btn ui-btn--primary ui-btn--sm" to="/races/new"><Plus :size="16" />{{ t('common.create') }}</RouterLink>
      </div>
    </header>

    <div class="races__filters">
      <SegmentedControl v-model="status" :options="statusOptions" :aria-label="t('raceFilters.statusGroup')" />
      <SegmentedControl v-model="game" :options="gameChoices" size="sm" :aria-label="t('fields.game')" />
      <SwitchToggle v-model="myGamesOnly" :label="t('raceFilters.myGamesOnly')" :disabled="!canFilterMyGames" />
      <Popover v-model:open="filtersOpen" width="320px" :label="t('raceFilters.moreFilters')">
        <template #trigger="{ toggle }">
          <button class="ui-btn ui-btn--outline ui-btn--sm" :class="{ 'is-on': activeTypeFilters }" type="button" :aria-expanded="filtersOpen" @click="toggle">
            <SlidersHorizontal :size="15" />
            {{ activeTypeFilters ? t('home.calendar.filtersActive', { count: activeTypeFilters }) : t('home.calendar.filters') }}
          </button>
        </template>
        <div class="races__type-filters">
          <RaceTypeFilters v-model="typeFilters" />
        </div>
      </Popover>
    </div>

    <p v-if="error" class="ui-alert">{{ error }}</p>

    <TransitionGroup v-if="visibleRaces.length" tag="div" name="ui-list" class="races__list" :class="{ 'is-loading': loading }">
      <RaceRow v-for="(race, index) in visibleRaces" :key="race.id" v-reveal="{ delay: index * 70, y: 14, blur: 4 }" :race="race" :assets="assets" :weather-settings="weatherSettings" />
    </TransitionGroup>
    <EmptyState v-else-if="loading" loading :title="t('ui.common.loading')" compact />
    <EmptyState v-else :icon="CalendarSearch" :title="t('home.calendar.emptyTitle')" :text="t('home.calendar.emptyText')">
      <button v-if="hasFilters" class="ui-btn ui-btn--outline ui-btn--sm" type="button" @click="resetFilters">{{ t('home.calendar.reset') }}</button>
    </EmptyState>

    <PaginationControls
      v-model:page="page"
      :page-size="PAGE_SIZE"
      :loaded-count="visibleRaces.length"
      :has-next="hasNext"
      :total-items="isUpcoming ? races.length : null"
    />
  </section>
</template>

<style scoped>
.races {
  display: grid;
  gap: 18px;
}

.races__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
}

.races__title {
  display: grid;
  gap: 8px;
}

.races__actions {
  display: flex;
  gap: 8px;
}

.races__filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
}

.races__filters .is-on {
  border-color: var(--c-blue-line);
  color: var(--c-accent-text);
}

.races__type-filters {
  padding: 6px;
}

.races__list {
  position: relative;
  display: grid;
  gap: 10px;
  transition: opacity var(--dur-2);
}

.races__list.is-loading {
  opacity: 0.55;
}
</style>
