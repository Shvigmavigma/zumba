<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { Search, SlidersHorizontal } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import PaginationControls from '../components/PaginationControls.vue'
import UserAvatar from '../components/UserAvatar.vue'
import { countryLabel, gameLabel } from '../i18nLabels'
import { formatPilotNumber, formatRating, pilotName, teamHref, teamShortName } from '../pilotDisplay'

const { t } = useI18n()
const pilots = ref([])
const search = ref('')
const sort = ref('rating_desc')
const error = ref('')
const page = ref(1)
const pageSize = 20
const hasNextPage = computed(() => pilots.value.length === pageSize)

async function load() {
  try {
    const params = new URLSearchParams()
    if (search.value.trim()) params.set('search', search.value.trim())
    params.set('sort', sort.value)
    params.set('limit', String(pageSize))
    params.set('offset', String((page.value - 1) * pageSize))
    pilots.value = await api(`/users/pilots?${params.toString()}`)
  } catch (err) {
    error.value = err.message
  }
}

function resetPageAndLoad() {
  if (page.value === 1) {
    load()
    return
  }
  page.value = 1
}

onMounted(load)
watch(page, load)
watch([search, sort], resetPageAndLoad)

function pilotGames(pilot) {
  return pilot.games?.length ? pilot.games.map((game) => gameLabel(t, game)).join(' / ') : t('common.none')
}

function pilotNumber(pilot) {
  return pilot.pilot_number !== null && pilot.pilot_number !== undefined ? `#${formatPilotNumber(pilot.pilot_number)}` : '-'
}

function pilotCountry(pilot) {
  return pilot.country ? countryLabel(t, pilot.country) : t('common.none')
}
</script>

<template>
  <section class="section pilot-list-page">
    <div class="section-header pilot-list-header">
      <h1>{{ t('nav.pilots') }}</h1>
      <div class="pilot-list-controls">
        <label class="pilot-control-field">
          <Search :size="16" />
          <input v-model="search" class="pilot-list-search" :placeholder="t('common.search')" />
        </label>
        <label class="pilot-control-field pilot-control-select">
          <SlidersHorizontal :size="16" />
          <select v-model="sort" class="pilot-list-sort" :aria-label="t('common.sort')">
            <option value="rating_desc">{{ t('sort.ratingDesc') }}</option>
            <option value="rating_asc">{{ t('sort.ratingAsc') }}</option>
            <option value="sr_desc">{{ t('sort.srDesc') }}</option>
            <option value="sr_asc">{{ t('sort.srAsc') }}</option>
            <option value="alpha_asc">{{ t('sort.alphaAsc') }}</option>
            <option value="alpha_desc">{{ t('sort.alphaDesc') }}</option>
          </select>
        </label>
      </div>
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="pilot-roster card" role="table" :aria-label="t('nav.pilots')">
      <div class="pilot-roster-head" role="row">
        <span role="columnheader">#</span>
        <span role="columnheader">{{ t('roles.pilot') }}</span>
        <span role="columnheader">{{ t('fields.team') }}</span>
        <span role="columnheader">{{ t('fields.country') }}</span>
        <span role="columnheader">RER</span>
        <span role="columnheader">SR</span>
        <span role="columnheader">{{ t('fields.ratingRaces') }}</span>
      </div>

      <article v-for="pilot in pilots" :key="pilot.id" class="pilot-roster-row" role="row">
        <span class="pilot-roster-number" role="cell" data-label="#">{{ pilotNumber(pilot) }}</span>

        <div class="pilot-roster-driver" role="cell" :data-label="t('roles.pilot')">
          <UserAvatar mini :src="pilot.avatar_url" :color="pilot.avatar_color" :label="pilot.nickname || pilot.login" />
          <RouterLink class="user-list-main" :to="`/pilots/${pilot.id}`">
            <strong>{{ pilotName(pilot, pilot.login) }}</strong>
            <span>{{ pilot.nickname || pilot.login }} - {{ pilotGames(pilot) }}</span>
          </RouterLink>
        </div>

        <span class="pilot-roster-team" role="cell" :data-label="t('fields.team')">
          <RouterLink v-if="pilot.team_id" class="team-mini-chip team-link-chip" :to="teamHref(pilot.team_id)" :title="pilot.team_name || t('common.none')">
            {{ teamShortName(pilot.team_name, pilot.team_abbreviation) }}
          </RouterLink>
          <span v-else class="team-mini-chip" :title="pilot.team_name || t('common.none')">{{ teamShortName(pilot.team_name, pilot.team_abbreviation) }}</span>
        </span>
        <span class="pilot-roster-country" role="cell" :data-label="t('fields.country')">{{ pilotCountry(pilot) }}</span>
        <span class="pilot-roster-metric" role="cell" data-label="RER"><strong>{{ formatRating(pilot.rating) }}</strong><small>RER</small></span>
        <span class="pilot-roster-metric" role="cell" data-label="SR"><strong>{{ pilot.sr }}</strong><small>SR</small></span>
        <span class="pilot-roster-metric" role="cell" :data-label="t('fields.ratingRaces')"><strong>{{ pilot.rating_race_count ?? 0 }}</strong><small>{{ t('fields.ratingRaces') }}</small></span>
      </article>

      <div v-if="!pilots.length" class="pilot-roster-empty">{{ t('common.noMatches') }}</div>
    </div>
    <PaginationControls v-model:page="page" :page-size="pageSize" :loaded-count="pilots.length" :has-next="hasNextPage" />
  </section>
</template>
