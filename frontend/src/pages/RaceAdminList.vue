<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { Download, Eye, Pencil, Plus, RotateCw, SquareCheckBig, Trash2 } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import PaginationControls from '../components/PaginationControls.vue'
import { gameLabel, gameOptions, isExternalRace, raceOpenHref, statusLabel } from '../i18nLabels'
import { formatDateTime } from '../timezone'

const { t } = useI18n()
const races = ref([])
const search = ref('')
const statusFilter = ref('all')
const gameFilter = ref('all')
const error = ref('')
const busyRace = ref({})
const page = ref(1)
const pageSize = 25
const raceGameOptions = computed(() => gameOptions(t, true))

const statusOptions = computed(() => [
  { value: 'all', label: t('raceAdmin.allStatuses') },
  { value: 'not_finished', label: t('raceFilters.notFinished') },
  { value: 'registration_open', label: statusLabel(t, 'registration_open') },
  { value: 'ongoing', label: statusLabel(t, 'ongoing') },
  { value: 'finished', label: statusLabel(t, 'finished') }
])

const visibleCount = computed(() => races.value.length)
const hasNextPage = computed(() => races.value.length === pageSize)

function formatDate(value) {
  return formatDateTime(value)
}

function fillPercent(race) {
  if (race.game === 'LMU') return 0
  if (!race.max_pilots) return 0
  return Math.min(100, Math.round((race.registered_count / race.max_pilots) * 100))
}

async function load() {
  error.value = ''
  try {
    const params = new URLSearchParams({
      limit: String(pageSize),
      offset: String((page.value - 1) * pageSize),
      status_filter: statusFilter.value,
      game_filter: gameFilter.value
    })
    if (search.value.trim()) {
      params.set('search', search.value.trim())
    }
    races.value = await api(`/races/manage?${params.toString()}`)
  } catch (err) {
    error.value = err.message
  }
}

function applyFilters() {
  if (page.value === 1) {
    load()
    return
  }
  page.value = 1
}

async function closeRace(race) {
  if (!window.confirm(t('raceAdmin.confirmClose', { name: race.name }))) return
  busyRace.value = { ...busyRace.value, [race.id]: true }
  error.value = ''
  try {
    await api(`/races/${race.id}/close`, { method: 'POST' })
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    busyRace.value = { ...busyRace.value, [race.id]: false }
  }
}

async function deleteRace(race) {
  if (!window.confirm(t('raceAdmin.confirmDelete', { name: race.name }))) return
  busyRace.value = { ...busyRace.value, [race.id]: true }
  error.value = ''
  try {
    await api(`/races/${race.id}`, { method: 'DELETE' })
    races.value = races.value.filter((item) => item.id !== race.id)
  } catch (err) {
    error.value = err.message
  } finally {
    busyRace.value = { ...busyRace.value, [race.id]: false }
  }
}

async function exportRegistrations(race) {
  busyRace.value = { ...busyRace.value, [race.id]: true }
  error.value = ''
  try {
    const data = await api(`/races/${race.id}/registered-pilots`)
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = race.game === 'ACC'
      ? `race-${race.id}-entrylist.json`
      : race.is_team_event
      ? `race-${race.id}-team-registrations.json`
      : `race-${race.id}-registered-pilots.json`
    link.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    error.value = err.message
  } finally {
    busyRace.value = { ...busyRace.value, [race.id]: false }
  }
}

onMounted(load)
watch(page, load)
</script>

<template>
  <section class="section race-admin-page">
    <div class="section-header race-admin-header">
      <div>
        <h1>{{ t('raceAdmin.title') }}</h1>
        <p class="muted">{{ t('raceAdmin.loaded', { count: visibleCount }) }}</p>
      </div>
      <div class="toolbar">
        <button class="icon-button" type="button" :title="t('common.reload')" @click="load">
          <RotateCw :size="18" />
        </button>
        <RouterLink class="button primary" to="/races/new">
          <Plus :size="16" />
          {{ t('common.create') }}
        </RouterLink>
      </div>
    </div>

    <form class="race-admin-filters card" @submit.prevent="applyFilters">
      <label class="field">
        <span>{{ t('common.search') }}</span>
        <input v-model="search" :placeholder="t('raceAdmin.searchPlaceholder')" />
      </label>
      <label class="field">
        <span>{{ t('common.status') }}</span>
        <select v-model="statusFilter">
          <option v-for="option in statusOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
      </label>
      <label class="field">
        <span>{{ t('fields.game') }}</span>
        <select v-model="gameFilter">
          <option v-for="option in raceGameOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
      </label>
      <button class="button primary" type="submit">{{ t('common.apply') }}</button>
    </form>

    <p v-if="error" class="error">{{ error }}</p>

    <div class="race-admin-table-card card">
      <table class="race-admin-table">
        <thead>
          <tr>
            <th>{{ t('fields.race') }}</th>
            <th>{{ t('common.status') }}</th>
            <th>{{ t('fields.date') }}</th>
            <th>{{ t('fields.registrations') }}</th>
            <th>{{ t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="race in races" :key="race.id">
            <td>
              <div class="race-admin-title">
                <a v-if="isExternalRace(race)" :href="raceOpenHref(race)">{{ race.name }}</a>
                <RouterLink v-else :to="raceOpenHref(race)">{{ race.name }}</RouterLink>
                <p class="muted">
                  {{ [gameLabel(t, race.game), race.track, race.car_class, race.game !== 'LMU' ? (race.has_qualification ? t('raceDetails.withQualification') : t('raceDetails.withoutQualification')) : ''].filter(Boolean).join(' - ') }}
                  <template v-if="race.is_team_event"> - Командная</template>
                </p>
                <p>{{ race.description }}</p>
              </div>
            </td>
            <td>
              <span class="status-badge race-status-badge" :class="`race-status-${race.status}`">{{ statusLabel(t, race.status) }}</span>
            </td>
            <td>
              <div class="race-admin-date">
                <strong>{{ formatDate(race.datetime_start) }}</strong>
                <span>{{ formatDate(race.datetime_end) }}</span>
              </div>
            </td>
            <td>
              <div v-if="race.game !== 'LMU'" class="race-registration-cell">
                <strong>{{ race.registered_count }} / {{ race.max_pilots }}</strong>
                <span class="race-registration-meter">
                  <span :style="{ width: `${fillPercent(race)}%` }"></span>
                </span>
              </div>
              <span v-else class="muted">-</span>
            </td>
            <td>
              <div class="race-admin-actions">
                <a v-if="isExternalRace(race)" class="icon-button" :href="raceOpenHref(race)" :title="t('common.open')">
                  <Eye :size="16" />
                </a>
                <RouterLink v-else class="icon-button" :to="raceOpenHref(race)" :title="t('common.open')">
                  <Eye :size="16" />
                </RouterLink>
                <RouterLink class="icon-button" :to="`/races/${race.id}/edit`" :title="t('common.edit')">
                  <Pencil :size="16" />
                </RouterLink>
                <button
                  v-if="race.status !== 'finished'"
                  class="icon-button"
                  type="button"
                  :title="t('common.close')"
                  :disabled="busyRace[race.id]"
                  @click="closeRace(race)"
                >
                  <SquareCheckBig :size="16" />
                </button>
                <button class="icon-button" type="button" :title="t('raceAdmin.exportRegistrations')" :disabled="busyRace[race.id]" @click="exportRegistrations(race)">
                  <Download :size="16" />
                </button>
                <button class="icon-button danger-icon" type="button" :title="t('common.delete')" :disabled="busyRace[race.id]" @click="deleteRace(race)">
                  <Trash2 :size="16" />
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="!races.length">
            <td colspan="5">
              <div class="empty-row">{{ t('raceAdmin.noRacesFound') }}</div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <PaginationControls v-model:page="page" :page-size="pageSize" :loaded-count="races.length" :has-next="hasNextPage" />
  </section>
</template>
