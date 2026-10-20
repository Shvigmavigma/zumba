<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { AlertTriangle, Gauge, Medal, RefreshCw, Search, SearchX, Trophy, User, Users, X } from 'lucide-vue-next'
import { api } from '../api'
import PaginationControls from '../components/PaginationControls.vue'
import EmptyState from '../ui/EmptyState.vue'
import PageHeader from '../ui/PageHeader.vue'
import SegmentedControl from '../ui/SegmentedControl.vue'
import CountUp from '../ui/fx/CountUp.vue'
import HallPodium from './hall-of-fame/HallPodium.vue'
import HallStandings from './hall-of-fame/HallStandings.vue'
import { HALL_MODE_MEDALS, HALL_MODE_RATING, hallRating, hallStat, rankHallItems } from './hall-of-fame/hallRanking'
import { gameOptions } from '../i18nLabels'
import { OVERALL_RATING_GAME, RATING_GAMES, ratingForGame } from '../pilotDisplay'

const { t } = useI18n()

const data = ref({ pilots: [], teams: [] })
const activeTab = ref('pilots')
const ratingMode = ref(HALL_MODE_RATING)
const search = ref('')
const ratingGame = ref(OVERALL_RATING_GAME)
const loading = ref(false)
const error = ref('')
const pilotPage = ref(1)
const teamPage = ref(1)
const pageSize = 20
const ratingGameOptions = computed(() => gameOptions(t, true))
const modeOptions = computed(() => [
  { value: HALL_MODE_RATING, label: t('hallOfFame.byRating'), icon: Gauge },
  { value: HALL_MODE_MEDALS, label: t('hallOfFame.byMedals'), icon: Medal }
])

const tabs = computed(() => [
  { value: 'pilots', label: t('hallOfFame.pilotsTab'), icon: User, count: rankedPilots.value.length },
  { value: 'teams', label: t('hallOfFame.teamsTab'), icon: Users, count: rankedTeams.value.length }
])
const rankedPilots = computed(() => rankItems(data.value.pilots))
const rankedTeams = computed(() => rankItems(data.value.teams))
const visiblePilots = computed(() => filterItems(rankedPilots.value, pilotSearchText))
const visibleTeams = computed(() => filterItems(rankedTeams.value, teamSearchText))
const pagedPilots = computed(() => visiblePilots.value.slice((pilotPage.value - 1) * pageSize, pilotPage.value * pageSize))
const pagedTeams = computed(() => visibleTeams.value.slice((teamPage.value - 1) * pageSize, teamPage.value * pageSize))
const pilotTotalPages = computed(() => Math.max(1, Math.ceil(visiblePilots.value.length / pageSize)))
const teamTotalPages = computed(() => Math.max(1, Math.ceil(visibleTeams.value.length / pageSize)))
const totalMedals = computed(() => rankedPilots.value.reduce((sum, pilot) => sum + statValue(pilot, 'podiums'), 0))

// View helpers for the redesigned layout (no change to ranking or filtering).
const isPilots = computed(() => activeTab.value === 'pilots')
const ranked = computed(() => (isPilots.value ? rankedPilots.value : rankedTeams.value))
const visible = computed(() => (isPilots.value ? visiblePilots.value : visibleTeams.value))
const paged = computed(() => (isPilots.value ? pagedPilots.value : pagedTeams.value))
const currentPage = computed(() => (isPilots.value ? pilotPage.value : teamPage.value))
const scopeLabel = computed(() => ratingGameOptions.value.find((option) => option.value === ratingGame.value)?.label || ratingGame.value)
const hasData = computed(() => data.value.pilots.length > 0 || data.value.teams.length > 0)
const revealKey = computed(() => `${activeTab.value}-${ratingMode.value}-${ratingGame.value}-${currentPage.value}`)
const summary = computed(() => [
  { key: 'pilots', icon: Trophy, label: t('hallOfFame.ratedPilots'), value: data.value.pilots.length },
  { key: 'teams', icon: Users, label: t('hallOfFame.ratedTeams'), value: data.value.teams.length },
  { key: 'medals', icon: Medal, label: t('hallOfFame.totalMedals'), value: totalMedals.value }
])

function statValue(item, field) {
  return hallStat(item, field, ratingGame.value)
}

/** The RER the item is ranked by in the selected simulator. */
function ratingValue(item) {
  return hallRating(item, ratingGame.value)
}

function rankItems(items) {
  return rankHallItems(items, { mode: ratingMode.value, game: ratingGame.value })
}

function bestPilotFor(team) {
  return ratingGame.value === OVERALL_RATING_GAME ? team.best_pilot : team.best_pilots_by_game?.[ratingGame.value]
}

function filterItems(items, textFactory) {
  const needle = search.value.trim().toLowerCase()
  if (!needle) return items
  return items.filter((item) => textFactory(item).includes(needle))
}

function pilotSearchText(pilot) {
  return [
    pilot.login,
    pilot.nickname,
    pilot.first_name,
    pilot.last_name,
    pilot.pilot_number,
    pilot.team_name,
    statValue(pilot, 'points'),
    statValue(pilot, 'gold'),
    statValue(pilot, 'silver'),
    statValue(pilot, 'bronze'),
    ...RATING_GAMES.map((game) => ratingForGame(pilot, game)),
    pilot.sr
  ]
    .filter((value) => value !== undefined && value !== null)
    .join(' ')
    .toLowerCase()
}

function teamSearchText(team) {
  return [
    team.name,
    team.description,
    statValue(team, 'points'),
    statValue(team, 'gold'),
    statValue(team, 'silver'),
    statValue(team, 'bronze'),
    ...RATING_GAMES.map((game) => hallRating(team, game)),
    bestPilotFor(team)?.login,
    bestPilotFor(team)?.nickname,
    bestPilotFor(team)?.first_name,
    bestPilotFor(team)?.last_name,
    ratingForGame(bestPilotFor(team), ratingGame.value)
  ]
    .filter((value) => value !== undefined && value !== null)
    .join(' ')
    .toLowerCase()
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await api('/hall-of-fame')
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(search, () => {
  pilotPage.value = 1
  teamPage.value = 1
})
watch(activeTab, () => {
  pilotPage.value = 1
  teamPage.value = 1
})
watch([ratingGame, ratingMode], () => {
  pilotPage.value = 1
  teamPage.value = 1
})
watch(visiblePilots, () => {
  if (pilotPage.value > pilotTotalPages.value) {
    pilotPage.value = pilotTotalPages.value
  }
})
watch(visibleTeams, () => {
  if (teamPage.value > teamTotalPages.value) {
    teamPage.value = teamTotalPages.value
  }
})
</script>

<template>
  <div class="ui-page ui-shell ui-shell--wide hall">
    <PageHeader :eyebrow="t('hallPage.eyebrow')" :title="t('nav.hallOfFame')" :lead="t('hallOfFame.subtitle')">
      <template #aside>
        <dl class="hall__summary" :aria-label="t('hallPage.summary')">
          <div v-for="(item, index) in summary" :key="item.key" v-reveal="{ delay: 260 + index * 90, y: 10, blur: 4 }" v-spotlight class="hall__stat">
            <dt><component :is="item.icon" :size="14" aria-hidden="true" />{{ item.label }}</dt>
            <dd><CountUp :value="item.value" /></dd>
          </div>
        </dl>
      </template>
      <template #actions>
        <button v-spark class="ui-btn ui-btn--outline ui-btn--sm hall__reload" type="button" :disabled="loading" @click="load">
          <RefreshCw :size="15" :class="{ 'is-spinning': loading }" aria-hidden="true" />
          {{ loading ? t('hallPage.updating') : t('common.reload') }}
        </button>
      </template>
    </PageHeader>

    <div v-reveal="{ delay: 120, y: 14 }" class="hall__controls">
      <SegmentedControl v-model="activeTab" :options="tabs" :aria-label="t('nav.hallOfFame')" />
      <SegmentedControl v-model="ratingMode" :options="modeOptions" size="sm" :aria-label="t('hallOfFame.mode')" />
      <SegmentedControl v-model="ratingGame" :options="ratingGameOptions" size="sm" :aria-label="t('hallOfFame.priorityGame')" />
      <p class="hall__order">{{ ratingMode === HALL_MODE_RATING ? t('hallPage.orderRating') : t('hallPage.order') }}</p>
    </div>

    <p v-if="error" class="ui-alert" role="alert">
      <AlertTriangle :size="18" aria-hidden="true" />
      <span class="hall__error-text">{{ error }}</span>
      <button class="ui-btn ui-btn--outline ui-btn--sm" type="button" :disabled="loading" @click="load">{{ t('ui.common.retry') }}</button>
    </p>

    <EmptyState v-if="loading && !hasData" loading :title="t('ui.common.loading')" />

    <template v-else-if="hasData || !error">
      <section v-if="ranked.length" class="hall__podium" :class="{ 'is-loading': loading }" aria-labelledby="hall-podium-title">
        <header class="hall__podium-head">
          <p class="ui-eyebrow ui-eyebrow--accent">{{ t('hallPage.podium.eyebrow', { scope: scopeLabel }) }}</p>
          <h2 id="hall-podium-title" :key="activeTab" v-split class="ui-title">{{ isPilots ? t('hallPage.podium.pilots') : t('hallPage.podium.teams') }}</h2>
        </header>
        <HallPodium :key="`${activeTab}-${ratingMode}-${ratingGame}`" :items="ranked.slice(0, 3)" :kind="activeTab" :game="ratingGame" :mode="ratingMode" :stat="statValue" :rating="ratingValue" />
      </section>

      <EmptyState
        v-else
        :icon="Trophy"
        :title="isPilots ? t('hallOfFame.emptyPilots') : t('hallOfFame.emptyTeams')"
        :text="ratingMode === HALL_MODE_RATING ? '' : t('hallPage.emptyText')"
      />

      <section v-if="ranked.length" v-reveal="{ y: 24 }" class="hall__board ui-card ui-card--flush" :class="{ 'is-loading': loading }" aria-labelledby="hall-board-title">
        <header class="hall__board-head">
          <div class="hall__board-title">
            <p class="ui-eyebrow">{{ t('hallPage.table.eyebrow', { scope: scopeLabel }) }}</p>
            <h2 id="hall-board-title" class="hall__board-h">{{ isPilots ? t('hallPage.table.pilots') : t('hallPage.table.teams') }}</h2>
            <span class="hall__board-count ui-num">
              {{ search.trim() ? t('hallPage.table.shown', { shown: visible.length, total: ranked.length }) : t('hallPage.table.total', { total: ranked.length }) }}
            </span>
          </div>
          <label class="hall__search">
            <Search class="hall__search-icon" :size="17" aria-hidden="true" />
            <input v-model="search" class="ui-input hall__search-input" type="search" :placeholder="t('hallOfFame.searchPlaceholder')" :aria-label="t('hallOfFame.searchPlaceholder')" />
            <Transition name="ui-fade">
              <button v-if="search" class="hall__search-clear" type="button" :aria-label="t('hallPage.clearSearch')" @click="search = ''"><X :size="15" /></button>
            </Transition>
          </label>
        </header>

        <HallStandings
          v-if="visible.length"
          :kind="activeTab"
          :rows="paged"
          :offset="(currentPage - 1) * pageSize"
          :game="ratingGame"
          :mode="ratingMode"
          :stat="statValue"
          :rating="ratingValue"
          :best-pilot="bestPilotFor"
          :reveal-key="revealKey"
        />
        <div v-else class="hall__no-match">
          <EmptyState :icon="SearchX" :title="t('hallPage.noMatchTitle')" :text="t('hallPage.noMatchText', { query: search.trim() })" compact>
            <button class="ui-btn ui-btn--outline ui-btn--sm" type="button" @click="search = ''">{{ t('hallPage.resetSearch') }}</button>
          </EmptyState>
        </div>

        <footer class="hall__board-foot">
          <PaginationControls v-if="isPilots" v-model:page="pilotPage" :page-size="pageSize" :total-items="visiblePilots.length" />
          <PaginationControls v-else v-model:page="teamPage" :page-size="pageSize" :total-items="visibleTeams.length" />
        </footer>
      </section>
    </template>
  </div>
</template>

<style scoped>
.hall {
  gap: clamp(22px, 3.2vw, 40px);
}

/* ---------- Header summary ---------- */
.hall__summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 0;
}

.hall__stat {
  display: grid;
  gap: 6px;
  min-width: 120px;
  padding: 12px 14px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  background: var(--c-surface);
  -webkit-backdrop-filter: var(--glass-filter);
  backdrop-filter: var(--glass-filter);
}

.hall__stat dt {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  line-height: 1.25;
  text-transform: uppercase;
}

.hall__stat dt svg {
  flex: 0 0 auto;
  color: var(--c-accent-text);
}

.hall__stat dd {
  margin: 0;
  color: var(--c-text);
  font-size: 26px;
  font-weight: 700;
  line-height: 1;
}

.hall__reload .is-spinning {
  animation: hall-spin 900ms linear infinite;
}

/* ---------- Controls ---------- */
.hall__controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
}

.hall__order {
  margin: 0 0 0 auto;
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.04em;
}

.hall__error-text {
  flex: 1 1 auto;
}

/* ---------- Podium ---------- */
.hall__podium {
  position: relative;
  isolation: isolate;
  display: grid;
  gap: clamp(18px, 2.6vw, 30px);
  padding-top: 6px;
  transition: opacity var(--dur-2);
}

/* A soft stage light behind the podium. */
.hall__podium::before {
  position: absolute;
  inset: 8% 10% auto;
  z-index: -1;
  height: 80%;
  border-radius: 50%;
  background: radial-gradient(closest-side, color-mix(in srgb, var(--bm-blue) 26%, transparent), transparent);
  content: '';
  filter: blur(30px);
  pointer-events: none;
}

.hall__podium-head {
  display: grid;
  justify-items: center;
  gap: 8px;
  text-align: center;
}

/* ---------- Standings board ---------- */
.hall__board {
  gap: 0;
  transition: opacity var(--dur-2);
}

.is-loading {
  opacity: 0.55;
}

.hall__board-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 14px 20px;
  padding: clamp(16px, 2vw, 22px) clamp(16px, 2vw, 22px) 16px;
  border-bottom: 1px solid var(--c-line);
}

.hall__board-title {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.hall__board-h {
  margin: 0;
  color: var(--c-text);
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  line-height: 1.15;
  text-transform: uppercase;
}

.hall__board-count {
  color: var(--c-text-3);
  font-size: 12px;
}

.hall__search {
  position: relative;
  display: flex;
  align-items: center;
  flex: 0 1 360px;
  min-width: min(100%, 240px);
}

.hall__search-icon {
  position: absolute;
  left: 14px;
  z-index: 1;
  color: var(--c-text-3);
  pointer-events: none;
  transition: color var(--dur-2);
}

.hall__search:focus-within .hall__search-icon {
  color: var(--c-accent-text);
}

.hall__search-input {
  min-height: 44px;
  padding-right: 42px;
  padding-left: 42px;
  border-radius: var(--r-pill);
}

.hall__search-input::-webkit-search-cancel-button {
  -webkit-appearance: none;
  appearance: none;
}

.hall__search-clear {
  position: absolute;
  right: 6px;
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: color-mix(in srgb, var(--c-text) 10%, transparent);
  color: var(--c-text-2);
  cursor: pointer;
  transition: background-color var(--dur-2), transform var(--dur-2) var(--ease-spring);
}

.hall__search-clear:hover {
  background: var(--c-blue-soft);
  color: var(--c-text);
}

.hall__search-clear:active {
  transform: scale(0.9);
}

.hall__no-match {
  padding: 18px;
}

.hall__board-foot {
  padding: 14px 16px;
  border-top: 1px solid var(--c-line);
}

.hall__board-foot:empty,
.hall__board-foot:not(:has(*)) {
  display: none;
}

@keyframes hall-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 760px) {
  .hall__summary {
    width: 100%;
  }

  .hall__stat {
    min-width: 0;
    padding: 10px 12px;
  }

  .hall__stat dd {
    font-size: 22px;
  }

  .hall__controls > :deep(.segmented:first-child) {
    width: 100%;
  }

  .hall__controls > :deep(.segmented:first-child .segmented__option) {
    flex: 1 1 0;
  }

  .hall__order {
    margin-left: 0;
  }

  .hall__search {
    flex: 1 1 100%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .hall__reload .is-spinning {
    animation: none;
  }
}
</style>
