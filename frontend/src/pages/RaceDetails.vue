<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import UserAvatar from '../components/UserAvatar.vue'
import { countryLabel, gameLabel, statusLabel } from '../i18nLabels'
import { state } from '../store'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const race = ref(null)
const penalties = ref([])
const appeals = ref([])
const car = ref('')
const error = ref('')
const actionPending = ref(false)
const appealForms = ref({})

const participants = computed(() => race.value?.registered_pilots || [])
const registered = computed(() => participants.value.some((item) => item.user_id === state.user?.id))
const canManageRace = computed(() => ['admin', 'moder'].includes(state.user?.role))

function formatDate(value) {
  return new Date(value).toLocaleString(state.locale, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function participantName(item) {
  const fullName = [item.first_name, item.last_name].filter(Boolean).join(' ')
  return fullName || item.nickname || item.login || `${t('roles.pilot')} ${item.user_id}`
}

function participantSubtitle(item) {
  const number = item.pilot_number ? `#${item.pilot_number}` : `ID ${item.user_id}`
  return item.nickname ? `${number} - ${item.nickname}` : number
}

function participantById(userId) {
  return participants.value.find((item) => item.user_id === userId)
}

function penaltyTargetName(penalty) {
  const target = participantById(penalty.target_id)
  return target ? participantName(target) : `${t('roles.pilot')} ${penalty.target_id}`
}

function penaltyTargetSubtitle(penalty) {
  const target = participantById(penalty.target_id)
  return target ? participantSubtitle(target) : `ID ${penalty.target_id}`
}

function penaltyTargetColor(penalty) {
  return participantById(penalty.target_id)?.avatar_color || '#2563eb'
}

function isOwnPenalty(penalty) {
  return penalty.target_id === state.user?.id
}

function penaltyTypeLabel(penalty) {
  return penalty.penalty_type === 'time' ? t('raceDetails.timePenalty') : t('raceDetails.srPenalty')
}

function penaltyValueLabel(penalty) {
  const value = Number(penalty.penalty_value)
  if (penalty.penalty_type === 'time') {
    return `+${(value / 1000).toFixed(1)}s`
  }
  return `-${value.toFixed(1)} SR`
}

function penaltyEffectLabel(penalty) {
  const value = Number(penalty.penalty_value)
  if (penalty.penalty_type === 'time') {
    return t('raceDetails.timePenaltyEffect', { value: `${(value / 1000).toFixed(1)}s` })
  }
  return t('raceDetails.srPenaltyEffect', { value: `${value.toFixed(1)} SR` })
}

function appealForm(penalty) {
  return appealForms.value[penalty.id] || { proof_link: '', description: '' }
}

function setAppealField(penalty, field, value) {
  const form = appealForm(penalty)
  appealForms.value = {
    ...appealForms.value,
    [penalty.id]: {
      ...form,
      [field]: value
    }
  }
}

async function load() {
  try {
    race.value = await api(`/races/${route.params.id}`)
    if (state.user) {
      penalties.value = await api(`/penalties?race_id=${route.params.id}`)
      appeals.value = await api('/appeals')
    }
    car.value = race.value.allowed_cars?.[0] || ''
  } catch (err) {
    error.value = err.message
  }
}

async function register() {
  race.value = await api(`/races/${race.value.id}/register`, { method: 'POST', body: { car_model: car.value } })
}

async function unregister() {
  race.value = await api(`/races/${race.value.id}/register`, { method: 'DELETE' })
}

async function closeRace() {
  if (!race.value || !window.confirm(t('raceDetails.confirmClose'))) return
  error.value = ''
  actionPending.value = true
  try {
    race.value = await api(`/races/${race.value.id}/close`, { method: 'POST' })
  } catch (err) {
    error.value = err.message
  } finally {
    actionPending.value = false
  }
}

async function deleteRace() {
  if (!race.value || !window.confirm(t('raceDetails.confirmDelete'))) return
  error.value = ''
  actionPending.value = true
  try {
    await api(`/races/${race.value.id}`, { method: 'DELETE' })
    router.push('/calendar')
  } catch (err) {
    error.value = err.message
    actionPending.value = false
  }
}

async function createAppeal(penalty) {
  const form = appealForm(penalty)
  await api('/appeals', { method: 'POST', body: { ...form, penalty_id: penalty.id, race_id: race.value.id } })
  appealForms.value = {
    ...appealForms.value,
    [penalty.id]: { proof_link: '', description: '' }
  }
  await load()
}

function appealForPenalty(penaltyId) {
  return appeals.value.find((item) => item.penalty_id === penaltyId)
}

function canAppealPenalty(penalty) {
  return isOwnPenalty(penalty) && penalty.status === 'active' && !appealForPenalty(penalty.id)
}

onMounted(load)
</script>

<template>
  <section class="section race-details-page">
    <p v-if="error" class="error">{{ error }}</p>

    <template v-if="race">
      <section class="card race-details-hero">
        <div class="section-header">
          <div class="race-details-title">
            <h1>{{ race.name }}</h1>
            <p class="muted">{{ gameLabel(t, race.game) }} - {{ race.track }} - {{ race.car_class }}</p>
          </div>
          <div v-if="canManageRace" class="toolbar">
            <RouterLink class="button" :to="`/races/${race.id}/edit`">{{ t('common.edit') }}</RouterLink>
            <button v-if="race.status !== 'finished'" class="button primary" type="button" :disabled="actionPending" @click="closeRace">{{ t('raceDetails.closeRace') }}</button>
            <button class="button danger" type="button" :disabled="actionPending" @click="deleteRace">{{ t('common.delete') }}</button>
          </div>
        </div>

        <p>{{ race.description }}</p>
        <div class="race-details-meta">
          <span class="status-badge race-status-badge" :class="`race-status-${race.status}`">{{ statusLabel(t, race.status) }}</span>
          <span>{{ formatDate(race.datetime_start) }}</span>
          <span>{{ formatDate(race.datetime_end) }}</span>
          <span>{{ participants.length }} / {{ race.max_pilots }}</span>
        </div>
        <p>{{ t('fields.server') }}: <a :href="race.server_link">{{ race.server_link }}</a></p>
        <p>{{ t('fields.mods') }}: {{ race.mods_pack?.join(', ') || t('common.none') }}</p>
      </section>

      <section v-if="race.status === 'registration_open' && state.user" class="card race-registration-panel">
        <div v-if="registered" class="section-header">
          <strong>{{ t('raceDetails.alreadyRegistered') }}</strong>
          <button class="button danger" @click="unregister">{{ t('common.unregister') }}</button>
        </div>
        <form v-else class="form" @submit.prevent="register">
          <label class="field">
            <span>{{ t('common.car') }}</span>
            <select v-model="car">
              <option v-for="item in race.allowed_cars" :key="item">{{ item }}</option>
            </select>
          </label>
          <button class="button primary" type="submit">{{ t('common.register') }}</button>
        </form>
      </section>

      <section class="card race-participants-panel">
        <div class="section-header">
          <div>
            <h2>{{ t('raceDetails.participants') }}</h2>
            <p class="muted">{{ t('raceDetails.registeredPilots', { count: participants.length }) }}</p>
          </div>
          <span class="pill">{{ participants.length }} / {{ race.max_pilots }}</span>
        </div>

        <div v-if="participants.length" class="race-participant-list">
          <article v-for="item in participants" :key="item.user_id" class="race-participant-row">
            <UserAvatar class="pilot-avatar-slot" :color="item.avatar_color" :label="participantName(item)" />
            <div class="race-participant-main">
              <strong>{{ participantName(item) }}</strong>
              <span>{{ participantSubtitle(item) }}</span>
            </div>
            <div class="race-participant-stat">
              <span>SR</span>
              <strong>{{ item.sr ?? '-' }}</strong>
            </div>
            <div class="race-participant-country">
              <span>{{ t('fields.country') }}</span>
              <strong>{{ countryLabel(t, item.country) }}</strong>
            </div>
            <div class="race-participant-car">
              <span>{{ t('common.car') }}</span>
              <strong>{{ item.car_model }}</strong>
            </div>
          </article>
        </div>

        <div v-else class="empty-row">{{ t('raceDetails.noRegisteredPilots') }}</div>
      </section>

      <section class="section race-penalties-section">
        <div class="section-header">
          <div>
            <h2>{{ t('raceDetails.penalties') }}</h2>
            <p class="muted">{{ t('raceDetails.penaltiesCount', { count: penalties.length }) }}</p>
          </div>
          <span class="pill">{{ penalties.length }}</span>
        </div>

        <div v-if="penalties.length" class="race-penalty-list">
          <article v-for="penalty in penalties" :key="penalty.id" class="card race-penalty-card" :class="{ 'is-own': isOwnPenalty(penalty) }">
            <div class="race-penalty-head">
              <div class="user-list-cell">
                <UserAvatar mini :color="penaltyTargetColor(penalty)" :label="penaltyTargetName(penalty)" />
                <div class="user-list-main">
                  <strong>{{ penaltyTargetName(penalty) }}</strong>
                  <span>{{ penaltyTargetSubtitle(penalty) }}</span>
                </div>
              </div>
              <div class="race-penalty-badges">
                <span v-if="isOwnPenalty(penalty)" class="pill">{{ t('raceDetails.yourPenalty') }}</span>
                <span class="status-badge" :class="`status-${penalty.status}`">{{ statusLabel(t, penalty.status) }}</span>
              </div>
            </div>

            <div class="race-penalty-summary">
              <div class="race-penalty-impact">
                <strong>{{ penaltyTypeLabel(penalty) }} - {{ penaltyValueLabel(penalty) }}</strong>
                <span>{{ penaltyEffectLabel(penalty) }}</span>
              </div>
              <span class="race-penalty-date">{{ formatDate(penalty.created_at) }}</span>
            </div>
            <p>{{ penalty.description }}</p>

            <div v-if="appealForPenalty(penalty.id)" class="race-appeal-state">
              <span class="pill">{{ t('raceDetails.appeal') }}: {{ statusLabel(t, appealForPenalty(penalty.id).status) }}</span>
              <p v-if="appealForPenalty(penalty.id)?.rejection_reason" class="muted">{{ appealForPenalty(penalty.id).rejection_reason }}</p>
            </div>

            <form v-if="canAppealPenalty(penalty)" class="form race-appeal-form" @submit.prevent="createAppeal(penalty)">
              <label class="field">
                <span>{{ t('fields.proofLink') }}</span>
                <input :value="appealForm(penalty).proof_link" type="url" required @input="setAppealField(penalty, 'proof_link', $event.target.value)" />
              </label>
              <label class="field">
                <span>{{ t('fields.description') }}</span>
                <textarea :value="appealForm(penalty).description" required @input="setAppealField(penalty, 'description', $event.target.value)"></textarea>
              </label>
              <button class="button primary" type="submit">{{ t('raceDetails.appeal') }}</button>
            </form>
          </article>
        </div>

        <div v-else class="empty-row">{{ t('raceDetails.noPenalties') }}</div>
      </section>
    </template>
  </section>
</template>
