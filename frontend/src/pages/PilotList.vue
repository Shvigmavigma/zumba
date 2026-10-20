<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Map as MapIcon, Search, SlidersHorizontal, Users, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import LicenseBadge from '../components/LicenseBadge.vue'
import PaginationControls from '../components/PaginationControls.vue'
import PilotRoles from '../components/PilotRoles.vue'
import UserAvatar from '../components/UserAvatar.vue'
import EmptyState from '../ui/EmptyState.vue'
import PageHeader from '../ui/PageHeader.vue'
import SegmentedControl from '../ui/SegmentedControl.vue'
import TierPlate from './pilots/TierPlate.vue'
import TrackRecords from './pilots/TrackRecords.vue'
import { countryCode } from '../countries'
import { countryLabel, gameLabel, gameOptions } from '../i18nLabels'
import { ensureLicenseSettings } from '../licenseSettings'
import { DEFAULT_LICENSE_TIERS, formatPilotNumber, formatRating, pilotName, ratingForGame, ratingLicenseTier, ratingRaceCountForGame, teamHref, teamShortName } from '../pilotDisplay'
import { rankLadder } from '../ranks'
import { state } from '../store'
import { useRanks } from '../useRanks'
import RankAura from '../ui/rank/RankAura.vue'

const { t } = useI18n()
const { rankOf } = useRanks()
const route = useRoute()
const activeTab = ref('pilots')
const pilots = ref([])
const search = ref('')
const sort = ref('rating_desc')
const ratingGame = ref('ACC')
const error = ref('')
const loading = ref(true)
const page = ref(1)
const pageSize = 20
const hasNextPage = computed(() => pilots.value.length === pageSize)
const tabOptions = computed(() => [
  { value: 'pilots', label: t('pilotsPage.tabs.pilots'), icon: Users },
  { value: 'tracks', label: t('pilotsPage.tabs.tracks'), icon: MapIcon }
])
const gameChoices = computed(() => gameOptions(t).map((option) => ({ ...option, label: `RER ${option.label}` })))
const tiers = computed(() => state.licenseTiers || DEFAULT_LICENSE_TIERS)
// Every tier with the rank it looks like, for the ladder of previews above the list.
const ladder = computed(() => rankLadder(tiers.value))
const myTier = computed(() => (state.user ? ratingLicenseTier(ratingForGame(state.user, ratingGame.value), tiers.value) : null))
const showPodium = computed(() => sort.value === 'rating_desc' && page.value === 1 && !search.value.trim())

async function load() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (search.value.trim()) params.set('search', search.value.trim())
    params.set('sort', sort.value)
    params.set('rating_game', ratingGame.value)
    params.set('limit', String(pageSize))
    params.set('offset', String((page.value - 1) * pageSize))
    pilots.value = await api(`/users/pilots?${params.toString()}`)
    error.value = ''
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function resetPageAndLoad() {
  if (page.value === 1) {
    load()
    return
  }
  page.value = 1
}

onMounted(() => {
  load()
  ensureLicenseSettings()
})
watch(page, load)
watch([search, sort, ratingGame], resetPageAndLoad)
watch(() => route.query.track, (track) => {
  if (track) activeTab.value = 'tracks'
}, { immediate: true })

function place(index) {
  return (page.value - 1) * pageSize + index + 1
}

function pilotGames(pilot) {
  return pilot.games?.length ? pilot.games.map((game) => gameLabel(t, game)).join(' / ') : t('common.none')
}

function pilotCountry(pilot) {
  return pilot.country ? countryLabel(t, pilot.country) : t('common.none')
}
</script>

<template>
  <div class="ui-page ui-shell ui-shell--wide pilots">
    <PageHeader :eyebrow="t('pilotsPage.eyebrow')" :title="t('nav.pilots')" :lead="t('pilotsPage.lead')">
      <template #actions>
        <SegmentedControl v-model="activeTab" :options="tabOptions" :aria-label="t('nav.pilots')" />
      </template>
    </PageHeader>

    <Transition name="ui-fade" mode="out-in">
      <div v-if="activeTab === 'pilots'" key="pilots" class="pilots__panel">
        <div class="pilots__controls">
          <SegmentedControl v-model="ratingGame" :options="gameChoices" :aria-label="t('fields.game')" />
          <label class="pilots__search">
            <Search :size="16" />
            <input v-model="search" type="search" :placeholder="t('pilotsPage.searchPlaceholder')" :aria-label="t('common.search')" />
            <button v-if="search" class="pilots__clear" type="button" :aria-label="t('pilotsPage.resetSearch')" @click="search = ''"><X :size="14" /></button>
          </label>
          <label class="pilots__sort">
            <SlidersHorizontal :size="16" />
            <select v-model="sort" :aria-label="t('common.sort')">
              <option value="rating_desc">{{ t('sort.ratingDesc') }}</option>
              <option value="rating_asc">{{ t('sort.ratingAsc') }}</option>
              <option value="sr_desc">{{ t('sort.srDesc') }}</option>
              <option value="sr_asc">{{ t('sort.srAsc') }}</option>
              <option value="alpha_asc">{{ t('sort.alphaAsc') }}</option>
              <option value="alpha_desc">{{ t('sort.alphaDesc') }}</option>
            </select>
          </label>
        </div>

        <ul class="tiers" :aria-label="t('pilotsPage.tiersTitle')">
          <TierPlate
            v-for="(step, index) in ladder"
            :key="step.name"
            v-reveal="{ delay: index * 50, y: 10, blur: 0 }"
            class="tiers__item"
            :step="step"
            :mine="Boolean(myTier && myTier.name === step.name)"
            :mine-label="t('pilotsPage.yourTier')"
          />
        </ul>

        <p v-if="error" class="ui-alert">{{ error }}</p>

        <div class="roster" :class="{ 'is-loading': loading && pilots.length }" role="table" :aria-label="t('pilotTabs.pilots')">
          <div class="roster__head" role="row">
            <span role="columnheader">{{ t('pilotsPage.columns.place') }}</span>
            <span role="columnheader">{{ t('pilotsPage.columns.pilot') }}</span>
            <span role="columnheader">{{ t('pilotsPage.columns.team') }}</span>
            <span role="columnheader">{{ t('pilotsPage.columns.country') }}</span>
            <span role="columnheader" class="is-num">{{ t('pilotsPage.columns.rer') }}</span>
            <span role="columnheader" class="is-num">{{ t('pilotsPage.columns.sr') }}</span>
            <span role="columnheader" class="is-num">{{ t('pilotsPage.columns.races') }}</span>
          </div>

          <article
            v-for="(pilot, index) in pilots"
            :key="`${ratingGame}-${pilot.id}`"
            class="roster__row rank-surface"
            :class="{ [`is-p${index + 1}`]: showPodium && index < 3, 'is-me': state.user?.id === pilot.id }"
            :data-rank="rankOf(pilot)"
            :style="{ '--i': index }"
            role="row"
          >
            <RankAura :rank="rankOf(pilot)" :seed="pilot.id" />
            <span class="roster__place" role="cell" :data-label="t('pilotsPage.columns.place')">
              <span class="ui-pos" :class="showPodium && index < 3 ? `ui-pos--${index + 1}` : ''">{{ place(index) }}</span>
            </span>

            <div class="roster__pilot" role="cell" :data-label="t('pilotsPage.columns.pilot')">
              <UserAvatar mini class="roster__avatar rank-avatar" :data-rank="rankOf(pilot)" :src="pilot.avatar_url" :color="pilot.avatar_color" :label="pilot.nickname || pilot.login" />
              <RouterLink class="roster__who" :to="`/pilots/${pilot.id}`">
                <span class="roster__name">
                  <strong class="rank-name" :data-rank="rankOf(pilot)">{{ pilotName(pilot, pilot.login) }}</strong>
                  <PilotRoles :roles="pilot.pilot_roles" />
                  <LicenseBadge :user="pilot" :game="ratingGame" />
                </span>
                <small><b class="ui-num">#{{ formatPilotNumber(pilot.pilot_number) }}</b> · {{ pilot.nickname || pilot.login }} · {{ pilotGames(pilot) }}</small>
              </RouterLink>
            </div>

            <span class="roster__team" role="cell" :data-label="t('pilotsPage.columns.team')">
              <RouterLink v-if="pilot.team_id" class="roster__chip" :to="teamHref(pilot.team_id)" :title="pilot.team_name || t('common.none')">
                {{ teamShortName(pilot.team_name, pilot.team_abbreviation) }}
              </RouterLink>
              <span v-else class="roster__chip is-empty" :title="t('common.none')">{{ teamShortName(pilot.team_name, pilot.team_abbreviation) }}</span>
            </span>

            <span class="roster__country" role="cell" :data-label="t('pilotsPage.columns.country')">
              <span v-if="countryCode(pilot.country)" class="roster__code">{{ countryCode(pilot.country) }}</span>
              {{ pilotCountry(pilot) }}
            </span>
            <span class="roster__metric roster__metric--rer ui-num" role="cell" :data-label="`RER ${ratingGame}`">{{ formatRating(ratingForGame(pilot, ratingGame)) }}</span>
            <span class="roster__metric ui-num" role="cell" data-label="SR">{{ pilot.sr }}</span>
            <span class="roster__metric ui-num" role="cell" :data-label="t('fields.ratingRaces')">{{ ratingRaceCountForGame(pilot, ratingGame) }}</span>
          </article>

          <EmptyState v-if="loading && !pilots.length" class="roster__empty" loading :title="t('ui.common.loading')" compact />
          <EmptyState v-else-if="!pilots.length" class="roster__empty" :icon="Users" :title="t('pilotsPage.emptyTitle')" :text="t('pilotsPage.emptyText')" compact>
            <button v-if="search" class="ui-btn ui-btn--outline ui-btn--sm" type="button" @click="search = ''">{{ t('pilotsPage.resetSearch') }}</button>
          </EmptyState>
        </div>

        <PaginationControls v-model:page="page" :page-size="pageSize" :loaded-count="pilots.length" :has-next="hasNextPage" />
      </div>

      <TrackRecords v-else key="tracks" />
    </Transition>
  </div>
</template>

<style scoped>
.pilots__panel {
  display: grid;
  gap: 18px;
}

.pilots__controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
}

.pilots__search,
.pilots__sort {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 44px;
  padding: 0 14px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-pill);
  background: var(--c-sunken);
  color: var(--c-text-3);
  transition: border-color var(--dur-2), box-shadow var(--dur-2);
}

.pilots__search {
  flex: 1 1 240px;
  max-width: 420px;
}

.pilots__search:focus-within,
.pilots__sort:focus-within {
  border-color: var(--bm-blue-bright);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--bm-blue) 20%, transparent);
}

.pilots__search input,
.pilots__sort select {
  flex: 1 1 auto;
  min-width: 0;
  height: 40px;
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
  color: var(--c-text);
  outline: none;
}

.pilots__search input:focus,
.pilots__sort select:focus {
  box-shadow: none;
}

.pilots__clear {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: color-mix(in srgb, var(--c-text) 14%, transparent);
  color: var(--c-text);
  cursor: pointer;
}

/* The RER ladder: one preview plate per tier (pilots/TierPlate.vue). */
.tiers {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(158px, 1fr));
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.roster {
  display: grid;
  overflow: hidden;
  border: 1px solid var(--c-line);
  border-radius: var(--r-xl);
  background: var(--c-surface);
  transition: opacity var(--dur-2);
  -webkit-backdrop-filter: var(--glass-filter);
  backdrop-filter: var(--glass-filter);
}

.roster.is-loading {
  opacity: 0.6;
}

.roster__head,
.roster__row {
  display: grid;
  grid-template-columns: 64px minmax(280px, 2.4fr) 96px minmax(130px, 1fr) 96px 72px 84px;
  align-items: center;
  gap: 12px;
  padding: 0 18px;
}

.roster__head {
  min-height: 46px;
  border-bottom: 1px solid var(--c-line);
  background: color-mix(in srgb, var(--c-surface-solid) 90%, var(--bm-blue));
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.is-num {
  text-align: right;
}

.roster__row {
  position: relative;
  min-height: 68px;
  border-bottom: 1px solid var(--c-line);
  animation: roster-in 560ms var(--ease-out) both;
  animation-delay: calc(var(--i) * 28ms);
  transition: background-color var(--dur-2);
}

@keyframes roster-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
}

.roster__row:last-of-type {
  border-bottom: 0;
}

/* Ranked pilots (bronze and up) sit in the table as banners: inset, rounded,
   with the rank backdrop (.rank-surface) and rim (RankAura). */
.roster__row[data-rank]:not([data-rank='rookie']) {
  margin: 5px 6px;
  padding-inline: 12px;
  border-bottom-color: transparent;
  border-radius: var(--r-md);
}

.roster__row[data-rank]:not([data-rank='rookie']):hover {
  filter: brightness(1.12);
}

.roster__row:hover {
  background: var(--c-blue-soft);
}

.roster__row::before {
  position: absolute;
  top: 10px;
  bottom: 10px;
  left: 0;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: transparent;
  content: '';
}

.roster__row.is-p1::before {
  background: var(--bm-gold);
}

.roster__row.is-p2::before {
  background: var(--bm-silver);
}

.roster__row.is-p3::before {
  background: var(--bm-bronze);
}

.roster__row.is-p1 {
  background: linear-gradient(90deg, color-mix(in srgb, var(--bm-gold) 10%, transparent), transparent 45%);
}

.roster__row.is-me {
  box-shadow: inset 0 0 0 1px var(--c-blue-line);
}

.roster__pilot {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.roster__avatar {
  width: 40px;
  height: 40px;
  border-width: 1px;
  box-shadow: none;
}

.roster__who {
  display: grid;
  gap: 3px;
  min-width: 0;
  color: var(--c-text);
  text-decoration: none;
}

.roster__name {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.roster__name strong {
  overflow: hidden;
  font-size: 14.5px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.roster__who:hover strong {
  color: var(--c-accent-text);
}

.roster__who small {
  overflow: hidden;
  color: var(--c-text-3);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.roster__who small b {
  color: var(--c-text-2);
  font-weight: 600;
}

.roster__chip {
  display: inline-grid;
  place-items: center;
  min-width: 52px;
  height: 28px;
  padding: 0 8px;
  border: 1px solid var(--c-line-strong);
  border-radius: 8px;
  color: var(--c-text);
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
}

a.roster__chip:hover {
  border-color: var(--bm-blue);
  color: var(--c-accent-text);
}

.roster__chip.is-empty {
  color: var(--c-text-3);
}

.roster__country {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow: hidden;
  color: var(--c-text-2);
  font-size: 13.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.roster__code {
  padding: 1px 5px;
  border: 1px solid var(--c-line-strong);
  border-radius: 4px;
  color: var(--c-text);
  font-family: var(--font-mono);
  font-size: 10px;
}

.roster__metric {
  color: var(--c-text);
  font-size: 15px;
  text-align: right;
}

.roster__metric--rer {
  font-size: 17px;
  font-weight: 600;
}

.roster__empty {
  margin: 16px;
}

@media (max-width: 1100px) {
  .roster__head,
  .roster__row {
    grid-template-columns: 56px minmax(0, 1fr) 84px 80px 64px;
  }

  .roster__head > :nth-child(3),
  .roster__head > :nth-child(4),
  .roster__team,
  .roster__country {
    display: none;
  }
}

@media (max-width: 640px) {
  .tiers {
    grid-auto-columns: 164px;
    grid-auto-flow: column;
    grid-template-columns: none;
    padding-bottom: 6px;
    overflow-x: auto;
    scroll-snap-type: x proximity;
  }

  .tiers__item {
    scroll-snap-align: start;
  }

  .roster__head {
    display: none;
  }

  .roster__row {
    grid-template-columns: 44px minmax(0, 1fr) auto;
    grid-template-areas:
      'place pilot rer'
      'place pilot meta';
    gap: 2px 10px;
    padding: 12px 14px;
  }

  .roster__place {
    grid-area: place;
  }

  .roster__pilot {
    grid-area: pilot;
  }

  .roster__metric--rer {
    grid-area: rer;
  }

  .roster__metric:not(.roster__metric--rer) {
    display: none;
  }

  .roster__avatar {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .roster__row {
    animation: none;
  }
}
</style>
