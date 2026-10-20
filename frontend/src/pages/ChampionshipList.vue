<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { AlertTriangle, Flag, Plus, RefreshCw, X } from 'lucide-vue-next'
import { api } from '../api'
import EmptyState from '../ui/EmptyState.vue'
import PageHeader from '../ui/PageHeader.vue'
import { prefersReducedMotion } from '../ui/motion/env'
import { gameOptions } from '../i18nLabels'
import { state } from '../store'
import ChampionshipFormModal from './championships/ChampionshipFormModal.vue'
import ChampionshipHero from './championships/ChampionshipHero.vue'
import ChampionshipPicker from './championships/ChampionshipPicker.vue'
import ManagePanel from './championships/ManagePanel.vue'
import RegistrationPanel from './championships/RegistrationPanel.vue'
import StagesList from './championships/StagesList.vue'
import StandingsBoard from './championships/StandingsBoard.vue'
import {
  assetConfigForGame,
  carsForClasses,
  defaultChampionshipForm,
  defaultStage,
  optionalIso,
  parseCar,
  parsePilotNumber,
  pilotNumberDraft,
  toIso,
  toLocalInput
} from './championships/helpers'

const { t } = useI18n()
const championships = ref([])
const selectedId = ref(null)
const raceAssets = ref({ tracks: [], classes: [], games: {} })
const filter = ref('active')
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const listVersion = ref(0)
const createOpen = ref(false)
const editOpen = ref(false)
const applyPilotNumber = ref(pilotNumberDraft(state.user?.pilot_number))
const applyCar = ref('')
const myCarDraft = ref('')
const standingsPage = ref(1)
// The standings open folded on every championship: the top three, then the stages.
const standingsExpanded = ref(false)
const form = ref(defaultChampionshipForm())
const editForm = ref(defaultChampionshipForm())

const canManage = computed(() => ['admin', 'moder'].includes(state.user?.role))
const gameChoices = computed(() => gameOptions((key) => key, false))
const selected = computed(() => championships.value.find((item) => item.id === selectedId.value) || championships.value[0] || null)
const formRaceAssets = computed(() => assetConfigForGame(raceAssets.value, form.value.game))
const editRaceAssets = computed(() => assetConfigForGame(raceAssets.value, editForm.value.game))
const selectedRaceAssets = computed(() => assetConfigForGame(raceAssets.value, selected.value?.game || 'ACC'))
const selectedAllowedCars = computed(() => carsForClasses(selectedRaceAssets.value, new Set(selected.value?.classes || [])))
const standings = computed(() => selected.value?.standings || [])
const approvedRegistrations = computed(() => selected.value?.registrations?.filter((item) => item.status === 'approved') || [])
const myRegistration = computed(() => selected.value?.registrations?.find((item) => item.user_id === state.user?.id) || null)
const canChangeMyCar = computed(() => Boolean(selected.value?.car_change_allowed && myRegistration.value?.status === 'approved'))
const emptyText = computed(() => (filter.value === 'all' ? t('champPage.emptyAll') : t('champPage.emptyFiltered')))

function resetForm() {
  form.value = { ...defaultChampionshipForm(), stages: [{ ...defaultStage(), is_team_event: false }] }
}

function replaceChampionship(updated) {
  const exists = championships.value.some((item) => item.id === updated.id)
  championships.value = exists
    ? championships.value.map((item) => (item.id === updated.id ? updated : item))
    : [updated, ...championships.value]
}

function openCreate() {
  error.value = ''
  createOpen.value = true
}

function scrollToManage() {
  document.getElementById('champ-manage')?.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'start' })
}

async function loadChampionships() {
  loading.value = true
  error.value = ''
  try {
    const params = new URLSearchParams({ status_filter: filter.value, limit: '50' })
    championships.value = await api(`/championships?${params.toString()}`)
    listVersion.value += 1
    if (!selectedId.value || !championships.value.some((item) => item.id === selectedId.value)) {
      selectedId.value = championships.value[0]?.id || null
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function createChampionship() {
  saving.value = true
  error.value = ''
  try {
    const classes = form.value.classes
    if (!classes.length) throw new Error(t('championships.classRequired'))
    const stages = form.value.stages
      .filter((stage) => stage.datetime_start)
      .map((stage) => ({
        ...stage,
        datetime_start: toIso(stage.datetime_start),
        lmu_results_at: form.value.game === 'LMU' ? optionalIso(stage.lmu_results_at) : null,
        name: stage.name || null,
        track: stage.track || null,
        car_class: stage.car_class || null,
        server_link: stage.server_link || '',
        has_qualification: form.value.game === 'LMU' ? false : stage.has_qualification
      }))
    const created = await api('/championships', {
      method: 'POST',
      body: {
        ...form.value,
        classes,
        registration_start: toIso(form.value.registration_start),
        registration_end: toIso(form.value.registration_end),
        championship_start: toIso(form.value.championship_start),
        championship_end: toIso(form.value.championship_end),
        video_url: form.value.video_url || null,
        stages
      }
    })
    championships.value = [created, ...championships.value]
    selectedId.value = created.id
    createOpen.value = false
    resetForm()
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}

function startEditChampionship() {
  if (!selected.value) return
  editForm.value = {
    name: selected.value.name || '',
    description: selected.value.description || '',
    classes: [...(selected.value.classes || [])],
    registration_start: toLocalInput(selected.value.registration_start),
    registration_end: toLocalInput(selected.value.registration_end),
    championship_start: toLocalInput(selected.value.championship_start),
    championship_end: toLocalInput(selected.value.championship_end),
    video_url: selected.value.video_url || '',
    game: selected.value.game || 'ACC',
    car_change_allowed: Boolean(selected.value.car_change_allowed),
    scoring_system: selected.value.scoring_system || 'fia',
    pole_bonus_enabled: Boolean(selected.value.pole_bonus_enabled),
    is_team_event: Boolean(selected.value.is_team_event),
    is_published: Boolean(selected.value.is_published),
    stages: []
  }
  error.value = ''
  editOpen.value = true
}

async function updateChampionship() {
  if (!selected.value) return
  saving.value = true
  error.value = ''
  try {
    const classes = editForm.value.classes
    if (!classes.length) throw new Error(t('championships.classRequired'))
    const updated = await api(`/championships/${selected.value.id}`, {
      method: 'PATCH',
      body: {
        ...editForm.value,
        classes,
        registration_start: toIso(editForm.value.registration_start),
        registration_end: toIso(editForm.value.registration_end),
        championship_start: toIso(editForm.value.championship_start),
        championship_end: toIso(editForm.value.championship_end),
        video_url: editForm.value.video_url || null
      }
    })
    replaceChampionship(updated)
    editOpen.value = false
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}

async function deleteChampionship() {
  if (!selected.value || !window.confirm(t('championships.deleteConfirm', { name: selected.value.name }))) return
  saving.value = true
  error.value = ''
  try {
    const deletedId = selected.value.id
    await api(`/championships/${deletedId}`, { method: 'DELETE' })
    championships.value = championships.value.filter((item) => item.id !== deletedId)
    selectedId.value = championships.value[0]?.id || null
    editOpen.value = false
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}

async function applyToChampionship() {
  if (!selected.value) return
  error.value = ''
  try {
    const updated = await api(`/championships/${selected.value.id}/apply`, {
      method: 'POST',
      body: {
        pilot_number: parsePilotNumber(applyPilotNumber.value, t('championships.invalidPilotNumber')),
        car_model: parseCar(applyCar.value, t('championships.chooseCar'))
      }
    })
    replaceChampionship(updated)
  } catch (err) {
    error.value = err.message
  }
}

async function updateMyCar() {
  if (!selected.value) return
  error.value = ''
  try {
    const car = parseCar(myCarDraft.value, t('championships.chooseCar'))
    const updated = await api(`/championships/${selected.value.id}/me/car`, {
      method: 'PATCH',
      body: { car_model: car }
    })
    replaceChampionship(updated)
  } catch (err) {
    error.value = err.message
  }
}

onMounted(async () => {
  resetForm()
  await Promise.all([
    loadChampionships(),
    api('/race-assets').then((data) => {
      raceAssets.value = data
    }).catch((err) => {
      error.value = err.message
    })
  ])
})

watch(filter, loadChampionships)
watch(() => selected.value?.id, () => {
  standingsExpanded.value = false
})
// A team championship makes every drafted stage a team stage (and back).
watch(() => form.value.is_team_event, (value) => {
  form.value = { ...form.value, stages: form.value.stages.map((stage) => ({ ...stage, is_team_event: value })) }
})
// Any new version of the selected championship resets the per-championship drafts.
watch(selected, () => {
  standingsPage.value = 1
  myCarDraft.value = myRegistration.value?.car_model || ''
  applyPilotNumber.value = pilotNumberDraft(state.user?.pilot_number)
  applyCar.value = ''
  editOpen.value = false
})
</script>

<template>
  <div class="ui-page ui-shell ui-shell--wide champs">
    <PageHeader :eyebrow="t('champPage.eyebrow')" :title="t('championships.title')" :lead="t('champPage.lead')">
      <template #actions>
        <button class="ui-btn ui-btn--outline" type="button" :disabled="loading" @click="loadChampionships">
          <RefreshCw :size="16" :class="{ 'champs__spin': loading }" />{{ t('common.reload') }}
        </button>
        <button v-if="canManage" v-magnet class="ui-btn ui-btn--primary" type="button" @click="openCreate">
          <Plus :size="16" />{{ t('champPage.create') }}
        </button>
      </template>
    </PageHeader>

    <Transition name="ui-fade">
      <p v-if="error" class="ui-alert champs__alert" role="alert">
        <AlertTriangle :size="18" />
        <span class="champs__alert-text">{{ error }}</span>
        <button class="ui-btn ui-btn--ghost ui-btn--sm ui-btn--icon" type="button" :aria-label="t('common.close')" @click="error = ''"><X :size="16" /></button>
      </p>
    </Transition>

    <ChampionshipPicker
      v-model:filter="filter"
      v-model:selected-id="selectedId"
      :championships="championships"
      :selected="selected"
      :list-key="listVersion"
    />

    <Transition name="champ-swap" mode="out-in">
      <div v-if="selected" :key="selected.id" class="champs__detail">
        <ChampionshipHero :championship="selected" :assets="raceAssets" :can-manage="canManage" @manage="scrollToManage">
          <template #aside>
            <RegistrationPanel
              v-model:pilot-number="applyPilotNumber"
              v-model:car="applyCar"
              v-model:my-car="myCarDraft"
              :championship="selected"
              :allowed-cars="selectedAllowedCars"
              :my-registration="myRegistration"
              :can-change-my-car="canChangeMyCar"
              @apply="applyToChampionship"
              @change-car="updateMyCar"
            />
          </template>
        </ChampionshipHero>

        <div class="champs__sections" :class="{ 'is-standings-first': standings.length }">
          <StandingsBoard
            v-model:page="standingsPage"
            v-model:expanded="standingsExpanded"
            class="champs__standings"
            :standings="standings"
            :game="selected.game"
            :registrations="approvedRegistrations"
          />
          <StagesList class="champs__stages" :stages="selected.stages || []" :assets="raceAssets" />
        </div>

        <ManagePanel
          v-if="canManage"
          id="champ-manage"
          class="champs__manage"
          :championship="selected"
          :allowed-cars="selectedAllowedCars"
          :assets="selectedRaceAssets"
          :saving="saving"
          @updated="replaceChampionship"
          @error="error = $event"
          @edit="startEditChampionship"
          @delete="deleteChampionship"
        />
      </div>
      <EmptyState v-else-if="loading" key="loading" loading :title="t('ui.common.loading')" />
      <EmptyState v-else key="empty" :icon="Flag" :title="t('championships.noItems')" :text="emptyText">
        <button v-if="filter !== 'all'" class="ui-btn ui-btn--outline ui-btn--sm" type="button" @click="filter = 'all'">{{ t('champPage.showAll') }}</button>
      </EmptyState>
    </Transition>

    <template v-if="canManage">
      <ChampionshipFormModal
        v-model:form="form"
        mode="create"
        :open="createOpen"
        :assets="formRaceAssets"
        :game-choices="gameChoices"
        :saving="saving"
        :error="createOpen ? error : ''"
        @submit="createChampionship"
        @close="createOpen = false"
      />
      <ChampionshipFormModal
        v-model:form="editForm"
        mode="edit"
        :open="editOpen"
        :assets="editRaceAssets"
        :game-choices="gameChoices"
        :saving="saving"
        :error="editOpen ? error : ''"
        @submit="updateChampionship"
        @close="editOpen = false"
      />
    </template>
  </div>
</template>

<style scoped>
.champs__alert {
  position: sticky;
  top: calc(var(--header-h) + 12px);
  z-index: 30;
  align-items: center;
  background: color-mix(in srgb, var(--bm-red) 12%, var(--c-surface-solid));
  box-shadow: var(--shadow-1);
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
}

.champs__alert-text {
  flex: 1 1 auto;
}

.champs__spin {
  animation: champs-spin 900ms linear infinite;
}

.champs__detail {
  display: grid;
  gap: clamp(18px, 2.4vw, 28px);
  min-width: 0;
}

.champs__sections {
  display: grid;
  gap: clamp(18px, 2.4vw, 28px);
  min-width: 0;
}

/* Before results exist the calendar matters most; afterwards the table does. */
.champs__standings {
  order: 2;
}

.champs__stages {
  order: 1;
}

.champs__sections.is-standings-first .champs__standings {
  order: 1;
}

.champs__sections.is-standings-first .champs__stages {
  order: 2;
}

.champs__manage {
  scroll-margin-top: calc(var(--header-h) + 16px);
}

/* Switching championships: the old one dims away, the new one settles in. */
.champ-swap-enter-active {
  transition:
    opacity 420ms var(--ease-out),
    transform 560ms var(--ease-ios),
    filter 420ms var(--ease-out);
}

.champ-swap-leave-active {
  transition:
    opacity 180ms ease-in,
    transform 200ms ease-in,
    filter 180ms ease-in;
}

.champ-swap-enter-from {
  opacity: 0;
  filter: blur(8px);
  transform: translate3d(0, 18px, 0) scale(0.995);
}

.champ-swap-leave-to {
  opacity: 0;
  filter: blur(4px);
  transform: scale(0.99);
}

@keyframes champs-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .champ-swap-enter-active,
  .champ-swap-leave-active {
    transition: none;
  }

  .champs__spin {
    animation: none;
  }
}
</style>
