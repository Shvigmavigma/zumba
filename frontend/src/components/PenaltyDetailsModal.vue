<script setup>
import { X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { statusLabel } from '../i18nLabels'
import { formatRating, teamShortName } from '../pilotDisplay'

defineProps({
  penalty: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: ''
  }
})

defineEmits(['close'])

const { t } = useI18n()

function formatDate(value) {
  if (!value) return t('common.none')
  return new Date(value).toLocaleString(undefined, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function penaltyTypeLabel(penalty) {
  const hasTime = penaltyTimeMs(penalty) > 0
  const hasSr = penaltySrValue(penalty) > 0
  if (hasTime && hasSr) return t('raceDetails.combinedPenalty')
  return hasTime ? t('raceDetails.timePenalty') : t('raceDetails.srPenalty')
}

function penaltyTimeMs(penalty) {
  const value = Number(penalty?.time_penalty_ms ?? 0)
  if (value > 0) return value
  return penalty?.penalty_type === 'time' ? Number(penalty?.penalty_value || 0) : 0
}

function penaltySrValue(penalty) {
  const value = Number(penalty?.sr_penalty_value ?? 0)
  if (value > 0) return value
  return penalty?.penalty_type === 'sr' ? Number(penalty?.penalty_value || 0) : 0
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

function targetName(penalty) {
  return penalty?.target_nickname || penalty?.target_login || `${t('roles.pilot')} #${penalty?.target_id}`
}

function issuerName(penalty) {
  return penalty?.issuer_nickname || penalty?.issuer_login || `#${penalty?.issuer_id}`
}

function userMeta(rating, teamName) {
  return `RER ${formatRating(rating)} · ${teamShortName(teamName)}`
}
</script>

<template>
  <div class="penalty-modal-backdrop" @click.self="$emit('close')">
    <article class="card penalty-modal">
      <div class="section-header penalty-modal-head">
        <div>
          <h2>{{ t('raceDetails.penaltyDetails') }}</h2>
          <p v-if="penalty" class="muted">#{{ penalty.id }}</p>
        </div>
        <button class="icon-button" type="button" :title="t('common.close')" :aria-label="t('common.close')" @click="$emit('close')">
          <X :size="18" />
        </button>
      </div>

      <div v-if="loading" class="empty-row">{{ t('common.loading') }}</div>
      <p v-else-if="error" class="error">{{ error }}</p>

      <template v-else-if="penalty">
        <dl class="penalty-detail-grid">
          <div>
            <dt>{{ t('common.status') }}</dt>
            <dd><span class="status-badge" :class="`status-${penalty.status}`">{{ statusLabel(t, penalty.status) }}</span></dd>
          </div>
          <div>
            <dt>{{ t('fields.race') }}</dt>
            <dd>{{ penalty.race_name || `#${penalty.race_id}` }}</dd>
          </div>
          <div>
            <dt>{{ t('fields.target') }}</dt>
            <dd>{{ targetName(penalty) }} <span v-if="penalty.target_pilot_number" class="muted">#{{ penalty.target_pilot_number }} · {{ userMeta(penalty.target_rating, penalty.target_team_name) }}</span></dd>
          </div>
          <div>
            <dt>{{ t('fields.issuer') }}</dt>
            <dd>{{ issuerName(penalty) }} <span class="muted">{{ userMeta(penalty.issuer_rating, penalty.issuer_team_name) }}</span></dd>
          </div>
          <div>
            <dt>{{ t('fields.type') }}</dt>
            <dd>{{ penaltyTypeLabel(penalty) }}</dd>
          </div>
          <div>
            <dt>{{ t('fields.value') }}</dt>
            <dd>{{ penaltyValueLabel(penalty) }}</dd>
          </div>
          <div>
            <dt>{{ t('raceDetails.penaltyEffect') }}</dt>
            <dd>{{ penaltyEffectLabel(penalty) }}</dd>
          </div>
          <div>
            <dt>{{ t('fields.applied') }}</dt>
            <dd>{{ penalty.is_applied ? t('common.yes') : t('common.no') }}</dd>
          </div>
          <div>
            <dt>{{ t('fields.date') }}</dt>
            <dd>{{ formatDate(penalty.created_at) }}</dd>
          </div>
        </dl>

        <div class="penalty-detail-description">
          <span>{{ t('fields.description') }}</span>
          <p>{{ penalty.description }}</p>
        </div>
      </template>
    </article>
  </div>
</template>
