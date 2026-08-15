<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Medal, RefreshCw, Search, Trophy, Users } from 'lucide-vue-next'
import { api } from '../api'
import LicenseBadge from '../components/LicenseBadge.vue'
import PaginationControls from '../components/PaginationControls.vue'
import TeamAvatar from '../components/TeamAvatar.vue'
import UserAvatar from '../components/UserAvatar.vue'
import { gameOptions } from '../i18nLabels'
import { OVERALL_RATING_GAME, formatPilotNumber, formatRating, pilotName, ratingForGame, teamHref, teamShortName } from '../pilotDisplay'

const { t } = useI18n()

const data = ref({ pilots: [], teams: [] })
const activeTab = ref('pilots')
const search = ref('')
const ratingGame = ref(OVERALL_RATING_GAME)
const loading = ref(false)
const error = ref('')
const pilotPage = ref(1)
const teamPage = ref(1)
const pageSize = 20
const ratingGameOptions = computed(() => gameOptions(t, true))

const tabs = computed(() => [
  { id: 'pilots', label: t('hallOfFame.pilotsTab'), count: rankedPilots.value.length },
  { id: 'teams', label: t('hallOfFame.teamsTab'), count: rankedTeams.value.length }
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

function statSource(item) {
  if (ratingGame.value === OVERALL_RATING_GAME) return item || {}
  return item?.stats_by_game?.[ratingGame.value] || {}
}

function statValue(item, field) {
  return Number(statSource(item)?.[field] || 0)
}

function rankItems(items) {
  return [...items]
    .filter((item) => statValue(item, 'points') > 0)
    .sort((left, right) => (
      statValue(right, 'points') - statValue(left, 'points') ||
      statValue(right, 'gold') - statValue(left, 'gold') ||
      statValue(right, 'silver') - statValue(left, 'silver') ||
      statValue(right, 'bronze') - statValue(left, 'bronze') ||
      Number(ratingForGame(right, ratingGame.value) || 0) - Number(ratingForGame(left, ratingGame.value) || 0) ||
      String(left.nickname || left.name || '').localeCompare(String(right.nickname || right.name || ''), undefined, { sensitivity: 'base' })
    ))
}

function bestPilotFor(team) {
  return ratingGame.value === OVERALL_RATING_GAME ? team.best_pilot : team.best_pilots_by_game?.[ratingGame.value]
}

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
    statValue(pilot, 'points'),
    statValue(pilot, 'gold'),
    statValue(pilot, 'silver'),
    statValue(pilot, 'bronze'),
    ratingForGame(pilot, ratingGame.value),
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
    team.average_rating,
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
watch(ratingGame, () => {
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
      <select v-model="ratingGame" class="pilot-list-sort" :aria-label="t('fields.game')">
        <option v-for="option in ratingGameOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
      </select>
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
                  <span class="user-name-line">
                    <strong>{{ pilotTitle(pilot) }}</strong>
                    <LicenseBadge :user="pilot" :game="ratingGame" />
                  </span>
                  <span>{{ pilotLine(pilot) }}</span>
                </RouterLink>
              </div>
            </td>
            <td>
              <RouterLink v-if="pilot.team_id" class="team-mini-chip team-link-chip" :to="teamHref(pilot.team_id)" :title="pilot.team_name || t('common.none')">
                {{ teamShortName(pilot.team_name, pilot.team_abbreviation) }}
              </RouterLink>
              <span v-else class="team-mini-chip" :title="pilot.team_name || t('common.none')">{{ teamShortName(pilot.team_name, pilot.team_abbreviation) }}</span>
            </td>
            <td><span class="hall-medal-value gold">{{ statValue(pilot, 'gold') }}</span></td>
            <td><span class="hall-medal-value silver">{{ statValue(pilot, 'silver') }}</span></td>
            <td><span class="hall-medal-value bronze">{{ statValue(pilot, 'bronze') }}</span></td>
            <td>{{ statValue(pilot, 'podiums') }}</td>
            <td>{{ formatRating(ratingForGame(pilot, ratingGame)) }}</td>
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
                <RouterLink class="hall-title" :to="teamHref(team.id)">
                  <strong>{{ team.name }}</strong>
                  <span>{{ team.abbreviation }} · {{ team.description || t('common.none') }}</span>
                </RouterLink>
              </div>
            </td>
            <td>{{ team.member_count }}</td>
            <td><span class="hall-medal-value gold">{{ statValue(team, 'gold') }}</span></td>
            <td><span class="hall-medal-value silver">{{ statValue(team, 'silver') }}</span></td>
            <td><span class="hall-medal-value bronze">{{ statValue(team, 'bronze') }}</span></td>
            <td>{{ statValue(team, 'podiums') }}</td>
            <td>{{ formatRating(team.average_rating) }}</td>
            <td>
              <RouterLink v-if="bestPilotFor(team)" class="hall-best-link" :to="`/pilots/${bestPilotFor(team).id}`">
                <UserAvatar mini :src="bestPilotFor(team).avatar_url" :color="bestPilotFor(team).avatar_color" :label="pilotTitle(bestPilotFor(team))" />
                <span>
                  <span class="user-name-line">
                    <strong>{{ pilotTitle(bestPilotFor(team)) }}</strong>
                    <LicenseBadge :user="bestPilotFor(team)" :game="ratingGame" />
                  </span>
                  <small>#{{ formatPilotNumber(bestPilotFor(team).pilot_number) }} - {{ teamShortName(bestPilotFor(team).team_name, bestPilotFor(team).team_abbreviation) }}</small>
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
