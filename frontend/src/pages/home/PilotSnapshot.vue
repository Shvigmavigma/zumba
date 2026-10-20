<script setup>
// Right-hand card next to the next race: the signed-in pilot's numbers and
// their best licence, or a clear invitation to create an account. The card is
// as tall as the race card beside it; the licence takes up the room left over.
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowRight, Clock3, UserPlus } from 'lucide-vue-next'
import ActivityRings from '../../ui/ActivityRings.vue'
import CountUp from '../../ui/fx/CountUp.vue'
import PilotLicenseCard from '../../components/PilotLicenseCard.vue'
import UserAvatar from '../../components/UserAvatar.vue'
import { ensureLicenseSettings } from '../../licenseSettings'
import LicensePreview from '../auth/LicensePreview.vue'
import { DEFAULT_LICENSE_TIERS, OVERALL_RATING_GAME, RATING_GAMES, formatPilotNumber, licenseProgress, pilotName, ratedGames, ratingForGame, ratingRaceCountForGame } from '../../pilotDisplay'
import { state } from '../../store'

const { t, tm } = useI18n()
const MAX_SR = 30

const user = computed(() => state.user)
// Profile routes need an active account (see router.js).
const isActive = computed(() => user.value?.status === 'active')
// The overall rating, as the pilot's rank counts it: their best RER across the simulators.
const rating = computed(() => Number(ratingForGame(user.value, OVERALL_RATING_GAME)) || 0)
const races = computed(() => ratingRaceCountForGame(user.value, OVERALL_RATING_GAME))
const license = computed(() => licenseProgress(rating.value, state.licenseTiers || DEFAULT_LICENSE_TIERS))
const sr = computed(() => Number(user.value?.sr) || 0)
// The simulator the pilot is rated highest in, among those they race in.
const ratingIn = (game) => Number(ratingForGame(user.value, game)) || 0
const bestGame = computed(() => ratedGames(user.value).reduce((best, game) => (ratingIn(game) > ratingIn(best) ? game : best)))
const rings = computed(() => [
  { value: license.value.progress, color: license.value.tier.color === '#64748b' ? '#3c74f6' : license.value.tier.color, label: t('fields.license') },
  { value: sr.value / MAX_SR, color: '#4fd8ea', label: 'SR' }
])
const joinSteps = computed(() => tm('home.join.steps'))
// A guest sees the licence they would get, still blank: no name, number 000.
const BLANK_LICENCE = { games: [...RATING_GAMES] }

onMounted(ensureLicenseSettings)
</script>

<template>
  <article v-if="user" v-spotlight class="snap ui-glass">
    <header class="snap__head">
      <p class="ui-eyebrow">{{ t('home.profile.eyebrow') }}</p>
      <RouterLink v-if="isActive" class="ui-btn ui-btn--ghost ui-btn--icon ui-btn--sm" to="/profile" :aria-label="t('home.profile.open')"><ArrowRight :size="17" /></RouterLink>
    </header>

    <div class="snap__who">
      <UserAvatar class="snap__avatar" :src="user.avatar_url" :color="user.avatar_color" :label="user.nickname || user.login" />
      <div class="snap__name">
        <strong>{{ user.nickname || user.login }}</strong>
        <span>{{ pilotName(user, user.login) }} · #{{ formatPilotNumber(user.pilot_number) }}</span>
        <span class="license-chip" :style="{ '--tier': license.tier.color }">{{ license.tier.name }}</span>
      </div>
    </div>

    <div class="snap__rings">
      <ActivityRings :rings="rings" :size="118" :stroke="11" />
      <dl class="snap__legend">
        <div>
          <dt><i :style="{ background: rings[0].color }"></i>{{ t('home.profile.rating') }}</dt>
          <dd><CountUp :value="rating" /></dd>
        </div>
        <div>
          <dt><i style="background: #4fd8ea"></i>SR</dt>
          <dd><CountUp :value="sr" :decimals="1" /></dd>
        </div>
        <div>
          <dt>{{ t('home.profile.races') }}</dt>
          <dd><CountUp :value="races" /></dd>
        </div>
      </dl>
    </div>

    <div class="snap__next">
      <span>{{ license.next ? t('home.profile.toNext', { name: license.next.name }) : t('home.profile.maxTier') }}</span>
      <span class="ui-num">{{ license.next ? `${Math.round(rating)} / ${license.next.min_rating}` : Math.round(rating) }}</span>
      <span class="ui-meter snap__meter"><span :style="{ '--value': `${Math.round(license.progress * 100)}%` }"></span></span>
    </div>

    <div class="snap__licence">
      <p class="ui-eyebrow">{{ t('home.profile.bestLicence') }}</p>
      <PilotLicenseCard :pilot="user" :game="bestGame" :rating="ratingIn(bestGame)" />
    </div>

    <RouterLink v-if="isActive" class="ui-btn ui-btn--outline ui-btn--block" to="/profile">{{ t('home.profile.open') }}<ArrowRight :size="16" /></RouterLink>
    <p v-else class="snap__pending"><Clock3 :size="16" />{{ t(user.status === 'unapproved' ? 'ui.account.pendingHint' : 'ui.account.restrictedHint') }}</p>
  </article>

  <article v-else v-spotlight class="snap snap--join ui-glass ui-carbon">
    <p class="ui-eyebrow ui-eyebrow--accent">{{ t('home.join.eyebrow') }}</p>
    <h2 class="snap__join-title ui-display">{{ t('home.join.title') }}</h2>
    <p class="snap__join-text">{{ t('home.join.text') }}</p>
    <ol class="snap__steps">
      <li v-for="(step, index) in joinSteps" :key="index" v-reveal="{ delay: 100 + index * 90, y: 8, blur: 0 }">
        <span class="ui-num">{{ index + 1 }}</span>{{ step }}
      </li>
    </ol>
    <div class="snap__licence">
      <LicensePreview :form="BLANK_LICENCE" />
    </div>
    <div class="snap__join-actions">
      <RouterLink v-magnet v-spark class="ui-btn ui-btn--primary ui-btn--block" to="/register"><UserPlus :size="17" />{{ t('home.join.register') }}</RouterLink>
      <RouterLink class="ui-btn ui-btn--ghost ui-btn--block" to="/login">{{ t('home.join.login') }}</RouterLink>
    </div>
  </article>
</template>

<style scoped>
.snap {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 22px;
  border-radius: var(--r-xl);
}

/* Takes the height the race card leaves free, with the licence in the middle of it. */
.snap__licence {
  display: grid;
  flex: 1 1 auto;
  align-content: center;
  gap: 10px;
}

.snap__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.snap__who {
  display: flex;
  align-items: center;
  gap: 14px;
}

.snap__avatar {
  width: 68px;
  height: 68px;
  flex: 0 0 auto;
}

.snap__name {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.snap__name strong {
  overflow: hidden;
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  text-overflow: ellipsis;
  text-transform: uppercase;
  white-space: nowrap;
}

.snap__name > span:not(.license-chip) {
  overflow: hidden;
  color: var(--c-text-3);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.license-chip {
  justify-self: start;
  padding: 3px 9px;
  border: 1px solid color-mix(in srgb, var(--tier) 55%, transparent);
  border-radius: var(--r-pill);
  background: color-mix(in srgb, var(--tier) 16%, transparent);
  color: color-mix(in srgb, var(--tier) 60%, var(--c-text));
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.snap__rings {
  display: flex;
  align-items: center;
  gap: 20px;
}

.snap__legend {
  display: grid;
  flex: 1 1 auto;
  gap: 10px;
  margin: 0;
}

.snap__legend div {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.snap__legend dt {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--c-text-3);
  font-size: 12.5px;
}

.snap__legend i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.snap__legend dd {
  margin: 0;
  color: var(--c-text);
  font-size: 20px;
  font-weight: 600;
}

.snap__next {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  color: var(--c-text-2);
  font-size: 12.5px;
}

.snap__next .ui-num {
  color: var(--c-text-3);
}

.snap__meter {
  grid-column: 1 / -1;
}

.snap__pending {
  display: flex;
  gap: 10px;
  margin: 0;
  padding: 12px 14px;
  border: 1px solid color-mix(in srgb, var(--bm-amber) 30%, transparent);
  border-radius: var(--r-md);
  background: color-mix(in srgb, var(--bm-amber) 9%, transparent);
  color: var(--c-text-2);
  font-size: 13px;
  line-height: 1.45;
}

.snap__pending svg {
  flex: none;
  margin-top: 1px;
  color: var(--bm-amber);
}

.snap--join {
  gap: 16px;
}

.snap__join-title {
  color: var(--c-text);
  font-size: clamp(22px, 2.2vw, 28px);
  line-height: 1.18;
}

.snap__join-text {
  margin: 0;
  color: var(--c-text-2);
  font-size: 14px;
  line-height: 1.55;
}

.snap__steps {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.snap__steps li {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--c-text);
  font-size: 14px;
}

.snap__steps .ui-num {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--c-blue-line);
  border-radius: 50%;
  background: var(--c-blue-soft);
  color: var(--c-accent-text);
  font-size: 12px;
}

.snap__join-actions {
  display: grid;
  gap: 6px;
}
</style>
