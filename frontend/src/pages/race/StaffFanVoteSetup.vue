<script setup>
// Staff: choose exactly three nominees and start (or restart) the fan vote.
import { useI18n } from 'vue-i18n'
import { Check, Heart } from 'lucide-vue-next'
import LicenseBadge from '../../components/LicenseBadge.vue'
import PilotRoles from '../../components/PilotRoles.vue'
import UserAvatar from '../../components/UserAvatar.vue'
import { formatRating, ratingForGame, teamShortName } from '../../pilotDisplay'
import { numberLabel, personName } from './raceFormat'

const props = defineProps({
  candidates: { type: Array, default: () => [] },
  selection: { type: Array, default: () => [] },
  enabled: { type: Boolean, default: false },
  canSave: { type: Boolean, default: false },
  game: { type: String, default: 'ACC' }
})
const emit = defineEmits(['toggle', 'submit'])
const { t } = useI18n()

function pilotName(item) {
  return personName(item, `${t('roles.pilot')} ${item.user_id}`)
}

function pilotSubtitle(item) {
  const team = teamShortName(item.team_name, item.team_abbreviation)
  return [numberLabel(item), `RER ${formatRating(ratingForGame(item, props.game))}`, `SR ${item.sr ?? '-'}`, team].filter(Boolean).join(' - ')
}

function isPicked(userId) {
  return props.selection.includes(Number(userId))
}
</script>

<template>
  <form class="staff-block" @submit.prevent="emit('submit')">
    <div class="staff-block__head fv-setup__head">
      <strong><Heart :size="15" /> {{ t('raceDetails.fanVoteSetupHint') }}</strong>
      <span class="ui-chip ui-chip--blue ui-num">{{ t('raceDetails.fanVoteChooseThree', { count: selection.length }) }}</span>
    </div>

    <div class="fv-setup__grid">
      <button
        v-for="item in candidates"
        :key="`fan-vote-${item.user_id}`"
        class="fv-setup__pilot"
        type="button"
        :class="{ 'is-picked': isPicked(item.user_id) }"
        :aria-pressed="isPicked(item.user_id)"
        :disabled="!isPicked(item.user_id) && selection.length >= 3"
        @click="emit('toggle', item.user_id)"
      >
        <UserAvatar mini :src="item.avatar_url || ''" :color="item.avatar_color" :label="pilotName(item)" />
        <span class="fv-setup__main">
          <span class="fv-setup__name">{{ pilotName(item) }}<LicenseBadge :user="item" :game="game" /><PilotRoles :roles="item.pilot_roles" /></span>
          <small>{{ pilotSubtitle(item) }}</small>
        </span>
        <span class="fv-setup__tick" aria-hidden="true"><Check :size="14" /></span>
      </button>
    </div>

    <div class="staff-actions">
      <button class="ui-btn ui-btn--primary" type="submit" :disabled="!canSave">
        <Heart :size="16" />{{ enabled ? t('raceDetails.fanVoteRestart') : t('raceDetails.fanVoteStart') }}
      </button>
    </div>
  </form>
</template>

<style scoped>
.staff-block .staff-block__head.fv-setup__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px 12px;
}

.fv-setup__head strong {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.fv-setup__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 8px;
}

.fv-setup__pilot {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  background: var(--c-surface-solid);
  color: var(--c-text);
  cursor: pointer;
  font: inherit;
  text-align: left;
  transition: border-color var(--dur-2), background-color var(--dur-2), transform var(--dur-2) var(--ease-ios);
}

.fv-setup__pilot:hover:not(:disabled) {
  border-color: var(--c-blue-line);
}

.fv-setup__pilot:active:not(:disabled) {
  transform: scale(0.98);
}

.fv-setup__pilot:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.fv-setup__pilot.is-picked {
  border-color: var(--bm-blue-bright);
  background: var(--c-blue-soft);
}

.fv-setup__main {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.fv-setup__name {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 6px;
  font-size: 13.5px;
  font-weight: 600;
}

.fv-setup__main small {
  overflow: hidden;
  color: var(--c-text-3);
  font-size: 11.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fv-setup__tick {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border: 1px solid var(--c-line-strong);
  border-radius: 50%;
  color: transparent;
  transition: background-color var(--dur-2), color var(--dur-2), transform var(--dur-3) var(--ease-spring);
}

.is-picked .fv-setup__tick {
  border-color: transparent;
  background: var(--bm-blue);
  color: #fff;
  transform: scale(1.08);
}
</style>
