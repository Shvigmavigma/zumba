<script setup>
// Profile hero on a carbon plate, finished in the pilot's overall rank (best
// RER across simulators): the backdrop, rim and avatar ring grow from matte
// rookie to a champion's animated aura, and the rank strip shows the way to
// the next tier. One rating card per simulator, each in its own tier.
// The season champion (seasonChampion.js) gets a banner of their own instead
// of the rank backdrop: the title is not a rating, so the rank strip and the
// rating cards stay and keep showing the RER tier next to it.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { CalendarDays, CircleOff, Crown, MessageCircle, Users } from 'lucide-vue-next'
import CountUp from '../../ui/fx/CountUp.vue'
import RankAura from '../../ui/rank/RankAura.vue'
import RankEmblem from '../../ui/rank/RankEmblem.vue'
import RankScene from '../../ui/rank/RankScene.vue'
import SeasonChampionBackdrop from '../../ui/rank/SeasonChampionBackdrop.vue'
import PilotRoles from '../../components/PilotRoles.vue'
import RankStrip from './RankStrip.vue'
import UserAvatar from '../../components/UserAvatar.vue'
import { countryCode } from '../../countries'
import { countryLabel, roleLabel } from '../../i18nLabels'
import { DEFAULT_LICENSE_TIERS, formatPilotNumber, licenseProgress, pilotName, ratedGames, ratingForGame, ratingRaceCountForGame, teamHref, teamShortName } from '../../pilotDisplay'
import { isRerExcluded, overallRank, rankFor } from '../../ranks'
import { seasonTitleEvent, seasonTitleRole } from '../../seasonChampion'
import { formatShortDate } from '../../timezone'

const props = defineProps({
  pilot: { type: Object, required: true },
  tiers: { type: Array, default: () => DEFAULT_LICENSE_TIERS },
  /** Peak rating per game, from the rating history when it is loaded. */
  peaks: { type: Object, default: () => ({}) },
  own: { type: Boolean, default: false }
})
defineEmits(['open-avatar'])

const { t } = useI18n()
const name = computed(() => pilotName(props.pilot, props.pilot.login))
const code = computed(() => countryCode(props.pilot.country))
// A pilot outside the rating has no tiers to climb: no strip, no rating cards.
const excluded = computed(() => isRerExcluded(props.pilot))
const games = computed(() => (excluded.value ? [] : ratedGames(props.pilot)))
const cards = computed(() => games.value.map((game) => {
  const rating = Math.round(Number(ratingForGame(props.pilot, game)) || 0)
  const progress = licenseProgress(rating, props.tiers)
  return {
    game,
    rating,
    races: ratingRaceCountForGame(props.pilot, game),
    peak: props.peaks[game],
    rank: rankFor(rating, props.tiers).key,
    ...progress
  }
}))
const rank = computed(() => overallRank(props.pilot, props.tiers))
const seasonTitle = computed(() => seasonTitleRole(props.pilot))
</script>

<template>
  <section class="hero ui-carbon" :class="{ 'hero--season ui-dark': seasonTitle }" :data-rank="rank.key">
    <SeasonChampionBackdrop v-if="seasonTitle" cx="var(--scene-cx)" cy="var(--scene-cy)" />
    <template v-else>
      <div class="hero__rank" aria-hidden="true">
        <span class="hero__rank-glow"></span>
        <RankScene :rank="rank.key" :seed="pilot.id || 1" cx="var(--scene-cx)" cy="var(--scene-cy)" />
        <RankEmblem v-if="rank.level >= 1" class="hero__rank-crest" :rank="rank.key" :size="300" />
      </div>
      <RankAura :rank="rank.key" size="lg" :seed="pilot.id || 1" glint />
    </template>
    <div class="hero__identity">
      <button class="hero__avatar" type="button" :aria-label="t('profilePage.actions.openAvatar')" @click="$emit('open-avatar')">
        <UserAvatar class="hero__avatar-img" :src="pilot.avatar_url" :color="pilot.avatar_color" :label="pilot.nickname || pilot.login" />
        <span class="hero__number ui-num">#{{ formatPilotNumber(pilot.pilot_number) }}</span>
      </button>
      <div class="hero__text">
        <p class="ui-eyebrow">
          {{ own ? t('profilePage.ownEyebrow') : t('profilePage.eyebrow') }}
          <template v-if="pilot.role && pilot.role !== 'pilot'"> · {{ roleLabel(t, pilot.role) }}</template>
          <span v-if="pilot.country" class="hero__country">
            <span v-if="code" class="hero__code">{{ code }}</span>{{ countryLabel(t, pilot.country) }}
          </span>
        </p>
        <p v-if="seasonTitle" class="hero__title">
          <span class="hero__title-pill"><Crown :size="14" />{{ t('profilePage.seasonTitle.pill') }}</span>
          <b class="hero__title-event">{{ seasonTitleEvent(seasonTitle) }}</b>
          <span class="hero__title-note">{{ t('profilePage.seasonTitle.note') }}</span>
        </p>
        <h1 v-split class="hero__name ui-display">{{ name }}</h1>
        <p class="hero__nick">
          <span>{{ pilot.nickname || pilot.login }}</span>
          <PilotRoles :roles="pilot.pilot_roles" :limit="4" />
        </p>
        <ul class="hero__links">
          <li>
            <RouterLink v-if="pilot.team_id" class="hero__chip" :to="teamHref(pilot.team_id)" :title="pilot.team_name">
              <Users :size="14" /><b>{{ teamShortName(pilot.team_name, pilot.team_abbreviation) }}</b>{{ pilot.team_name }}
            </RouterLink>
            <span v-else class="hero__chip is-muted"><Users :size="14" />{{ t('profilePage.about.noTeam') }}</span>
          </li>
          <li v-if="pilot.discord"><span class="hero__chip"><MessageCircle :size="14" />{{ pilot.discord }}</span></li>
          <li><span class="hero__since"><CalendarDays :size="14" />{{ t('profilePage.since', { date: formatShortDate(pilot.created_at) }) }}</span></li>
        </ul>
        <p v-if="excluded" class="hero__excluded"><CircleOff :size="15" /><b>{{ t('common.rerExcluded') }}</b>{{ t('profilePage.rerExcludedNote') }}</p>
        <RankStrip v-else :rank="rank" :tiers="tiers" />
        <div v-if="$slots.actions" class="hero__actions"><slot name="actions" /></div>
      </div>
    </div>

    <div v-if="cards.length" class="hero__cards" :class="{ 'is-many': cards.length > 2 }">
      <article v-for="(card, index) in cards" :key="card.game" v-reveal="{ delay: 120 + index * 90, y: 14 }" v-spotlight class="rating" :data-rank="card.rank" :style="{ '--tier': card.tier.color }">
        <RankAura :rank="card.rank" :seed="index * 3 + 1" />
        <header class="rating__head">
          <span class="ui-chip ui-chip--solid">{{ card.game }}</span>
          <span class="rating__tier">{{ card.tier.name }}</span>
        </header>
        <p class="rating__value"><CountUp :value="card.rating" /><small>RER</small></p>
        <span class="ui-meter rating__meter"><span :style="{ '--value': `${Math.round(card.progress * 100)}%` }"></span></span>
        <p class="rating__meta">
          <span>{{ card.next ? t('profilePage.ratingCard.toNext', { name: card.next.name, count: card.toNext }) : t('profilePage.ratingCard.maxTier') }}</span>
          <span v-if="card.peak"> · {{ t('profilePage.ratingCard.peak', { value: card.peak }) }}</span>
          <span> · {{ t('profilePage.ratingCard.races', { count: card.races }) }}</span>
        </p>
      </article>
    </div>

  </section>
</template>

<style scoped>
.hero__excluded {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 8px;
  margin: 0;
  color: var(--c-text-2);
  font-size: 13.5px;
}

.hero__excluded b {
  color: var(--c-text);
}

.hero {
  /* The rank scene radiates from the avatar: padding + ring + half the avatar. */
  --scene-cx: calc(clamp(20px, 3vw, 36px) + 5px + clamp(92px, 10vw, 128px) / 2);
  --scene-cy: 50%;
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, auto);
  align-items: center;
  gap: 24px 32px;
  padding: clamp(20px, 3vw, 36px);
  overflow: hidden;
  border: 1px solid var(--c-line);
  border-radius: var(--r-xl);
  box-shadow: var(--shadow-1);
}

/* ---------- Rank backdrop ---------- */
.hero__rank {
  position: absolute;
  inset: 0;
  overflow: hidden;
  border-radius: inherit;
  pointer-events: none;
}

.hero__rank > * {
  position: absolute;
}

.hero__rank-glow {
  inset: 0;
  background:
    radial-gradient(40% 70% at 8% 50%, color-mix(in srgb, var(--rank-2) 24%, transparent), transparent 70%),
    radial-gradient(50% 80% at 100% 0%, color-mix(in srgb, var(--bm-blue) 18%, transparent), transparent 70%);
}

.hero__rank-crest {
  top: 50%;
  right: -60px;
  opacity: 0.1;
  transform: translateY(-50%) rotate(-12deg);
}

/* ---------- Season champion ---------- */
/* Dark in both themes (.ui-dark); the backdrop draws its own gold rim. */
.hero--season {
  border-color: transparent;
  background: #06070a;
  box-shadow: var(--shadow-2), 0 30px 90px -44px rgba(245, 200, 76, 0.6);
}

.hero--season .hero__avatar {
  background: conic-gradient(from var(--rank-angle), #fff3c4, #f5c84c, #8a6614, #f5c84c, #fff3c4);
  box-shadow: 0 0 44px rgba(245, 200, 76, 0.45);
  animation: hero-ring 9s linear infinite;
}

.hero__title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 12px;
  margin: 0;
}

.hero__title-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 28px;
  padding: 0 12px;
  border-radius: var(--r-pill);
  background: linear-gradient(120deg, #fff3c4, #f5c84c 45%, #c9971c);
  color: #1a1304;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  box-shadow: 0 8px 24px -10px rgba(245, 200, 76, 0.9);
}

.hero__title-event {
  color: #f5c84c;
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

/* Says what the title is: won over a season, not a rating. */
.hero__title-note {
  flex-basis: 100%;
  color: var(--c-text-2);
  font-size: 12.5px;
  line-height: 1.4;
}

.hero__identity {
  position: relative;
  z-index: 3;
  display: flex;
  align-items: center;
  gap: clamp(16px, 2.4vw, 28px);
  min-width: 0;
}

.hero__avatar {
  position: relative;
  flex: 0 0 auto;
  padding: 5px;
  border: 0;
  border-radius: 50%;
  background: conic-gradient(from var(--rank-angle), var(--rank-1), var(--rank-2), var(--rank-3), var(--rank-2), var(--rank-1));
  cursor: zoom-in;
  box-shadow: 0 0 40px var(--rank-glow);
  transition: transform var(--dur-3) var(--ease-ios);
}

/* From gold upwards the ring turns, faster at the top. */
.hero[data-rank='gold'] .hero__avatar,
.hero[data-rank='platinum'] .hero__avatar {
  animation: hero-ring 9s linear infinite;
}

.hero[data-rank='diamond'] .hero__avatar,
.hero[data-rank='champ'] .hero__avatar {
  animation: hero-ring 5s linear infinite;
}

@keyframes hero-ring {
  to {
    --rank-angle: 360deg;
  }
}

.hero__avatar:hover {
  transform: scale(1.03) rotate(-2deg);
}

.hero__avatar-img {
  width: clamp(92px, 10vw, 128px);
  height: clamp(92px, 10vw, 128px);
  border: 3px solid var(--c-bg);
  box-shadow: none;
}

.hero__number {
  position: absolute;
  right: -6px;
  bottom: 2px;
  padding: 4px 8px;
  border-radius: 9px;
  background: #fff;
  color: #05070d;
  font-size: 13px;
  font-weight: 700;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.35);
}

.hero__text {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.hero__country {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: 6px;
}

.hero__code {
  padding: 1px 5px;
  border: 1px solid var(--c-line-strong);
  border-radius: 4px;
  color: var(--c-text);
  font-size: 10px;
}

.hero__name {
  color: var(--c-text);
  font-size: clamp(28px, 4.2vw, 54px);
  overflow-wrap: anywhere;
}

.hero__nick {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: 0;
  color: var(--c-text-2);
  font-size: 15px;
}

.hero__links {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  margin: 4px 0 0;
  padding: 0;
  list-style: none;
}

.hero__chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 32px;
  max-width: 320px;
  padding: 0 12px;
  overflow: hidden;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-pill);
  background: var(--c-sunken);
  color: var(--c-text);
  font-size: 13px;
  text-decoration: none;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: border-color var(--dur-2);
}

a.hero__chip:hover {
  border-color: var(--c-blue-line);
}

.hero__chip b {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.06em;
}

.hero__chip.is-muted {
  color: var(--c-text-3);
}

.hero__since {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--c-text-3);
  font-size: 13px;
}

.hero__cards {
  position: relative;
  z-index: 3;
  display: grid;
  grid-template-columns: repeat(2, minmax(200px, 240px));
  gap: 10px;
}

.hero__cards.is-many {
  grid-template-columns: repeat(2, minmax(190px, 220px));
}

.rating {
  position: relative;
  overflow: hidden;
  display: grid;
  gap: 10px;
  padding: 14px 16px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-lg);
  /* Frosted rather than solid, so the rank scene shimmers through. */
  background: color-mix(in srgb, var(--c-surface-solid) 52%, transparent);
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
}

.rating__head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rating__tier {
  color: color-mix(in srgb, var(--tier) 70%, var(--c-text));
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.rating__value {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin: 0;
  color: var(--c-text);
  font-size: 30px;
  font-weight: 600;
  line-height: 1;
}

.rating__value small {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.1em;
}

.rating__meter > span {
  background: linear-gradient(90deg, color-mix(in srgb, var(--tier) 70%, var(--bm-blue)), var(--bm-cyan));
}

.rating__meta {
  margin: 0;
  color: var(--c-text-3);
  font-size: 12px;
}

.hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
}

@media (prefers-reduced-motion: reduce) {
  .hero__avatar {
    animation: none !important;
  }
}

@media (max-width: 1100px) {
  .hero {
    --scene-cy: clamp(140px, 22vw, 190px);
    grid-template-columns: minmax(0, 1fr);
  }

  .hero__cards,
  .hero__cards.is-many {
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  }
}

@media (max-width: 600px) {
  .hero {
    --scene-cy: calc(clamp(20px, 3vw, 36px) + 5px + clamp(92px, 10vw, 128px) / 2);
  }

  .hero__identity {
    flex-direction: column;
    align-items: flex-start;
  }

}
</style>
