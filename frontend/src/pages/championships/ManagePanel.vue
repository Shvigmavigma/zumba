<script setup>
// Staff tools for the selected championship, grouped in one card: pending
// requests, participants (add, change car, remove) and stages (add, edit,
// delete). Every action reports the updated championship back to the page.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Check, Pencil, Plus, RefreshCw, Search, ShieldCheck, Trash2, UserPlus, X } from 'lucide-vue-next'
import { api } from '../../api'
import EmptyState from '../../ui/EmptyState.vue'
import FormField from '../../ui/FormField.vue'
import SegmentedControl from '../../ui/SegmentedControl.vue'
import UserAvatar from '../../components/UserAvatar.vue'
import { statusLabel } from '../../i18nLabels'
import { formatPilotNumber, formatRating, pilotName, ratingForGame, teamShortName } from '../../pilotDisplay'
import { formatDateTime } from '../../timezone'
import StageFields from './StageFields.vue'
import { defaultStage, optionalIso, parseCar, parsePilotNumber, pilotNumberDraft, seasonProgress, toIso, toLocalInput } from './helpers'

const props = defineProps({
  championship: { type: Object, required: true },
  allowedCars: { type: Array, default: () => [] },
  /** Track/class lists for the championship's game. */
  assets: { type: Object, default: () => ({ tracks: [], classes: [] }) },
  saving: { type: Boolean, default: false }
})
const emit = defineEmits(['updated', 'error', 'edit', 'delete'])

const { t } = useI18n()
const tab = ref('requests')
const pilotSearch = ref('')
const pilotResults = ref([])
const pilotLoading = ref(false)
const addPilotId = ref('')
const addPilotCar = ref('')
const addPilotNumber = ref('')
const carDrafts = ref({})
const numberDrafts = ref({})
const stageCreateOpen = ref(false)
const stageForm = ref(defaultStage())
const stageEditForm = ref(defaultStage())
const editingStageId = ref(null)

const pendingRegistrations = computed(() => props.championship.registrations?.filter((item) => item.status === 'pending') || [])
const approvedRegistrations = computed(() => props.championship.registrations?.filter((item) => item.status === 'approved') || [])
const stages = computed(() => seasonProgress(props.championship.stages || []).stages)
const tabs = computed(() => [
  { value: 'requests', label: t('champPage.manage.requests'), count: pendingRegistrations.value.length },
  { value: 'participants', label: t('fields.participants'), count: approvedRegistrations.value.length },
  { value: 'stages', label: t('championships.stages'), count: stages.value.length }
])

function pilotTitle(user) {
  return pilotName(user, user.login)
}

function pilotLine(user, pilotNumber = user.pilot_number) {
  return [`#${formatPilotNumber(pilotNumber)}`, user.nickname, teamShortName(user.team_name, user.team_abbreviation), `RER ${formatRating(ratingForGame(user, props.championship.game))}`].filter(Boolean).join(' - ')
}

function resetStageForm() {
  stageForm.value = { ...defaultStage(), is_team_event: Boolean(props.championship.is_team_event) }
}

function resetStageEditForm() {
  stageEditForm.value = defaultStage()
  editingStageId.value = null
}

/** Runs one staff action; the page shows any error in its alert. */
async function run(action) {
  emit('error', '')
  try {
    const updated = await action()
    if (updated) emit('updated', updated)
    return updated
  } catch (err) {
    emit('error', err.message)
    return null
  }
}

const base = () => `/championships/${props.championship.id}`

function moderateRegistration(registration, status) {
  return run(() => api(`${base()}/registrations/${registration.id}`, {
    method: 'PATCH',
    body: {
      status,
      pilot_number: parsePilotNumber(numberDrafts.value[registration.user_id] || pilotNumberDraft(registration.pilot_number ?? registration.user.pilot_number), t('championships.invalidPilotNumber')),
      car_model: parseCar(carDrafts.value[registration.user_id] || registration.car_model, t('championships.chooseCar'))
    }
  }))
}

function removeParticipant(userId) {
  return run(() => api(`${base()}/participants/${userId}`, { method: 'DELETE' }))
}

/** Gives every participant the number from their profile; taken ones are replaced with free ones. */
function assignProfileNumbers() {
  if (props.championship.is_team_event || !window.confirm(t('championships.assignProfileNumbersConfirm', { name: props.championship.name }))) return null
  return run(() => api(`${base()}/registrations/assign-profile-numbers`, { method: 'POST' }))
}

function updateCar(userId) {
  return run(() => {
    const car = parseCar(carDrafts.value[userId], t('championships.chooseCar'))
    return api(`${base()}/participants/${userId}/car`, { method: 'PATCH', body: { car_model: car } })
  })
}

async function searchPilots() {
  pilotLoading.value = true
  try {
    const params = new URLSearchParams({ search: pilotSearch.value, limit: '20', rating_game: props.championship.game || 'ACC' })
    pilotResults.value = await api(`/users/pilots?${params.toString()}`)
  } catch (err) {
    emit('error', err.message)
  } finally {
    pilotLoading.value = false
  }
}

async function addParticipant() {
  if (!addPilotId.value || !addPilotNumber.value || !addPilotCar.value) return
  const updated = await run(() => api(`${base()}/participants`, {
    method: 'POST',
    body: {
      user_id: Number(addPilotId.value),
      pilot_number: parsePilotNumber(addPilotNumber.value, t('championships.invalidPilotNumber')),
      car_model: parseCar(addPilotCar.value, t('championships.chooseCar'))
    }
  }))
  if (!updated) return
  addPilotId.value = ''
  addPilotCar.value = ''
  addPilotNumber.value = ''
}

async function addStage() {
  if (!stageForm.value.datetime_start) return
  const isLmu = props.championship.game === 'LMU'
  const updated = await run(() => api(`${base()}/stages`, {
    method: 'POST',
    body: {
      ...stageForm.value,
      name: stageForm.value.name || null,
      track: stageForm.value.track || null,
      car_class: stageForm.value.car_class || null,
      server_link: stageForm.value.server_link || '',
      lmu_results_at: isLmu ? optionalIso(stageForm.value.lmu_results_at) : null,
      has_qualification: isLmu ? false : stageForm.value.has_qualification,
      datetime_start: toIso(stageForm.value.datetime_start)
    }
  }))
  if (!updated) return
  resetStageForm()
  stageCreateOpen.value = false
}

function startEditStage(stage) {
  editingStageId.value = stage.id
  stageEditForm.value = {
    name: stage.name || '',
    datetime_start: toLocalInput(stage.datetime_start),
    track: stage.track || '',
    car_class: stage.car_class || '',
    server_link: stage.server_link || '',
    lmu_results_at: stage.lmu_results_at ? toLocalInput(stage.lmu_results_at) : '',
    has_qualification: Boolean(stage.has_qualification),
    scoring_system: stage.scoring_system || 'fia',
    pole_bonus_enabled: Boolean(stage.pole_bonus_enabled),
    is_team_event: Boolean(stage.is_team_event)
  }
}

async function updateStage(stageId) {
  if (!stageEditForm.value.datetime_start) return
  const isLmu = props.championship.game === 'LMU'
  const updated = await run(() => api(`${base()}/stages/${stageId}`, {
    method: 'PATCH',
    body: {
      ...stageEditForm.value,
      track: stageEditForm.value.track || null,
      car_class: stageEditForm.value.car_class || null,
      server_link: stageEditForm.value.server_link || '',
      lmu_results_at: isLmu ? optionalIso(stageEditForm.value.lmu_results_at) : null,
      has_qualification: isLmu ? false : stageEditForm.value.has_qualification,
      datetime_start: toIso(stageEditForm.value.datetime_start)
    }
  }))
  if (updated) resetStageEditForm()
}

async function deleteStage(stage) {
  if (!window.confirm(t('championships.stageDeleteConfirm'))) return
  const updated = await run(() => api(`${base()}/stages/${stage.id}`, { method: 'DELETE' }))
  if (updated) resetStageEditForm()
}

function toggleStageCreate() {
  stageCreateOpen.value = !stageCreateOpen.value
}

function toggleStageEdit(stage) {
  if (editingStageId.value === stage.id) resetStageEditForm()
  else startEditStage(stage)
}

// Any new version of the championship refreshes the drafts and closes stage forms.
watch(() => props.championship, (championship) => {
  const drafts = {}
  const numbers = {}
  ;(championship?.registrations || []).forEach((item) => {
    drafts[item.user_id] = item.car_model || ''
    numbers[item.user_id] = pilotNumberDraft(item.pilot_number ?? item.user?.pilot_number)
  })
  carDrafts.value = drafts
  numberDrafts.value = numbers
  stageCreateOpen.value = false
  resetStageForm()
  resetStageEditForm()
}, { immediate: true })

watch(pilotSearch, () => {
  if (pilotSearch.value.trim().length >= 1) searchPilots()
  else pilotResults.value = []
})
</script>

<template>
  <section class="manage ui-card" aria-labelledby="champ-manage-title">
    <header class="manage__head">
      <div class="ui-card__title">
        <span class="ui-eyebrow manage__eyebrow"><ShieldCheck :size="14" />{{ t('champPage.manage.eyebrow') }}</span>
        <h3 id="champ-manage-title">{{ t('champPage.manage.title') }}</h3>
      </div>
      <div class="manage__actions">
        <span class="ui-chip" :class="championship.is_published ? 'ui-chip--green' : 'ui-chip--amber'">
          {{ championship.is_published ? t('champPage.manage.published') : t('champPage.unpublished') }}
        </span>
        <button class="ui-btn ui-btn--outline ui-btn--sm" type="button" @click="emit('edit')"><Pencil :size="15" />{{ t('champPage.manage.edit') }}</button>
        <button class="ui-btn ui-btn--danger ui-btn--sm" type="button" :disabled="saving" @click="emit('delete')"><Trash2 :size="15" />{{ t('championships.deleteChampionship') }}</button>
      </div>
    </header>

    <SegmentedControl v-model="tab" :options="tabs" :aria-label="t('champPage.manage.title')" />

    <Transition name="ui-fade" mode="out-in">
      <div v-if="tab === 'requests'" key="requests" class="manage__pane">
        <p class="manage__hint">{{ t('champPage.manage.requestsHint') }}</p>
        <TransitionGroup v-if="pendingRegistrations.length" tag="ul" name="ui-fade" class="manage__list">
          <li v-for="registration in pendingRegistrations" :key="registration.id" class="person person--request">
            <UserAvatar mini class="ui-avatar-sm" :src="registration.user.avatar_url" :color="registration.user.avatar_color" :label="pilotTitle(registration.user)" />
            <div class="person__who">
              <strong>{{ pilotTitle(registration.user) }}</strong>
              <small>{{ pilotLine(registration.user, registration.pilot_number) }}</small>
            </div>
            <input v-model="numberDrafts[registration.user_id]" class="ui-input manage__input manage__number ui-num" inputmode="numeric" pattern="[0-9]{3}" minlength="3" maxlength="3" :placeholder="t('fields.pilotNumber')" :aria-label="t('fields.pilotNumber')" />
            <select v-if="allowedCars.length" v-model="carDrafts[registration.user_id]" class="ui-select manage__input" required :aria-label="t('championships.car')">
              <option value="" disabled>{{ t('championships.chooseCar') }}</option>
              <option v-for="car in allowedCars" :key="car" :value="car">{{ car }}</option>
            </select>
            <input v-else v-model="carDrafts[registration.user_id]" class="ui-input manage__input" maxlength="80" required :aria-label="t('championships.car')" />
            <div class="person__buttons">
              <button class="ui-btn ui-btn--sm manage__approve" type="button" @click="moderateRegistration(registration, 'approved')"><Check :size="15" />{{ t('common.approve') }}</button>
              <button class="ui-btn ui-btn--danger ui-btn--sm ui-btn--icon" type="button" :title="t('common.reject')" :aria-label="t('common.reject')" @click="moderateRegistration(registration, 'rejected')"><X :size="15" /></button>
            </div>
          </li>
        </TransitionGroup>
        <EmptyState v-else :icon="Check" :title="t('championships.noPendingRequests')" compact />
      </div>

      <div v-else-if="tab === 'participants'" key="participants" class="manage__pane">
        <div class="manage__add ui-sunken">
          <p class="manage__sub">{{ t('championships.addPilot') }}</p>
          <div class="manage__add-grid">
            <FormField :label="t('champPage.manage.findPilot')" :icon="Search">
              <template #default="{ id }">
                <input :id="id" v-model="pilotSearch" class="ui-input" type="search" :placeholder="t('championships.pilotSearchPlaceholder')" />
              </template>
            </FormField>
            <FormField :label="t('championships.pilot')" :hint="pilotLoading ? t('ui.common.loading') : ''">
              <template #default="{ id }">
                <select :id="id" v-model="addPilotId" class="ui-select" :disabled="pilotLoading || !pilotResults.length">
                  <option value="">{{ t('championships.choosePilot') }}</option>
                  <option v-for="pilot in pilotResults" :key="pilot.id" :value="pilot.id">{{ pilotTitle(pilot) }} - #{{ formatPilotNumber(pilot.pilot_number) }}</option>
                </select>
              </template>
            </FormField>
            <FormField :label="t('fields.pilotNumber')">
              <template #default="{ id }">
                <input :id="id" v-model="addPilotNumber" class="ui-input ui-num" inputmode="numeric" pattern="[0-9]{3}" minlength="3" maxlength="3" placeholder="000" required />
              </template>
            </FormField>
            <FormField :label="t('championships.car')">
              <template #default="{ id }">
                <select v-if="allowedCars.length" :id="id" v-model="addPilotCar" class="ui-select" required>
                  <option value="" disabled>{{ t('championships.chooseCar') }}</option>
                  <option v-for="car in allowedCars" :key="car" :value="car">{{ car }}</option>
                </select>
                <input v-else :id="id" v-model="addPilotCar" class="ui-input" maxlength="80" required />
              </template>
            </FormField>
            <button class="ui-btn ui-btn--primary manage__add-btn" type="button" :disabled="!addPilotId || !addPilotNumber || !addPilotCar" @click="addParticipant">
              <UserPlus :size="16" />{{ t('common.add') }}
            </button>
          </div>
        </div>

        <div v-if="!championship.is_team_event && approvedRegistrations.length" class="manage__toolbar">
          <p class="manage__hint">{{ t('champPage.manage.profileNumbersHint') }}</p>
          <button class="ui-btn ui-btn--outline ui-btn--sm" type="button" :disabled="saving" @click="assignProfileNumbers">
            <RefreshCw :size="15" />{{ t('championships.assignProfileNumbers') }}
          </button>
        </div>

        <TransitionGroup v-if="approvedRegistrations.length" tag="ul" name="ui-fade" class="manage__list">
          <li v-for="registration in approvedRegistrations" :key="registration.id" class="person person--participant">
            <UserAvatar mini class="ui-avatar-sm" :src="registration.user.avatar_url" :color="registration.user.avatar_color" :label="pilotTitle(registration.user)" />
            <div class="person__who">
              <strong>{{ pilotTitle(registration.user) }}</strong>
              <small>{{ pilotLine(registration.user, registration.pilot_number) }}</small>
            </div>
            <select v-if="allowedCars.length" v-model="carDrafts[registration.user_id]" class="ui-select manage__input" required :aria-label="t('championships.car')">
              <option value="" disabled>{{ t('championships.chooseCar') }}</option>
              <option v-for="car in allowedCars" :key="car" :value="car">{{ car }}</option>
            </select>
            <input v-else v-model="carDrafts[registration.user_id]" class="ui-input manage__input" maxlength="80" required :aria-label="t('championships.car')" />
            <div class="person__buttons">
              <button class="ui-btn ui-btn--outline ui-btn--sm" type="button" @click="updateCar(registration.user_id)">{{ t('champPage.manage.saveCar') }}</button>
              <button class="ui-btn ui-btn--danger ui-btn--sm ui-btn--icon" type="button" :title="t('champPage.manage.removePilot')" :aria-label="t('champPage.manage.removePilot')" @click="removeParticipant(registration.user_id)"><Trash2 :size="15" /></button>
            </div>
          </li>
        </TransitionGroup>
        <EmptyState v-else :icon="UserPlus" :title="t('champPage.manage.noParticipants')" compact />
      </div>

      <div v-else key="stages" class="manage__pane">
        <div class="manage__toolbar">
          <p class="manage__hint">{{ t('champPage.manage.stagesHint') }}</p>
          <button class="ui-btn ui-btn--sm" :class="stageCreateOpen ? 'ui-btn--ghost' : 'ui-btn--primary'" type="button" @click="toggleStageCreate">
            <component :is="stageCreateOpen ? X : Plus" :size="15" />{{ stageCreateOpen ? t('common.close') : t('champPage.manage.addStage') }}
          </button>
        </div>

        <Transition name="ui-pop">
          <form v-if="stageCreateOpen" class="manage__stage-form ui-sunken" @submit.prevent="addStage">
            <p class="manage__sub">{{ t('champPage.manage.newStage') }}</p>
            <StageFields v-model="stageForm" :game="championship.game" :assets="assets" />
            <div class="manage__form-actions">
              <button class="ui-btn ui-btn--primary ui-btn--sm" type="submit"><Plus :size="15" />{{ t('common.create') }}</button>
            </div>
          </form>
        </Transition>

        <ul v-if="stages.length" class="manage__list">
          <li v-for="item in stages" :key="item.stage.id" class="manage__stage" :class="{ 'is-editing': editingStageId === item.stage.id }">
            <div class="manage__stage-row">
              <span class="manage__round ui-num">R{{ item.round }}</span>
              <div class="person__who">
                <strong>{{ item.stage.name }}</strong>
                <small>{{ [formatDateTime(item.stage.datetime_start), item.stage.track, item.stage.car_class].filter(Boolean).join(' · ') }}</small>
              </div>
              <span class="ui-chip">{{ statusLabel(t, item.stage.status) }}</span>
              <div class="person__buttons">
                <button class="ui-btn ui-btn--ghost ui-btn--sm ui-btn--icon" type="button" :title="t('championships.editStage')" :aria-label="t('championships.editStage')" :aria-expanded="editingStageId === item.stage.id" @click="toggleStageEdit(item.stage)"><Pencil :size="15" /></button>
                <button class="ui-btn ui-btn--danger ui-btn--sm ui-btn--icon" type="button" :title="t('championships.deleteStage')" :aria-label="t('championships.deleteStage')" :disabled="item.stage.status === 'finished'" @click="deleteStage(item.stage)"><Trash2 :size="15" /></button>
              </div>
            </div>
            <Transition name="ui-pop">
              <form v-if="editingStageId === item.stage.id" class="manage__stage-form" @submit.prevent="updateStage(item.stage.id)">
                <StageFields v-model="stageEditForm" :game="championship.game" :assets="assets" name-required />
                <div class="manage__form-actions">
                  <button class="ui-btn ui-btn--ghost ui-btn--sm" type="button" @click="resetStageEditForm">{{ t('champPage.form.cancel') }}</button>
                  <button class="ui-btn ui-btn--primary ui-btn--sm" type="submit">{{ t('common.save') }}</button>
                </div>
              </form>
            </Transition>
          </li>
        </ul>
        <EmptyState v-else-if="!stageCreateOpen" :icon="Plus" :title="t('champPage.stages.emptyTitle')" :text="t('champPage.manage.stagesEmpty')" compact />
      </div>
    </Transition>
  </section>
</template>

<style scoped>
.manage {
  border-color: color-mix(in srgb, var(--bm-amber) 22%, var(--c-line));
}

.manage__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px 16px;
}

.manage__eyebrow {
  color: color-mix(in srgb, var(--bm-amber) 80%, var(--c-text));
}

.manage__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.manage__pane {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.manage__hint {
  margin: 0;
  color: var(--c-text-3);
  font-size: 13px;
}

.manage__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.manage__sub {
  margin: 0;
  color: var(--c-text);
  font-size: 14px;
  font-weight: 650;
}

.manage__list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.person {
  display: grid;
  align-items: center;
  gap: 10px 12px;
  padding: 10px 12px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  background: var(--c-surface-solid);
}

.person--request {
  grid-template-columns: auto minmax(160px, 1fr) 110px minmax(160px, 240px) auto;
}

.person--participant {
  grid-template-columns: auto minmax(160px, 1fr) minmax(160px, 260px) auto;
}

.person__who {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.person__who strong {
  overflow: hidden;
  color: var(--c-text);
  font-size: 14px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.person__who small {
  overflow: hidden;
  color: var(--c-text-3);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.person__buttons {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}

.manage__input {
  min-height: 38px;
  font-size: 13.5px;
}

.manage__number {
  text-align: center;
}

.manage__approve {
  --btn-bg: color-mix(in srgb, var(--bm-green) 14%, transparent);
  --btn-fg: color-mix(in srgb, var(--bm-green) 80%, var(--c-text));
  --btn-line: color-mix(in srgb, var(--bm-green) 36%, transparent);
}

.manage__approve:hover {
  border-color: var(--bm-green);
}

.manage__add,
.manage__stage-form {
  display: grid;
  gap: 14px;
  padding: 16px;
  border-radius: var(--r-lg);
}

.manage__add-grid {
  display: grid;
  grid-template-columns: minmax(200px, 1.3fr) minmax(200px, 1.3fr) 120px minmax(180px, 1.2fr) auto;
  align-items: end;
  gap: 12px;
}

.manage__add-btn {
  min-height: 48px;
}

.manage__form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.manage__stage {
  display: grid;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  background: var(--c-surface-solid);
  transition: border-color var(--dur-2);
}

.manage__stage.is-editing {
  border-color: var(--c-blue-line);
}

.manage__stage .manage__stage-form {
  padding: 4px 0 2px;
}

.manage__stage-row {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 12px;
}

.manage__round {
  display: grid;
  place-items: center;
  height: 34px;
  border-radius: var(--r-xs);
  background: var(--c-sunken);
  color: var(--c-text);
  font-size: 13px;
  font-weight: 700;
}

@media (max-width: 1100px) {
  .manage__add-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .manage__add-btn {
    justify-self: start;
  }
}

@media (max-width: 860px) {
  .person--request,
  .person--participant {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .person--request .manage__input,
  .person--participant .manage__input,
  .person__buttons {
    grid-column: 1 / -1;
  }

  .person__buttons {
    justify-content: flex-start;
  }

  .manage__stage-row {
    grid-template-columns: 40px minmax(0, 1fr) auto;
  }

  .manage__stage-row .ui-chip {
    display: none;
  }
}

@media (max-width: 560px) {
  .manage__add-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
