<script setup>
import { nextTick, ref, watch } from 'vue'
import { Gavel, Link2, Scale, Send, Trash2, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import LicenseBadge from './LicenseBadge.vue'
import UserAvatar from './UserAvatar.vue'
import EmptyState from '../ui/EmptyState.vue'
import FormField from '../ui/FormField.vue'
import { statusLabel } from '../i18nLabels'
import { formatPilotNumber, formatRating, ratingForGame, teamShortName } from '../pilotDisplay'
import { state } from '../store'
import { formatDateTime } from '../timezone'

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
  },
  focusPenaltyId: {
    type: [Number, String],
    default: null
  },
  game: {
    type: String,
    default: 'ACC'
  },
  canCreate: {
    type: Boolean,
    default: false
  },
  canDelete: {
    type: Boolean,
    default: false
  },
  createOpen: {
    type: Boolean,
    default: false
  },
  busy: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'create-appeal', 'create-penalty', 'delete-penalty', 'update:createOpen'])
const { t } = useI18n()
const modalRoot = ref(null)
const appealDrafts = ref({})
const penaltyDraft = ref({
  target_id: '',
  time_seconds: 5,
  sr_penalty_value: 0.3,
  description: ''
})

function formatDate(value) {
  return formatDateTime(value)
}

function participantName(item) {
  const fullName = [item.first_name, item.last_name].filter(Boolean).join(' ')
  return fullName || item.nickname || item.login || `${t('roles.pilot')} ${item.user_id}`
}

function participantSubtitle(item) {
  const number = item.pilot_number !== null && item.pilot_number !== undefined ? `#${formatPilotNumber(item.pilot_number)}` : `ID ${item.user_id}`
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
  return target ? `${participantSubtitle(target)} · RER ${formatRating(ratingForGame(target, props.game))}${target.exclude_from_rer ? ` · ${t('common.rerExcluded')}` : ''} · ${teamShortName(target.team_name, target.team_abbreviation)}` : `ID ${penalty.target_id}`
}

function penaltyTargetColor(penalty) {
  return participantById(penalty.target_id)?.avatar_color || '#2563eb'
}

function penaltyTargetAvatar(penalty) {
  return participantById(penalty.target_id)?.avatar_url || ''
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

/** Chip tone for penalty and appeal statuses. */
function statusTone(status) {
  return { active: 'red', rejected: 'red', appealed: 'amber', pending: 'amber', approved: 'green' }[status] || ''
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

function toggleCreateForm() {
  emit('update:createOpen', !props.createOpen)
}

function submitPenalty() {
  const timeSeconds = Number(penaltyDraft.value.time_seconds)
  const srValue = Number(penaltyDraft.value.sr_penalty_value)
  emit('create-penalty', {
    target_id: Number(penaltyDraft.value.target_id),
    time_penalty_ms: Math.round(timeSeconds * 1000),
    sr_penalty_value: srValue,
    description: penaltyDraft.value.description.trim()
  })
}

async function focusPenaltyCard() {
  if (!props.open || props.focusPenaltyId === null || props.focusPenaltyId === undefined) return
  await nextTick()
  const card = modalRoot.value?.querySelector(`[data-penalty-id="${props.focusPenaltyId}"]`)
  card?.scrollIntoView({ block: 'center', behavior: 'auto' })
}

watch(() => [props.open, props.focusPenaltyId, props.penalties.length], focusPenaltyCard)
</script>

<template>
  <Teleport to="body">
    <Transition name="pm">
      <div v-if="open" class="ui-modal-backdrop pm-backdrop" @click.self="$emit('close')">
        <article ref="modalRoot" class="ui-modal ui-modal--wide pm" role="dialog" aria-modal="true" aria-labelledby="race-penalties-title">
          <header class="ui-modal__head pm__head">
            <div class="pm__title">
              <p class="ui-eyebrow ui-eyebrow--accent"><Scale :size="13" />{{ t('racePage.penalties.eyebrow') }}</p>
              <h2 id="race-penalties-title">{{ t('raceDetails.penalties') }}</h2>
              <p class="pm__count">{{ t('raceDetails.penaltiesCount', { count: penalties.length }) }}</p>
            </div>
            <div class="pm__tools">
              <button
                v-if="canCreate"
                class="ui-btn ui-btn--sm"
                :class="createOpen ? 'ui-btn--outline' : 'ui-btn--danger'"
                type="button"
                :disabled="!participants.length"
                @click="toggleCreateForm"
              >
                <Gavel v-if="!createOpen" :size="15" />
                {{ createOpen ? t('common.close') : t('raceDetails.issuePenalty') }}
              </button>
              <button class="ui-btn ui-btn--ghost ui-btn--icon ui-btn--sm" type="button" :title="t('common.close')" :aria-label="t('common.close')" @click="$emit('close')">
                <X :size="18" />
              </button>
            </div>
          </header>

          <Transition name="pm-drop">
            <form v-if="canCreate && createOpen" class="pm__create" @submit.prevent="submitPenalty">
              <div class="pm__create-grid">
                <FormField v-slot="{ id }" :label="t('roles.pilot')" required>
                  <select :id="id" v-model="penaltyDraft.target_id" class="ui-select" required>
                    <option value="" disabled>{{ t('raceDetails.selectPenaltyPilot') }}</option>
                    <option v-for="item in participants" :key="item.user_id" :value="item.user_id">
                      {{ participantName(item) }} #{{ item.pilot_number !== null && item.pilot_number !== undefined ? formatPilotNumber(item.pilot_number) : item.user_id }}
                    </option>
                  </select>
                </FormField>
                <FormField v-slot="{ id }" :label="t('raceDetails.timePenaltySeconds')" required>
                  <input :id="id" v-model.number="penaltyDraft.time_seconds" class="ui-input ui-num" type="number" min="0.1" step="0.1" required />
                </FormField>
                <FormField v-slot="{ id }" :label="t('raceDetails.srPenaltyValue')" required>
                  <input :id="id" v-model.number="penaltyDraft.sr_penalty_value" class="ui-input ui-num" type="number" min="0.1" step="0.1" required />
                </FormField>
              </div>
              <FormField v-slot="{ id }" :label="t('fields.description')" required>
                <textarea :id="id" v-model="penaltyDraft.description" class="ui-textarea" required :placeholder="t('raceDetails.penaltyDescriptionPlaceholder')"></textarea>
              </FormField>
              <div class="pm__create-actions">
                <button class="ui-btn ui-btn--danger" type="submit" :disabled="busy || !participants.length">
                  <Gavel :size="16" />{{ t('raceDetails.issuePenalty') }}
                </button>
              </div>
            </form>
          </Transition>

          <div v-if="penalties.length" class="pm__list">
            <article
              v-for="penalty in penalties"
              :key="penalty.id"
              class="pm__card"
              :class="{ 'is-own': isOwnPenalty(penalty), 'is-focused': Number(focusPenaltyId) === Number(penalty.id) }"
              :data-penalty-id="penalty.id"
            >
              <header class="pm__card-head">
                <div class="pm__who">
                  <UserAvatar mini :src="penaltyTargetAvatar(penalty)" :color="penaltyTargetColor(penalty)" :label="penaltyTargetName(penalty)" />
                  <div class="pm__who-main">
                    <span class="pm__name">
                      <strong>{{ penaltyTargetName(penalty) }}</strong>
                      <LicenseBadge :user="participantById(penalty.target_id)" :game="game" />
                    </span>
                    <span class="pm__sub">{{ penaltyTargetSubtitle(penalty) }}</span>
                  </div>
                </div>
                <div class="pm__badges">
                  <span v-if="isOwnPenalty(penalty)" class="ui-chip ui-chip--blue">{{ t('raceDetails.yourPenalty') }}</span>
                  <span class="ui-chip" :class="statusTone(penalty.status) ? `ui-chip--${statusTone(penalty.status)}` : ''">{{ statusLabel(t, penalty.status) }}</span>
                  <button
                    v-if="canDelete"
                    class="ui-btn ui-btn--danger ui-btn--icon ui-btn--sm"
                    type="button"
                    :title="t('common.delete')"
                    :aria-label="t('common.delete')"
                    @click="$emit('delete-penalty', penalty)"
                  >
                    <Trash2 :size="15" />
                  </button>
                </div>
              </header>

              <div class="pm__impact">
                <span class="pm__value ui-num">{{ penaltyValueLabel(penalty) }}</span>
                <div class="pm__impact-text">
                  <strong>{{ penaltyTypeLabel(penalty) }}</strong>
                  <span>{{ penaltyEffectLabel(penalty) }}</span>
                </div>
                <time class="pm__date ui-num">{{ formatDate(penalty.created_at) }}</time>
              </div>
              <p class="pm__desc">{{ penalty.description }}</p>

              <div v-if="appealForPenalty(penalty.id)" class="pm__appeal">
                <span class="ui-chip" :class="statusTone(appealForPenalty(penalty.id).status) ? `ui-chip--${statusTone(appealForPenalty(penalty.id).status)}` : ''">
                  {{ t('raceDetails.appeal') }}: {{ statusLabel(t, appealForPenalty(penalty.id).status) }}
                </span>
                <p v-if="appealForPenalty(penalty.id)?.rejection_reason" class="pm__reason">{{ appealForPenalty(penalty.id).rejection_reason }}</p>
              </div>

              <form v-if="canAppealPenalty(penalty)" class="pm__appeal-form" @submit.prevent="submitAppeal(penalty)">
                <p class="pm__appeal-lead">{{ t('racePage.penalties.appealLead') }}</p>
                <FormField v-slot="{ id, describedBy }" :label="t('fields.proofLink')" :hint="t('racePage.penalties.proofHint')" :icon="Link2" required>
                  <input
                    :id="id"
                    class="ui-input"
                    :value="appealDraft(penalty).proof_link"
                    type="url"
                    required
                    placeholder="https://"
                    :aria-describedby="describedBy"
                    @input="setAppealField(penalty, 'proof_link', $event.target.value)"
                  />
                </FormField>
                <FormField v-slot="{ id }" :label="t('fields.description')" required>
                  <textarea :id="id" class="ui-textarea" :value="appealDraft(penalty).description" required @input="setAppealField(penalty, 'description', $event.target.value)"></textarea>
                </FormField>
                <div class="pm__create-actions">
                  <button class="ui-btn ui-btn--primary" type="submit"><Send :size="16" />{{ t('raceDetails.appeal') }}</button>
                </div>
              </form>
            </article>
          </div>

          <EmptyState v-else :icon="Scale" compact :title="t('raceDetails.noPenalties')" :text="t('racePage.penalties.emptyText')" />
        </article>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.pm {
  gap: 18px;
}

.pm__title {
  display: grid;
  gap: 6px;
}

.pm__title h2 {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(18px, 2vw, 24px);
  text-transform: uppercase;
}

.pm__count {
  margin: 0;
  color: var(--c-text-3);
  font-size: 13px;
}

.pm__tools {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pm__create {
  display: grid;
  gap: 14px;
  padding: 16px;
  border: 1px solid color-mix(in srgb, var(--bm-red) 30%, var(--c-line));
  border-radius: var(--r-lg);
  background: color-mix(in srgb, var(--bm-red) 6%, var(--c-sunken));
}

.pm__create-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.pm__create-actions {
  display: flex;
  justify-content: flex-end;
}

.pm__list {
  display: grid;
  gap: 10px;
}

.pm__card {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-lg);
  background: var(--c-surface-solid);
  scroll-margin: 20px;
  transition: border-color var(--dur-2), box-shadow var(--dur-3);
}

.pm__card.is-own {
  border-color: var(--c-blue-line);
}

.pm__card.is-focused {
  border-color: var(--bm-red);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--bm-red) 18%, transparent);
  animation: pm-focus 1.4s var(--ease-out) 2;
}

@keyframes pm-focus {
  50% {
    box-shadow: 0 0 0 8px color-mix(in srgb, var(--bm-red) 10%, transparent);
  }
}

.pm__card-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.pm__who {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.pm__who-main {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.pm__name {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 8px;
  font-size: 14.5px;
}

.pm__sub {
  color: var(--c-text-3);
  font-size: 12.5px;
}

.pm__badges {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.pm__impact {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--r-md);
  background: var(--c-sunken);
}

.pm__value {
  padding: 6px 10px;
  border-radius: 9px;
  background: color-mix(in srgb, var(--bm-red) 14%, transparent);
  color: color-mix(in srgb, var(--bm-red) 85%, var(--c-text));
  font-size: 14px;
  font-weight: 800;
  white-space: nowrap;
}

.pm__impact-text {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.pm__impact-text strong {
  font-size: 13.5px;
}

.pm__impact-text span,
.pm__date {
  color: var(--c-text-3);
  font-size: 12px;
}

.pm__desc {
  margin: 0;
  color: var(--c-text-2);
  font-size: 14px;
  line-height: 1.55;
  white-space: pre-line;
}

.pm__appeal {
  display: grid;
  justify-items: start;
  gap: 6px;
}

.pm__reason {
  margin: 0;
  color: var(--c-text-2);
  font-size: 13px;
}

.pm__appeal-form {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--c-blue-line);
  border-radius: var(--r-md);
  background: var(--c-blue-soft);
}

.pm__appeal-lead {
  margin: 0;
  color: var(--c-text-2);
  font-size: 13px;
}

.pm-enter-active,
.pm-leave-active {
  transition: opacity var(--dur-2) var(--ease-out);
}

.pm-enter-active .pm,
.pm-leave-active .pm {
  transition: transform var(--dur-3) var(--ease-ios), filter var(--dur-2) var(--ease-out);
}

.pm-enter-from,
.pm-leave-to {
  opacity: 0;
}

.pm-enter-from .pm,
.pm-leave-to .pm {
  filter: blur(6px);
  transform: translateY(18px) scale(0.97);
}

.pm-drop-enter-active,
.pm-drop-leave-active {
  transition: opacity var(--dur-2) var(--ease-out), transform var(--dur-3) var(--ease-ios);
}

.pm-drop-enter-from,
.pm-drop-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.98);
}

@media (max-width: 640px) {
  .pm-backdrop {
    align-items: end;
    padding: 0;
  }

  .pm {
    max-height: 92dvh;
    border-radius: var(--r-xl) var(--r-xl) 0 0;
  }

  .pm__create-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .pm__impact {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .pm__date {
    grid-column: 1 / -1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .pm-enter-active,
  .pm-leave-active,
  .pm-enter-active .pm,
  .pm-leave-active .pm,
  .pm-drop-enter-active,
  .pm-drop-leave-active {
    transition: none;
  }

  .pm__card.is-focused {
    animation: none;
  }
}
</style>
