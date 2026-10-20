<script setup>
// Podium hero for the Hall of Fame: the top three of the current standings on
// gold, silver and bronze plates, the leader raised in the middle.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Crown } from 'lucide-vue-next'
import CountUp from '../../ui/fx/CountUp.vue'
import LicenseBadge from '../../components/LicenseBadge.vue'
import TeamAvatar from '../../components/TeamAvatar.vue'
import UserAvatar from '../../components/UserAvatar.vue'
import MedalPill from './MedalPill.vue'
import { formatPilotNumber, pilotName, teamHref, teamShortName } from '../../pilotDisplay'
import RankAura from '../../ui/rank/RankAura.vue'
import RankScene from '../../ui/rank/RankScene.vue'
import SeasonChampionBackdrop from '../../ui/rank/SeasonChampionBackdrop.vue'
import { SEASON_FINISH } from '../../ranks'
import { HALL_MODE_MEDALS, HALL_MODE_RATING } from './hallRanking'
import { useRanks } from '../../useRanks'

const props = defineProps({
  /** Ranked items, best first; only the first three are shown. */
  items: { type: Array, required: true },
  kind: { type: String, default: 'pilots' },
  game: { type: String, required: true },
  /** What the standings are ordered by: the big number on each plate. */
  mode: { type: String, default: HALL_MODE_MEDALS },
  /** (item, field) => number for the selected game. */
  stat: { type: Function, required: true },
  /** (item) => RER of a pilot or a team in the selected game. */
  rating: { type: Function, required: true }
})

const { t } = useI18n()
const isTeams = computed(() => props.kind === 'teams')
const { rankOf } = useRanks()
/** Only pilots have a rank; team plates keep the plain place finish. */
const rankKey = (item) => (isTeams.value ? 'rookie' : rankOf(item))
const REVEAL_DELAY = { 1: 260, 2: 120, 3: 0 }

const byRating = computed(() => props.mode === HALL_MODE_RATING)
const leaderScore = computed(() => (props.items[0] ? scoreOf(props.items[0]) : 0))

/** Display order on the podium: 2nd, 1st, 3rd. */
const places = computed(() => {
  const [first, second, third] = props.items
  return [
    second && { item: second, place: 2 },
    first && { item: first, place: 1 },
    third && { item: third, place: 3 }
  ].filter(Boolean)
})

function nameOf(item) {
  return isTeams.value ? item.name : pilotName(item, item.login)
}

function linkOf(item) {
  return isTeams.value ? teamHref(item.id) : `/pilots/${item.id}`
}

/** The number the plates are ordered by: RER, or podium points. */
function scoreOf(item) {
  return byRating.value ? Math.round(Number(props.rating(item)) || 0) : props.stat(item, 'points')
}

function gapOf(item) {
  return Math.max(0, leaderScore.value - scoreOf(item))
}
</script>

<template>
  <ol class="podium" :class="`podium--n${places.length}`">
    <li
      v-for="entry in places"
      :key="`${kind}-${entry.item.id}`"
      v-reveal="{ delay: REVEAL_DELAY[entry.place], y: 40, blur: 10, duration: 1000 }"
      class="podium__slot"
      :class="`is-p${entry.place}`"
      :style="{ '--rise-delay': `${REVEAL_DELAY[entry.place] + 180}ms` }"
    >
      <RouterLink
        v-tilt="6"
        class="podium__card"
        :class="{ 'is-ranked': rankKey(entry.item) !== 'rookie', 'is-season ui-dark': rankKey(entry.item) === SEASON_FINISH }"
        :data-rank="rankKey(entry.item)"
        :to="linkOf(entry.item)"
        :aria-label="t('hallPage.podium.open', { name: nameOf(entry.item) })"
      >
        <span class="ui-glare" aria-hidden="true"></span>
        <SeasonChampionBackdrop v-if="rankKey(entry.item) === SEASON_FINISH" class="podium__scene" size="card" cx="50%" cy="34%" />
        <template v-else-if="rankKey(entry.item) !== 'rookie'">
          <RankScene class="podium__scene" :rank="rankKey(entry.item)" size="card" :seed="entry.item.id" cx="50%" cy="34%" />
          <RankAura :rank="rankKey(entry.item)" size="lg" :seed="entry.item.id" glint />
        </template>
        <span class="podium__top">
          <span class="podium__place ui-num">P{{ entry.place }}</span>
          <span v-if="entry.place === 1" class="podium__leader"><Crown :size="14" />{{ t('hallPage.podium.leader') }}</span>
        </span>

        <span class="podium__avatar-wrap">
          <TeamAvatar v-if="isTeams" class="podium__avatar" :src="entry.item.avatar_url" :color="entry.item.avatar_color" :label="entry.item.name" />
          <UserAvatar v-else class="podium__avatar rank-avatar" :data-rank="rankKey(entry.item)" :src="entry.item.avatar_url" :color="entry.item.avatar_color" :label="nameOf(entry.item)" />
        </span>

        <strong class="podium__name rank-name" :data-rank="rankKey(entry.item)">{{ nameOf(entry.item) }}</strong>

        <span class="podium__meta">
          <template v-if="isTeams">
            <span class="ui-num">{{ entry.item.abbreviation || teamShortName(entry.item.name) }}</span>
            <span>{{ t('hallPage.podium.members', { count: entry.item.member_count ?? 0 }) }}</span>
          </template>
          <template v-else>
            <LicenseBadge class="podium__license" :user="entry.item" :game="game" />
            <span class="ui-num">#{{ formatPilotNumber(entry.item.pilot_number) }}</span>
            <span v-if="entry.item.team_id || entry.item.team_name" class="ui-num">{{ teamShortName(entry.item.team_name, entry.item.team_abbreviation) }}</span>
          </template>
        </span>

        <span class="podium__score">
          <CountUp class="podium__points" :value="scoreOf(entry.item)" :duration="1800" />
          <small>{{ byRating ? 'RER' : t('hallOfFame.pointsShort') }}</small>
        </span>
        <span class="podium__gap ui-num">
          <template v-if="entry.place === 1">{{ byRating ? (isTeams ? t('hallOfFame.averageRer') : t('hallPage.podium.bestRer')) : t('hallOfFame.points') }}</template>
          <template v-else>−{{ t(byRating ? 'hallPage.podium.gapRer' : 'hallPage.podium.gap', { points: gapOf(entry.item) }) }}</template>
        </span>

        <span class="podium__medals">
          <MedalPill tone="gold" size="md" :value="stat(entry.item, 'gold')" />
          <MedalPill tone="silver" size="md" :value="stat(entry.item, 'silver')" />
          <MedalPill tone="bronze" size="md" :value="stat(entry.item, 'bronze')" />
        </span>
      </RouterLink>

      <div class="podium__step" aria-hidden="true">
        <span class="podium__numeral">{{ entry.place }}</span>
      </div>
    </li>
  </ol>
</template>

<style scoped>
.podium {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.12fr) minmax(0, 1fr);
  align-items: end;
  gap: clamp(10px, 1.6vw, 22px);
  max-width: 1080px;
  width: 100%;
  margin: 0 auto;
  padding: 0;
  list-style: none;
}

.podium--n1 {
  grid-template-columns: minmax(0, 420px);
  justify-content: center;
}

.podium--n2 {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.12fr);
  max-width: 760px;
}

.podium__slot {
  --tone: var(--bm-silver);
  --step-h: 96px;
  display: grid;
  gap: 0;
  min-width: 0;
}

.podium__slot.is-p1 {
  --tone: var(--bm-gold);
  --step-h: 140px;
}

.podium__slot.is-p3 {
  --tone: var(--bm-bronze);
  --step-h: 64px;
}

/* ---------- Plate ---------- */
.podium__card {
  position: relative;
  z-index: 1;
  display: grid;
  justify-items: center;
  gap: 10px;
  margin-bottom: -18px;
  padding: 18px 18px 34px;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--tone) 34%, var(--c-line));
  border-radius: var(--r-xl);
  background:
    radial-gradient(120% 70% at 50% 0%, color-mix(in srgb, var(--tone) 20%, transparent), transparent 70%),
    var(--c-surface);
  box-shadow: var(--shadow-1);
  color: var(--c-text);
  text-align: center;
  text-decoration: none;
  -webkit-backdrop-filter: var(--glass-filter);
  backdrop-filter: var(--glass-filter);
  transition: border-color var(--dur-3) var(--ease-out), box-shadow var(--dur-3) var(--ease-out);
}

/* Pilots from bronze up: the plate takes the profile's rank finish (backdrop,
   living scene and animated rim) instead of the plain place colour. */
.podium__card.is-ranked {
  border-color: color-mix(in srgb, var(--rank-2) 50%, var(--c-line));
  background:
    radial-gradient(120% 70% at 50% 0%, color-mix(in srgb, var(--rank-2) 32%, transparent), transparent 70%),
    radial-gradient(90% 60% at 50% 100%, color-mix(in srgb, var(--rank-3) 50%, transparent), transparent 75%),
    var(--c-surface);
  box-shadow: var(--shadow-2), 0 24px 70px -22px var(--rank-glow);
}

.podium__scene {
  z-index: -1;
}

/* The season champion's plate: its backdrop paints the surface and the rim. */
.podium__card.is-season {
  border-color: transparent;
  background: #06070a;
  box-shadow: var(--shadow-2), 0 24px 70px -22px rgba(245, 200, 76, 0.6);
}

/* The rank's own sheen replaces the leader's gold sweep. */
.is-p1 .podium__card.is-ranked::after {
  display: none;
}

.podium__card:hover {
  border-color: color-mix(in srgb, var(--tone) 60%, transparent);
  box-shadow: var(--shadow-2), 0 0 0 1px color-mix(in srgb, var(--tone) 22%, transparent);
}

.is-p1 .podium__card {
  padding-top: 22px;
  box-shadow: var(--shadow-2), 0 24px 70px -20px color-mix(in srgb, var(--bm-gold) 55%, transparent);
}

/* A slow light sweep across the leader's plate. */
.is-p1 .podium__card::after {
  position: absolute;
  inset: 0;
  background: linear-gradient(110deg, transparent 35%, color-mix(in srgb, var(--bm-gold) 22%, transparent) 50%, transparent 65%);
  content: '';
  pointer-events: none;
  transform: translateX(-100%);
  animation: podium-sheen 6s var(--ease-out) 1.6s infinite;
}

.podium__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
}

.podium__place {
  padding: 4px 9px;
  border-radius: var(--r-xs);
  background: var(--tone);
  color: #10131a;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.podium__leader {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: color-mix(in srgb, var(--bm-gold) 85%, var(--c-text));
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

/* Avatar framed by a metal ring; the leader's ring turns slowly. */
.podium__avatar-wrap {
  position: relative;
  display: grid;
  place-items: center;
  padding: 4px;
  border-radius: 50%;
  background: conic-gradient(from var(--ring-angle, 0deg), var(--tone), color-mix(in srgb, var(--tone) 25%, transparent), var(--tone), color-mix(in srgb, var(--tone) 25%, transparent), var(--tone));
  box-shadow: 0 10px 30px -8px color-mix(in srgb, var(--tone) 70%, transparent);
}

.is-p1 .podium__avatar-wrap {
  animation: podium-ring 7s linear infinite;
}

.podium__avatar {
  width: 68px;
  height: 68px;
  border: 3px solid var(--c-surface-solid);
  box-shadow: none;
}

.is-p1 .podium__avatar {
  width: 86px;
  height: 86px;
}

.podium__name {
  max-width: 100%;
  overflow: hidden;
  font-family: var(--font-display);
  font-size: clamp(14px, 1.3vw, 17px);
  font-weight: 700;
  line-height: 1.2;
  text-overflow: ellipsis;
  text-transform: uppercase;
  white-space: nowrap;
}

.is-p1 .podium__name {
  font-size: clamp(15px, 1.5vw, 20px);
}

.podium__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 6px 10px;
  min-height: 22px;
  color: var(--c-text-3);
  font-size: 12.5px;
}

.podium__license {
  font-size: 10px;
}

.podium__score {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  margin-top: 2px;
}

.podium__points {
  color: var(--c-text);
  font-size: clamp(28px, 3vw, 40px);
  font-weight: 700;
  line-height: 1;
}

.is-p1 .podium__points {
  background: linear-gradient(180deg, #fff6d8, var(--bm-gold) 55%, color-mix(in srgb, var(--bm-gold) 70%, #6b4a00));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  font-size: clamp(34px, 3.8vw, 52px);
}

:root[data-theme='light'] .is-p1 .podium__points {
  background: linear-gradient(180deg, #c18f12, #7a5600);
  -webkit-background-clip: text;
  background-clip: text;
}

.podium__score small {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
}

.podium__gap {
  color: var(--c-text-3);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.podium__medals {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 6px;
  margin-top: 4px;
}

/* ---------- Step ---------- */
.podium__step {
  position: relative;
  display: grid;
  place-items: center;
  height: var(--step-h);
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--tone) 40%, transparent);
  border-bottom: 0;
  border-radius: var(--r-md) var(--r-md) 6px 6px;
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--tone) 46%, var(--c-surface-solid)), color-mix(in srgb, var(--tone) 6%, transparent)),
    var(--c-surface-solid);
  transform-origin: bottom center;
  animation: podium-rise 1100ms var(--ease-ios) var(--rise-delay, 0ms) both;
}

.podium__step::before {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(135deg, transparent 0 10px, color-mix(in srgb, #fff 5%, transparent) 10px 11px);
  content: '';
}

.podium__numeral {
  position: relative;
  padding-top: 14px;
  background: linear-gradient(180deg, #fff, color-mix(in srgb, var(--tone) 80%, #000));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  font-family: var(--font-display);
  font-size: clamp(34px, 4.6vw, 64px);
  font-weight: 800;
  line-height: 1;
  opacity: 0.9;
}

:root[data-theme='light'] .podium__numeral {
  background: linear-gradient(180deg, color-mix(in srgb, var(--tone) 55%, #000), color-mix(in srgb, var(--tone) 30%, #000));
  -webkit-background-clip: text;
  background-clip: text;
}

.is-p3 .podium__numeral {
  font-size: clamp(28px, 3.4vw, 44px);
}

@property --ring-angle {
  syntax: '<angle>';
  inherits: false;
  initial-value: 0deg;
}

@keyframes podium-ring {
  to {
    --ring-angle: 360deg;
  }
}

@keyframes podium-rise {
  from {
    opacity: 0;
    transform: scaleY(0.2);
  }
  to {
    opacity: 1;
    transform: scaleY(1);
  }
}

@keyframes podium-sheen {
  0% {
    transform: translateX(-100%);
  }
  30%,
  100% {
    transform: translateX(100%);
  }
}

/* ---------- Phones: the leader on top, 2nd and 3rd side by side ---------- */
@media (max-width: 640px) {
  .podium,
  .podium--n2 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .podium--n1 {
    grid-template-columns: minmax(0, 1fr);
  }

  .podium__slot.is-p1 {
    --step-h: 0px;
    grid-column: 1 / -1;
    order: -1;
  }

  .podium__slot {
    --step-h: 46px;
  }

  .podium__slot.is-p3 {
    --step-h: 30px;
  }

  .is-p1 .podium__card {
    margin-bottom: 0;
    padding-bottom: 20px;
  }

  .is-p1 .podium__step {
    display: none;
  }

  .podium__card {
    padding: 14px 10px 28px;
    gap: 8px;
  }

  .podium__avatar {
    width: 54px;
    height: 54px;
  }

  .is-p1 .podium__avatar {
    width: 76px;
    height: 76px;
  }

  .podium__medals :deep(.medal) {
    min-width: 40px;
    height: 26px;
    padding: 0 8px 0 6px;
    font-size: 12px;
  }

  .podium__numeral {
    padding-top: 6px;
    font-size: 24px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .podium__step,
  .is-p1 .podium__avatar-wrap,
  .is-p1 .podium__card::after {
    animation: none;
  }
}
</style>
