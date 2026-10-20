<script setup>
// Timing-screen standings for the Hall of Fame. One table for pilots or teams;
// on phones every row folds into a compact card.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import CountUp from '../../ui/fx/CountUp.vue'
import LicenseBadge from '../../components/LicenseBadge.vue'
import PilotRoles from '../../components/PilotRoles.vue'
import TeamAvatar from '../../components/TeamAvatar.vue'
import UserAvatar from '../../components/UserAvatar.vue'
import MedalPill from './MedalPill.vue'
import { formatPilotNumber, formatRating, pilotName, teamHref, teamShortName } from '../../pilotDisplay'
import { HALL_MODE_MEDALS, HALL_MODE_RATING } from './hallRanking'
import { useRanks } from '../../useRanks'
import RankAura from '../../ui/rank/RankAura.vue'

const props = defineProps({
  kind: { type: String, default: 'pilots' },
  /** Items of the current page, already ranked. */
  rows: { type: Array, required: true },
  /** Rank of the first row minus one. */
  offset: { type: Number, default: 0 },
  game: { type: String, required: true },
  /** What the standings are ordered by: it takes the highlighted last column. */
  mode: { type: String, default: HALL_MODE_MEDALS },
  /** (item, field) => number for the selected game. */
  stat: { type: Function, required: true },
  /** (item) => RER of a pilot or a team in the selected game. */
  rating: { type: Function, required: true },
  /** (team) => best pilot for the selected game or undefined. */
  bestPilot: { type: Function, required: true },
  /** Changing it re-runs the staggered row reveal. */
  revealKey: { type: String, default: '' }
})

const { t } = useI18n()
const { rankOf } = useRanks()
const isTeams = computed(() => props.kind === 'teams')
const byRating = computed(() => props.mode === HALL_MODE_RATING)
const rerLabel = computed(() => (isTeams.value ? t('hallOfFame.averageRer') : 'RER'))
const STAGGER = 45
const MAX_STAGGERED = 12

function place(index) {
  return props.offset + index + 1
}

function placeClass(index) {
  const value = place(index)
  return value <= 3 ? `is-p${value}` : ''
}

function pilotTitle(pilot) {
  return pilotName(pilot, pilot.login)
}

function ratingNumber(item) {
  return Math.round(Number(props.rating(item)) || 0)
}

function reveal(index) {
  return { delay: Math.min(index, MAX_STAGGERED) * STAGGER, y: 12, blur: 0, duration: 700 }
}
</script>

<template>
  <div class="standings">
    <table class="ui-table standings__table" :class="`is-${kind}`">
      <thead>
        <tr>
          <th class="c-pos">{{ t('hallOfFame.rank') }}</th>
          <th>{{ isTeams ? t('fields.team') : t('roles.pilot') }}</th>
          <th v-if="!isTeams">{{ t('fields.team') }}</th>
          <th v-else class="is-num">{{ t('fields.participants') }}</th>
          <th class="is-center"><i class="standings__dot is-gold" aria-hidden="true"></i>{{ t('hallOfFame.goldShort') }}</th>
          <th class="is-center"><i class="standings__dot is-silver" aria-hidden="true"></i>{{ t('hallOfFame.silverShort') }}</th>
          <th class="is-center"><i class="standings__dot is-bronze" aria-hidden="true"></i>{{ t('hallOfFame.bronzeShort') }}</th>
          <th class="is-num">{{ t('hallOfFame.podiums') }}</th>
          <th class="is-num">{{ byRating ? t('hallOfFame.points') : rerLabel }}</th>
          <th v-if="!isTeams" class="is-num">SR</th>
          <th v-else>{{ t('hallOfFame.bestPilot') }}</th>
          <th class="is-num c-pts-head">{{ byRating ? rerLabel : t('hallOfFame.points') }}</th>
        </tr>
      </thead>

      <tbody v-if="!isTeams" :key="revealKey">
        <tr v-for="(pilot, index) in rows" :key="pilot.id" v-reveal="reveal(index)" class="standings__row rank-surface" :class="placeClass(index)" :data-rank="rankOf(pilot)">
          <td class="c-pos"><RankAura :rank="rankOf(pilot)" :seed="pilot.id" /><span class="ui-pos" :class="place(index) <= 3 ? `ui-pos--${place(index)}` : ''">{{ place(index) }}</span></td>
          <td class="c-who">
            <RouterLink class="standings__who" :to="`/pilots/${pilot.id}`">
              <UserAvatar mini class="standings__avatar rank-avatar" :data-rank="rankOf(pilot)" :src="pilot.avatar_url" :color="pilot.avatar_color" :label="pilotTitle(pilot)" />
              <span class="standings__name">
                <span class="standings__line">
                  <strong class="rank-name" :data-rank="rankOf(pilot)">{{ pilotTitle(pilot) }}</strong>
                  <LicenseBadge :user="pilot" :game="game" />
                  <PilotRoles :roles="pilot.pilot_roles" />
                </span>
                <small><b class="ui-num" :title="t('hallPage.table.number')">#{{ formatPilotNumber(pilot.pilot_number) }}</b>{{ pilot.nickname || pilot.login }}</small>
              </span>
            </RouterLink>
          </td>
          <td class="c-team">
            <RouterLink v-if="pilot.team_id" class="standings__team is-link" :to="teamHref(pilot.team_id)" :title="pilot.team_name || t('common.none')">
              {{ teamShortName(pilot.team_name, pilot.team_abbreviation) }}
            </RouterLink>
            <span v-else class="standings__team" :title="pilot.team_name || t('common.none')">{{ teamShortName(pilot.team_name, pilot.team_abbreviation) }}</span>
          </td>
          <td class="c-medal is-center"><MedalPill tone="gold" :value="stat(pilot, 'gold')" /></td>
          <td class="c-medal is-center"><MedalPill tone="silver" :value="stat(pilot, 'silver')" /></td>
          <td class="c-medal is-center"><MedalPill tone="bronze" :value="stat(pilot, 'bronze')" /></td>
          <td class="c-stat is-num" :data-label="t('hallOfFame.podiums')">{{ stat(pilot, 'podiums') }}</td>
          <td v-if="byRating" class="c-stat is-num" :data-label="t('hallOfFame.points')">{{ stat(pilot, 'points') }}</td>
          <td v-else class="c-stat is-num" data-label="RER">{{ formatRating(rating(pilot)) }}</td>
          <td class="c-stat is-num" data-label="SR">{{ Number(pilot.sr).toFixed(1) }}</td>
          <td v-if="byRating" class="c-pts is-num"><CountUp :value="ratingNumber(pilot)" :duration="1200" /><small>RER</small></td>
          <td v-else class="c-pts is-num"><CountUp :value="stat(pilot, 'points')" :duration="1200" /><small>{{ t('hallOfFame.pointsShort') }}</small></td>
        </tr>
      </tbody>

      <tbody v-else :key="revealKey">
        <tr v-for="(team, index) in rows" :key="team.id" v-reveal="reveal(index)" class="standings__row" :class="placeClass(index)">
          <td class="c-pos"><span class="ui-pos" :class="place(index) <= 3 ? `ui-pos--${place(index)}` : ''">{{ place(index) }}</span></td>
          <td class="c-who">
            <RouterLink class="standings__who" :to="teamHref(team.id)">
              <TeamAvatar mini class="standings__avatar is-team" :src="team.avatar_url" :color="team.avatar_color" :label="team.name" />
              <span class="standings__name">
                <span class="standings__line"><strong>{{ team.name }}</strong></span>
                <small><b class="ui-num">{{ team.abbreviation }}</b>{{ team.description || t('common.none') }}</small>
              </span>
            </RouterLink>
          </td>
          <td class="c-stat is-num" :data-label="t('fields.participants')">{{ team.member_count }}</td>
          <td class="c-medal is-center"><MedalPill tone="gold" :value="stat(team, 'gold')" /></td>
          <td class="c-medal is-center"><MedalPill tone="silver" :value="stat(team, 'silver')" /></td>
          <td class="c-medal is-center"><MedalPill tone="bronze" :value="stat(team, 'bronze')" /></td>
          <td class="c-stat is-num" :data-label="t('hallOfFame.podiums')">{{ stat(team, 'podiums') }}</td>
          <td v-if="byRating" class="c-stat is-num" :data-label="t('hallOfFame.points')">{{ stat(team, 'points') }}</td>
          <td v-else class="c-stat is-num" :data-label="t('hallOfFame.averageRer')">{{ formatRating(rating(team)) }}</td>
          <td class="c-best" :data-label="t('hallOfFame.bestPilot')">
            <RouterLink v-if="bestPilot(team)" class="standings__best" :to="`/pilots/${bestPilot(team).id}`">
              <UserAvatar mini class="standings__avatar is-small" :src="bestPilot(team).avatar_url" :color="bestPilot(team).avatar_color" :label="pilotTitle(bestPilot(team))" />
              <span class="standings__name">
                <span class="standings__line">
                  <strong>{{ pilotTitle(bestPilot(team)) }}</strong>
                  <LicenseBadge :user="bestPilot(team)" :game="game" />
                  <PilotRoles :roles="bestPilot(team)?.pilot_roles" />
                </span>
                <small><b class="ui-num">#{{ formatPilotNumber(bestPilot(team).pilot_number) }}</b>{{ teamShortName(bestPilot(team).team_name, bestPilot(team).team_abbreviation) }}</small>
              </span>
            </RouterLink>
            <span v-else class="standings__none">{{ t('common.none') }}</span>
          </td>
          <td v-if="byRating" class="c-pts is-num"><CountUp :value="ratingNumber(team)" :duration="1200" /><small>RER</small></td>
          <td v-else class="c-pts is-num"><CountUp :value="stat(team, 'points')" :duration="1200" /><small>{{ t('hallOfFame.pointsShort') }}</small></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.standings {
  width: 100%;
  overflow-x: auto;
}

.standings__table {
  min-width: 980px;
}

.standings__table.is-teams {
  min-width: 1120px;
}

.standings__table th {
  background: color-mix(in srgb, var(--c-surface-solid) 86%, var(--bm-blue));
}

.standings__table th:first-child {
  padding-left: 22px;
}

.standings__table th:last-child,
.standings__table td:last-child {
  padding-right: 22px;
}

.standings__dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 6px;
  border-radius: 50%;
  background: var(--bm-gold);
  vertical-align: 1px;
}

.standings__dot.is-silver {
  background: var(--bm-silver);
}

.standings__dot.is-bronze {
  background: var(--bm-bronze);
}

/* ---------- Rows ---------- */
.standings__row {
  --tone: transparent;
  position: relative;
}

.standings__row.is-p1 {
  --tone: var(--bm-gold);
}

.standings__row.is-p2 {
  --tone: var(--bm-silver);
}

.standings__row.is-p3 {
  --tone: var(--bm-bronze);
}

.standings__row td {
  transition: background-color var(--dur-2) var(--ease-out);
}

.standings__row.is-p1 td,
.standings__row.is-p2 td,
.standings__row.is-p3 td {
  background: color-mix(in srgb, var(--tone) 5%, transparent);
}

/* The left edge lights up in the row's colour (blue for the field). */
.standings__row td:first-child {
  padding-left: 22px;
  box-shadow: inset 3px 0 0 var(--tone);
  transition: box-shadow var(--dur-3) var(--ease-ios), background-color var(--dur-2);
}

.standings__row:hover td:first-child {
  box-shadow: inset 5px 0 0 color-mix(in srgb, var(--tone) 60%, var(--bm-blue-bright));
}

.standings__row:hover td {
  background: var(--c-blue-soft);
}

.c-pos {
  width: 64px;
}

.c-who {
  min-width: 240px;
}

/* ---------- Pilot / team cell ---------- */
.standings__who,
.standings__best {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  color: var(--c-text);
  text-decoration: none;
}

.standings__avatar {
  width: 38px;
  height: 38px;
  border-width: 1px;
  box-shadow: none;
  transition: transform var(--dur-3) var(--ease-spring);
}

.standings__avatar.is-small {
  width: 32px;
  height: 32px;
}

.standings__row:hover .standings__who .standings__avatar,
.standings__best:hover .standings__avatar {
  transform: scale(1.08);
}

.standings__name {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.standings__line {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.standings__line strong {
  min-width: 0;
  overflow: hidden;
  font-size: 14.5px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color var(--dur-2);
}

.standings__who:hover strong,
.standings__best:hover strong {
  color: var(--c-accent-text);
}

.standings__line :deep(.license-badge) {
  flex: 0 0 auto;
  font-size: 10px;
}

.standings__name small {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 360px;
  overflow: hidden;
  color: var(--c-text-3);
  font-size: 12.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.standings__name small b {
  flex: 0 0 auto;
  color: var(--c-text-2);
  font-size: 11.5px;
  font-weight: 600;
}

.standings__team {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-pill);
  background: var(--c-sunken);
  color: var(--c-text-2);
  font-family: var(--font-mono);
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-decoration: none;
  white-space: nowrap;
  transition: border-color var(--dur-2), color var(--dur-2), background-color var(--dur-2);
}

.standings__team.is-link:hover {
  border-color: var(--c-blue-line);
  background: var(--c-blue-soft);
  color: var(--c-accent-text);
}

.standings__none {
  color: var(--c-text-3);
}

.c-stat {
  color: var(--c-text-2);
}

.c-pts {
  color: var(--c-text);
  font-size: 17px;
  font-weight: 700;
}

.c-pts small {
  margin-left: 5px;
  color: var(--c-text-3);
  font-size: 10.5px;
  font-weight: 600;
  text-transform: uppercase;
}

.standings__row.is-p1 .c-pts {
  color: color-mix(in srgb, var(--bm-gold) 80%, var(--c-text));
}

.c-pts-head {
  color: var(--c-accent-text) !important;
}

/* ---------- Phones: each row folds into a compact card ---------- */
@media (max-width: 760px) {
  .standings {
    overflow: visible;
  }

  .standings__table,
  .standings__table.is-teams,
  .standings__table tbody {
    display: block;
    min-width: 0;
  }

  .standings__table thead {
    display: none;
  }

  .standings__row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 10px;
    padding: 14px 16px;
    border-bottom: 1px solid var(--c-line);
    background: color-mix(in srgb, var(--tone) 5%, transparent);
    box-shadow: inset 3px 0 0 var(--tone);
  }

  .standings__row:last-child {
    border-bottom: 0;
  }

  .standings__row td,
  .standings__row td:first-child,
  .standings__row td:last-child,
  .standings__row.is-p1 td,
  .standings__row.is-p2 td,
  .standings__row.is-p3 td,
  .standings__row:hover td {
    padding: 0;
    border: 0;
    background: transparent;
    box-shadow: none;
  }

  /* First line: place, name, points. Everything else wraps below. */
  .standings__row::after {
    order: 3;
    flex-basis: 100%;
    height: 0;
    content: '';
  }

  .c-pos {
    order: 0;
    width: auto;
  }

  .c-who {
    order: 1;
    flex: 1 1 0;
    min-width: 0;
  }

  .c-pts {
    order: 2;
    font-size: 18px;
  }

  .c-team,
  .c-medal,
  .c-stat,
  .c-best {
    order: 4;
  }

  .c-stat::before,
  .c-best::before {
    margin-right: 6px;
    color: var(--c-text-3);
    content: attr(data-label);
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .c-stat {
    font-size: 13px;
  }

  .c-best {
    display: flex;
    flex-basis: 100%;
    align-items: center;
    min-width: 0;
    padding-top: 4px !important;
  }

  .c-best .standings__best {
    flex: 1 1 0;
  }

  .c-who .standings__line :deep(.pilot-roles) {
    display: none;
  }

  .standings__avatar {
    width: 34px;
    height: 34px;
  }

  .standings__name small {
    max-width: 100%;
  }
}
</style>
