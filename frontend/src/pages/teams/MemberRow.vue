<script setup>
// One pilot in a team roster or in the join requests list: position plate,
// avatar, name with licence and roles, rating and SR in mono.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { Crown } from 'lucide-vue-next'
import LicenseBadge from '../../components/LicenseBadge.vue'
import PilotRoles from '../../components/PilotRoles.vue'
import UserAvatar from '../../components/UserAvatar.vue'
import { formatPilotNumber, formatRating, pilotName, ratingForGame, teamShortName } from '../../pilotDisplay'
import { formatSr } from './teamUtils'
import RankAura from '../../ui/rank/RankAura.vue'
import { useRanks } from '../../useRanks'

const props = defineProps({
  member: { type: Object, required: true },
  game: { type: String, default: 'ACC' },
  /** 1-based place in the current order; hidden when null. */
  position: { type: Number, default: null },
  /** Paint places 1–3 gold, silver and bronze (only for real rankings). */
  podium: { type: Boolean, default: false },
  owner: { type: Boolean, default: false },
  teamName: { type: String, default: '' },
  teamAbbreviation: { type: String, default: '' },
  showGames: { type: Boolean, default: false },
  to: { type: String, default: '' }
})
const { t } = useI18n()
const { rankOf } = useRanks()
const rank = computed(() => rankOf(props.member))

const title = computed(() => pilotName(props.member, props.member.nickname || props.member.login))
const team = computed(() => {
  const name = props.member.team_name || props.teamName
  return name ? teamShortName(name, props.member.team_abbreviation || props.teamAbbreviation) : ''
})
const posClass = computed(() => (props.podium && props.position <= 3 ? `ui-pos--${props.position}` : ''))
</script>

<template>
  <div class="mrow rank-surface" :class="{ 'has-pos': position !== null, 'is-owner': owner }" :data-rank="rank">
    <RankAura :rank="rank" :seed="member.id || 0" />
    <span v-if="position !== null" class="ui-pos mrow__pos" :class="posClass">{{ position }}</span>
    <UserAvatar mini class="mrow__avatar rank-avatar" :data-rank="rank" :src="member.avatar_url" :color="member.avatar_color" :label="member.login" />

    <component :is="to ? RouterLink : 'span'" class="mrow__who" :to="to || undefined">
      <span class="mrow__name">
        <strong class="rank-name" :data-rank="rank">{{ title }}</strong>
        <LicenseBadge :user="member" :game="game" />
        <PilotRoles :roles="member.pilot_roles" />
      </span>
      <span class="mrow__sub">
        <span>{{ member.login }}</span>
        <span class="ui-num">#{{ formatPilotNumber(member.pilot_number) }}</span>
        <span v-if="team">{{ team }}</span>
        <template v-if="showGames && member.games?.length">
          <span v-for="item in member.games" :key="item" class="mrow__game">{{ t(`games.${item}`) }}</span>
        </template>
      </span>
    </component>

    <span v-if="owner" class="mrow__owner"><Crown :size="13" />{{ t('teams.owner') }}</span>

    <span class="mrow__stats">
      <span class="mrow__stat">
        <strong class="ui-num">{{ formatRating(ratingForGame(member, game)) }}</strong>
        <small>RER {{ game }}</small>
      </span>
      <span class="mrow__stat">
        <strong class="ui-num">{{ formatSr(member.sr) }}</strong>
        <small>SR</small>
      </span>
    </span>

    <span v-if="$slots.actions" class="mrow__actions"><slot name="actions" /></span>
  </div>
</template>

<style scoped>
.mrow {
  position: relative;
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr) auto auto auto;
  grid-template-areas: 'avatar who owner stats actions';
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid transparent;
  border-radius: var(--r-md);
  transition:
    background-color var(--dur-2) var(--ease-out),
    border-color var(--dur-2) var(--ease-out),
    transform var(--dur-3) var(--ease-ios);
}

.mrow.has-pos {
  grid-template-columns: 32px 40px minmax(0, 1fr) auto auto auto;
  grid-template-areas: 'pos avatar who owner stats actions';
}

.mrow:hover {
  border-color: var(--c-line);
  background: var(--c-blue-soft);
}

.mrow.is-owner {
  background: linear-gradient(90deg, color-mix(in srgb, var(--bm-gold) 9%, transparent), transparent 60%);
}

.mrow__pos {
  grid-area: pos;
  min-width: 30px;
}

.mrow__avatar {
  grid-area: avatar;
}

.mrow :deep(.mrow__avatar.user-avatar) {
  width: 40px;
  height: 40px;
  border-width: 1px;
  box-shadow: none;
}

.mrow__who {
  display: grid;
  grid-area: who;
  gap: 3px;
  min-width: 0;
  color: var(--c-text);
  text-decoration: none;
}

a.mrow__who:hover .mrow__name strong {
  color: var(--c-accent-text);
}

.mrow__name {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.mrow__name strong {
  overflow: hidden;
  font-size: 14.5px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color var(--dur-2);
}

.mrow__name :deep(.license-badge) {
  flex: 0 0 auto;
  font-size: 10px;
}

.mrow__name :deep(.pilot-roles) {
  margin-inline-start: 0;
}

.mrow__sub {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 10px;
  color: var(--c-text-3);
  font-size: 12.5px;
}

.mrow__game {
  padding: 1px 6px;
  border: 1px solid var(--c-line);
  border-radius: 6px;
  font-family: var(--font-mono);
  font-size: 10.5px;
  letter-spacing: 0.04em;
}

.mrow__owner {
  display: inline-flex;
  grid-area: owner;
  align-items: center;
  gap: 5px;
  padding: 4px 9px;
  border: 1px solid color-mix(in srgb, var(--bm-gold) 40%, transparent);
  border-radius: var(--r-pill);
  background: color-mix(in srgb, var(--bm-gold) 14%, transparent);
  color: color-mix(in srgb, var(--bm-gold) 80%, var(--c-text));
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
}

.mrow__stats {
  display: flex;
  grid-area: stats;
  gap: 18px;
}

.mrow__stat {
  display: grid;
  justify-items: end;
  gap: 1px;
  min-width: 52px;
}

.mrow__stat strong {
  color: var(--c-text);
  font-size: 15px;
  font-weight: 600;
}

.mrow__stat small {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  white-space: nowrap;
}

.mrow__actions {
  display: flex;
  grid-area: actions;
  gap: 6px;
}

@media (max-width: 640px) {
  .mrow,
  .mrow.has-pos {
    grid-template-columns: 40px minmax(0, 1fr) auto;
    grid-template-areas:
      'avatar who actions'
      'avatar stats owner';
    row-gap: 8px;
  }

  .mrow__pos {
    display: none;
  }

  .mrow__stats {
    justify-content: flex-start;
  }

  .mrow__stat {
    justify-items: start;
  }

  .mrow__owner {
    justify-self: end;
  }
}

@media (prefers-reduced-motion: reduce) {
  .mrow {
    transition: none;
  }
}
</style>
