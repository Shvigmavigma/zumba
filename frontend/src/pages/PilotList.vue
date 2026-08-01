<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import PaginationControls from '../components/PaginationControls.vue'
import UserAvatar from '../components/UserAvatar.vue'
import { gameLabel } from '../i18nLabels'
import { formatRating, teamShortName } from '../pilotDisplay'

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
</script>

<template>
  <section class="section pilot-list-page">
    <div class="section-header pilot-list-header">
      <h1>{{ t('nav.pilots') }}</h1>
      <div class="pilot-list-controls">
        <input v-model="search" class="pilot-list-search" :placeholder="t('common.search')" />
        <select v-model="sort" class="pilot-list-sort" :aria-label="t('common.sort')">
          <option value="rating_desc">{{ t('sort.ratingDesc') }}</option>
          <option value="rating_asc">{{ t('sort.ratingAsc') }}</option>
          <option value="sr_desc">{{ t('sort.srDesc') }}</option>
          <option value="sr_asc">{{ t('sort.srAsc') }}</option>
          <option value="alpha_asc">{{ t('sort.alphaAsc') }}</option>
          <option value="alpha_desc">{{ t('sort.alphaDesc') }}</option>
        </select>
      </div>
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <table class="table card">
      <thead>
        <tr><th>#</th><th>{{ t('roles.pilot') }}</th><th>{{ t('fields.team') }}</th><th>{{ t('fields.country') }}</th><th>RER</th><th>SR</th><th>{{ t('fields.ratingRaces') }}</th></tr>
      </thead>
      <tbody>
        <tr v-for="pilot in pilots" :key="pilot.id">
          <td>{{ pilot.pilot_number }}</td>
          <td>
            <div class="user-list-cell">
              <UserAvatar mini :color="pilot.avatar_color" :label="pilot.nickname || pilot.login" />
              <RouterLink class="user-list-main" :to="`/pilots/${pilot.id}`">
                <strong>{{ pilot.first_name }} {{ pilot.last_name }}</strong>
                <span>{{ pilot.nickname }} - {{ pilotGames(pilot) }}</span>
              </RouterLink>
            </div>
          </td>
          <td><span class="team-mini-chip" :title="pilot.team_name || t('common.none')">{{ teamShortName(pilot.team_name) }}</span></td>
          <td>{{ pilot.country || '-' }}</td>
          <td>{{ formatRating(pilot.rating) }}</td>
          <td>{{ pilot.sr }}</td>
          <td>{{ pilot.rating_race_count ?? 0 }}</td>
        </tr>
      </tbody>
    </table>
    <PaginationControls v-model:page="page" :page-size="pageSize" :loaded-count="pilots.length" :has-next="hasNextPage" />
  </section>
</template>
