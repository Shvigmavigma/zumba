<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Medal, RefreshCw, Search, Trophy, Users } from 'lucide-vue-next'
import { api } from '../api'
import PaginationControls from '../components/PaginationControls.vue'
import TeamAvatar from '../components/TeamAvatar.vue'
import UserAvatar from '../components/UserAvatar.vue'
import { formatPilotNumber, formatRating, pilotName, teamShortName } from '../pilotDisplay'

const { t } = useI18n()

const data = ref({ pilots: [], teams: [] })
const activeTab = ref('pilots')
const search = ref('')
const loading = ref(false)
const error = ref('')
const pilotPage = ref(1)
const teamPage = ref(1)
const pageSize = 20

const tabs = computed(() => [
  { id: 'pilots', label: t('hallOfFame.pilotsTab'), count: data.value.pilots.length },
  { id: 'teams', label: t('hallOfFame.teamsTab'), count: data.value.teams.length }
])
const visiblePilots = computed(() => filterItems(data.value.pilots, pilotSearchText))
const visibleTeams = computed(() => filterItems(data.value.teams, teamSearchText))
const pagedPilots = computed(() => visiblePilots.value.slice((pilotPage.value - 1) * pageSize, pilotPage.value * pageSize))
const pagedTeams = computed(() => visibleTeams.value.slice((teamPage.value - 1) * pageSize, teamPage.value * pageSize))
const pilotTotalPages = computed(() => Math.max(1, Math.ceil(visiblePilots.value.length / pageSize)))
const teamTotalPages = computed(() => Math.max(1, Math.ceil(visibleTeams.value.length / pageSize)))
const totalMedals = computed(() => data.value.pilots.reduce((sum, pilot) => sum + Number(pilot.podiums || 0), 0))

function filterItems(items, textFactory) {
  const needle = search.value.trim().toLowerCase()
  if (!needle) return items
  return items.filter((item) => textFactory(item).includes(needle))
}

function pilotTitle(pilot) {
  return pilotName(pilot, pilot.login)
}

function pilotLine(pilot) {
  return `#${formatPilotNumber(pilot.pilot_number)} - ${pilot.nickname || pilot.login}`
}

function pilotSearchText(pilot) {
  return [
    pilot.login,
    pilot.nickname,
    pilot.first_name,
    pilot.last_name,
    pilot.pilot_number,
    pilot.team_name,
    pilot.points,
    pilot.rating,
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
    team.points,
    team.average_rating,
    team.best_pilot?.login,
    team.best_pilot?.nickname,
    team.best_pilot?.first_name,
    team.best_pilot?.last_name
  ]
    .filter((value) => value !== undefined && value !== null)
    .join(' ')
    .toLowerCase()
}

function rankClass(index) {
  if (index === 0) return 'is-gold'
  if (index === 1) return 'is-silver'
  if (index === 2) return 'is-bronze'
  return ''
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
  <section class="section hall-page">
    <div class="section-header hall-header">
      <div>
        <h1>{{ t('nav.hallOfFame') }}</h1>
        <p class="muted">{{ t('hallOfFame.subtitle') }}</p>
      </div>
      <button class="button" type="button" :disabled="loading" @click="load">
        <RefreshCw :size="16" />
        {{ t('common.reload') }}
      </button>
    </div>

    <div class="hall-summary-grid">
      <article class="card hall-summary-card">
        <Trophy :size="22" />
        <span>{{ t('hallOfFame.ratedPilots') }}</span>
        <strong>{{ data.pilots.length }}</strong>
      </article>
      <article class="card hall-summary-card">
        <Users :size="22" />
        <span>{{ t('hallOfFame.ratedTeams') }}</span>
        <strong>{{ data.teams.length }}</strong>
      </article>
      <article class="card hall-summary-card">
        <Medal :size="22" />
        <span>{{ t('hallOfFame.totalMedals') }}</span>
        <strong>{{ totalMedals }}</strong>
      </article>
    </div>

    <div class="card hall-controls">
      <div class="hall-tabs" role="tablist" :aria-label="t('nav.hallOfFame')">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          type="button"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
          <span>{{ tab.count }}</span>
        </button>
      </div>
      <label class="hall-search">
        <Search :size="16" />
        <input v-model="search" type="search" :placeholder="t('hallOfFame.searchPlaceholder')" />
      </label>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="loading" class="card hall-empty">{{ t('common.loading') }}</div>

    <div v-else-if="activeTab === 'pilots'" class="hall-table-wrap card">
      <table class="hall-table">
        <thead>
          <tr>
            <th>{{ t('hallOfFame.rank') }}</th>
            <th>{{ t('roles.pilot') }}</th>
            <th>{{ t('fields.team') }}</th>
            <th>{{ t('hallOfFame.goldShort') }}</th>
            <th>{{ t('hallOfFame.silverShort') }}</th>
            <th>{{ t('hallOfFame.bronzeShort') }}</th>
            <th>{{ t('hallOfFame.podiums') }}</th>
            <th>RER</th>
            <th>SR</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(pilot, index) in pagedPilots" :key="pilot.id">
            <td><span class="hall-rank" :class="rankClass((pilotPage - 1) * pageSize + index)">{{ (pilotPage - 1) * pageSize + index + 1 }}</span></td>
            <td>
              <div class="hall-person-cell">
                <UserAvatar mini :src="pilot.avatar_url" :color="pilot.avatar_color" :label="pilotTitle(pilot)" />
                <RouterLink class="hall-title" :to="`/pilots/${pilot.id}`">
                  <strong>{{ pilotTitle(pilot) }}</strong>
                  <span>{{ pilotLine(pilot) }}</span>
                </RouterLink>
              </div>
            </td>
            <td><span class="team-mini-chip" :title="pilot.team_name || t('common.none')">{{ teamShortName(pilot.team_name) }}</span></td>
            <td><span class="hall-medal-value gold">{{ pilot.gold }}</span></td>
            <td><span class="hall-medal-value silver">{{ pilot.silver }}</span></td>
            <td><span class="hall-medal-value bronze">{{ pilot.bronze }}</span></td>
            <td>{{ pilot.podiums }}</td>
            <td>{{ formatRating(pilot.rating) }}</td>
            <td>{{ Number(pilot.sr).toFixed(1) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="!visiblePilots.length" class="hall-empty">{{ t('hallOfFame.emptyPilots') }}</div>
      <PaginationControls v-model:page="pilotPage" :page-size="pageSize" :total-items="visiblePilots.length" />
    </div>

    <div v-else class="hall-table-wrap card">
      <table class="hall-table hall-team-table">
        <thead>
          <tr>
            <th>{{ t('hallOfFame.rank') }}</th>
            <th>{{ t('fields.team') }}</th>
            <th>{{ t('fields.participants') }}</th>
            <th>{{ t('hallOfFame.goldShort') }}</th>
            <th>{{ t('hallOfFame.silverShort') }}</th>
            <th>{{ t('hallOfFame.bronzeShort') }}</th>
            <th>{{ t('hallOfFame.podiums') }}</th>
            <th>{{ t('hallOfFame.averageRer') }}</th>
            <th>{{ t('hallOfFame.bestPilot') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(team, index) in pagedTeams" :key="team.id">
            <td><span class="hall-rank" :class="rankClass((teamPage - 1) * pageSize + index)">{{ (teamPage - 1) * pageSize + index + 1 }}</span></td>
            <td>
              <div class="hall-person-cell">
                <TeamAvatar mini :src="team.avatar_url" :color="team.avatar_color" :label="team.name" />
                <span class="hall-title">
                  <strong>{{ team.name }}</strong>
                  <span>{{ team.description || t('common.none') }}</span>
                </span>
              </div>
            </td>
            <td>{{ team.member_count }}</td>
            <td><span class="hall-medal-value gold">{{ team.gold }}</span></td>
            <td><span class="hall-medal-value silver">{{ team.silver }}</span></td>
            <td><span class="hall-medal-value bronze">{{ team.bronze }}</span></td>
            <td>{{ team.podiums }}</td>
            <td>{{ formatRating(team.average_rating) }}</td>
            <td>
              <RouterLink v-if="team.best_pilot" class="hall-best-link" :to="`/pilots/${team.best_pilot.id}`">
                <UserAvatar mini :src="team.best_pilot.avatar_url" :color="team.best_pilot.avatar_color" :label="pilotTitle(team.best_pilot)" />
                <span>
                  <strong>{{ pilotTitle(team.best_pilot) }}</strong>
                  <small>#{{ formatPilotNumber(team.best_pilot.pilot_number) }} - {{ teamShortName(team.best_pilot.team_name) }}</small>
                </span>
              </RouterLink>
              <span v-else>{{ t('common.none') }}</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!visibleTeams.length" class="hall-empty">{{ t('hallOfFame.emptyTeams') }}</div>
      <PaginationControls v-model:page="teamPage" :page-size="pageSize" :total-items="visibleTeams.length" />
    </div>
  </section>
</template>
