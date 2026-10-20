<script setup>
// Fan favourite vote after the flag: three nominees chosen by the stewards,
// one vote per viewer, live percentages once results are shown.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Check, Heart } from 'lucide-vue-next'
import LicenseBadge from '../../components/LicenseBadge.vue'
import PilotRoles from '../../components/PilotRoles.vue'
import UserAvatar from '../../components/UserAvatar.vue'
import EmptyState from '../../ui/EmptyState.vue'
import { formatRating, ratingForGame, teamShortName } from '../../pilotDisplay'
import { formatDateTime } from '../../timezone'
import { numberLabel, personName } from './raceFormat'

const props = defineProps({
  fanVote: { type: Object, default: null },
  game: { type: String, default: 'ACC' },
  voting: { type: Boolean, default: false }
})
const emit = defineEmits(['vote'])
const { t } = useI18n()

const options = computed(() => props.fanVote?.options || [])
const showResults = computed(() => Boolean(props.fanVote?.show_results))

function pilotName(item) {
  return personName(item, `${t('roles.pilot')} ${item.user_id}`)
}

function pilotSubtitle(item) {
  const team = teamShortName(item.team_name, item.team_abbreviation)
  return [numberLabel(item), `RER ${formatRating(ratingForGame(item, props.game))}`, `SR ${item.sr ?? '-'}`, team].filter(Boolean).join(' - ')
}

function percent(option) {
  const value = Number(option.percentage || 0)
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

function isMine(option) {
  return props.fanVote?.my_vote_user_id === option.user_id
}
</script>

<template>
  <section class="vote ui-card" aria-labelledby="race-vote-title">
    <header class="ui-card__head">
      <div class="ui-card__title">
        <p class="ui-eyebrow ui-eyebrow--accent"><Heart :size="13" />{{ t('racePage.vote.eyebrow') }}</p>
        <h2 id="race-vote-title">{{ t('raceDetails.fanVoteTitle') }}</h2>
      </div>
      <span v-if="fanVote?.enabled" class="ui-chip" :class="fanVote.is_open ? 'ui-chip--green' : ''">
        <span v-if="fanVote.is_open" class="ui-dot ui-dot--green ui-dot--live"></span>
        {{ fanVote.is_open ? t('common.open') : t('raceDetails.fanVoteResults') }}
      </span>
    </header>

    <p class="vote__hint">{{ t('raceDetails.fanVoteHint') }}</p>

    <div v-if="fanVote?.enabled" class="vote__status">
      <strong>{{ fanVote.is_open ? t('raceDetails.fanVoteOpenUntil', { date: fanVote.ends_at ? formatDateTime(fanVote.ends_at) : '-' }) : t('raceDetails.fanVoteClosed') }}</strong>
      <span class="ui-num">{{ t('raceDetails.fanVoteTotal', { count: fanVote.total_votes || 0 }) }}</span>
    </div>

    <ul v-if="options.length" class="vote__options">
      <li
        v-for="(option, index) in options"
        :key="option.user_id"
        v-reveal="{ delay: index * 90, y: 12 }"
        class="vote__option"
        :class="{ 'is-mine': isMine(option) }"
      >
        <UserAvatar class="vote__avatar" :src="option.avatar_url || ''" :color="option.avatar_color" :label="pilotName(option)" />
        <div class="vote__main">
          <span class="vote__name">
            <strong>{{ pilotName(option) }}</strong>
            <LicenseBadge :user="option" :game="game" />
            <PilotRoles :roles="option.pilot_roles" />
          </span>
          <span class="vote__sub">{{ pilotSubtitle(option) }}</span>
          <div v-if="showResults" class="vote__result">
            <span class="ui-meter"><span :style="{ '--value': `${Math.min(100, Number(option.percentage || 0))}%` }"></span></span>
            <strong class="ui-num">{{ t('raceDetails.fanVotePercent', { value: percent(option) }) }}</strong>
            <span class="ui-faint ui-num">{{ option.votes }}</span>
          </div>
        </div>
        <button
          v-if="fanVote?.is_open"
          v-spark
          class="ui-btn ui-btn--sm"
          :class="isMine(option) ? 'ui-btn--primary' : 'ui-btn--outline'"
          type="button"
          :disabled="voting"
          @click="emit('vote', option.user_id)"
        >
          <Check v-if="isMine(option)" :size="15" />
          <Heart v-else :size="15" />
          {{ isMine(option) ? t('raceDetails.fanVoteSelected') : t('raceDetails.fanVoteVote') }}
        </button>
      </li>
    </ul>
    <EmptyState v-else :icon="Heart" compact :title="t('raceDetails.fanVoteEmpty')" />
  </section>
</template>

<style scoped>
.vote__hint {
  margin: 0;
  color: var(--c-text-3);
  font-size: 13px;
}

.vote__status {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 6px 12px;
  padding: 10px 14px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  background: var(--c-sunken);
  font-size: 13.5px;
}

.vote__status span {
  color: var(--c-text-2);
  font-size: 12.5px;
}

.vote__options {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.vote__option {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-lg);
  background: var(--c-surface-solid);
  transition: border-color var(--dur-2), transform var(--dur-3) var(--ease-ios);
}

.vote__option:hover {
  border-color: var(--c-blue-line);
  transform: translateY(-2px);
}

.vote__option.is-mine {
  border-color: color-mix(in srgb, #f43f5e 45%, transparent);
  background: linear-gradient(120deg, color-mix(in srgb, #f43f5e 10%, transparent), var(--c-surface-solid) 70%);
}

.vote__avatar {
  width: 44px;
  height: 44px;
}

.vote__main {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.vote__name {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 8px;
  font-size: 14.5px;
}

.vote__name :deep(.pilot-roles) {
  margin-inline-start: 0;
}

.vote__sub {
  overflow: hidden;
  color: var(--c-text-3);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.vote__result {
  display: grid;
  grid-template-columns: minmax(40px, 1fr) auto auto;
  align-items: center;
  gap: 10px;
  margin-top: 4px;
  font-size: 13px;
}

@media (max-width: 520px) {
  .vote__option {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .vote__option .ui-btn {
    grid-column: 1 / -1;
  }
}
</style>
