<script setup>
import { ref } from 'vue'
import { X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import UserAvatar from './UserAvatar.vue'
import { statusLabel } from '../i18nLabels'
import { formatRating, teamShortName } from '../pilotDisplay'
import { state } from '../store'

const props = defineProps({
  open: {
    type: Boolean,
    default: false
  },
  penalties: {
    type: Array,
    default: () => []
  },
  appeals: {
    type: Array,
    default: () => []
  },
  participants: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['close', 'create-appeal'])
const { t } = useI18n()
const appealDrafts = ref({})

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
  return props.participants.find((item) => item.user_id === userId)
}

function penaltyTargetName(penalty) {
  const target = participantById(penalty.target_id)
  return target ? participantName(target) : `${t('roles.pilot')} ${penalty.target_id}`
}

function penaltyTargetSubtitle(penalty) {
  const target = participantById(penalty.target_id)
  return target ? `${participantSubtitle(target)} · RER ${formatRating(target.rating)} · ${teamShortName(target.team_name)}` : `ID ${penalty.target_id}`
}

function penaltyTargetColor(penalty) {
  return participantById(penalty.target_id)?.avatar_color || '#2563eb'
}

function penaltyTimeMs(penalty) {
  const value = Number(penalty.time_penalty_ms ?? 0)
  if (value > 0) return value
  return penalty.penalty_type === 'time' ? Number(penalty.penalty_value || 0) : 0
}

function penaltySrValue(penalty) {
  const value = Number(penalty.sr_penalty_value ?? 0)
  if (value > 0) return value
  return penalty.penalty_type === 'sr' ? Number(penalty.penalty_value || 0) : 0
}

function penaltyTypeLabel(penalty) {
  const hasTime = penaltyTimeMs(penalty) > 0
  const hasSr = penaltySrValue(penalty) > 0
  if (hasTime && hasSr) return t('raceDetails.combinedPenalty')
  return hasTime ? t('raceDetails.timePenalty') : t('raceDetails.srPenalty')
}

function penaltyValueLabel(penalty) {
  const values = []
  const timeMs = penaltyTimeMs(penalty)
  const srValue = penaltySrValue(penalty)
  if (timeMs > 0) values.push(`+${(timeMs / 1000).toFixed(1)}s`)
  if (srValue > 0) values.push(`-${srValue.toFixed(1)} SR`)
  return values.join(' + ')
}

function penaltyEffectLabel(penalty) {
  const effects = []
  const timeMs = penaltyTimeMs(penalty)
  const srValue = penaltySrValue(penalty)
  if (timeMs > 0) effects.push(t('raceDetails.timePenaltyEffect', { value: `${(timeMs / 1000).toFixed(1)}s` }))
  if (srValue > 0) effects.push(t('raceDetails.srPenaltyEffect', { value: `${srValue.toFixed(1)} SR` }))
  return effects.join(' / ')
}

function isOwnPenalty(penalty) {
  return penalty.target_id === state.user?.id
}

function appealForPenalty(penaltyId) {
  return props.appeals.find((item) => item.penalty_id === penaltyId)
}

function canAppealPenalty(penalty) {
  return isOwnPenalty(penalty) && penalty.status === 'active' && !appealForPenalty(penalty.id)
}

function appealDraft(penalty) {
  return appealDrafts.value[penalty.id] || { proof_link: '', description: '' }
}

function setAppealField(penalty, field, value) {
  const draft = appealDraft(penalty)
  appealDrafts.value = {
    ...appealDrafts.value,
    [penalty.id]: {
      ...draft,
      [field]: value
    }
  }
}

function submitAppeal(penalty) {
  const draft = appealDraft(penalty)
  emit('create-appeal', penalty, draft)
  appealDrafts.value = {
    ...appealDrafts.value,
    [penalty.id]: { proof_link: '', description: '' }
  }
}
</script>

<template>
  <div v-if="open" class="penalty-modal-backdrop" @click.self="$emit('close')">
    <article class="card penalty-modal race-penalties-modal">
      <div class="section-header penalty-modal-head">
        <div>
          <h2>{{ t('raceDetails.penalties') }}</h2>
          <p class="muted">{{ t('raceDetails.penaltiesCount', { count: penalties.length }) }}</p>
        </div>
        <button class="icon-button" type="button" :title="t('common.close')" :aria-label="t('common.close')" @click="$emit('close')">
          <X :size="18" />
        </button>
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

          <form v-if="canAppealPenalty(penalty)" class="form race-appeal-form" @submit.prevent="submitAppeal(penalty)">
            <label class="field">
              <span>{{ t('fields.proofLink') }}</span>
              <input :value="appealDraft(penalty).proof_link" type="url" required @input="setAppealField(penalty, 'proof_link', $event.target.value)" />
            </label>
            <label class="field">
              <span>{{ t('fields.description') }}</span>
              <textarea :value="appealDraft(penalty).description" required @input="setAppealField(penalty, 'description', $event.target.value)"></textarea>
            </label>
            <button class="button primary" type="submit">{{ t('raceDetails.appeal') }}</button>
          </form>
        </article>
      </div>

      <div v-else class="empty-row">{{ t('raceDetails.noPenalties') }}</div>
    </article>
  </div>
</template>
