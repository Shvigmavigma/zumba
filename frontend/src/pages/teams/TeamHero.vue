<script setup>
// Team detail hero: the livery fills the plate, the abbreviation sits behind
// the name like a door number, key numbers run along the bottom.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Crown, LogIn, LogOut, Maximize2, Send } from 'lucide-vue-next'
import TeamAvatar from '../../components/TeamAvatar.vue'
import CountUp from '../../ui/fx/CountUp.vue'
import RacingLines from '../../ui/fx/RacingLines.vue'
import { formatRating, teamShortName } from '../../pilotDisplay'
import SeatMeter from './SeatMeter.vue'
import { averageOf, freeSeats, isTeamFull, teamStyle } from './teamUtils'

const props = defineProps({
  team: { type: Object, required: true },
  busy: { type: Boolean, default: false },
  signedIn: { type: Boolean, default: false }
})
const emit = defineEmits(['join', 'leave', 'open-avatar'])
const { t } = useI18n()

const abbreviation = computed(() => teamShortName(props.team.name, props.team.abbreviation))
const owner = computed(() => props.team.owner_nickname || props.team.owner_login || t('teams.noOwner'))
const averageSr = computed(() => averageOf(props.team.members, (member) => member.sr))
const full = computed(() => isTeamFull(props.team))
const seatsLeft = computed(() => freeSeats(props.team))
const showApplication = computed(() => props.team.my_application_status && !props.team.is_member)
const applicationChip = computed(() => ({
  pending: 'ui-chip--amber',
  approved: 'ui-chip--green',
  rejected: 'ui-chip--red'
}[props.team.my_application_status] || ''))
</script>

<template>
  <section class="hero" :style="teamStyle(team.avatar_color)" aria-labelledby="team-hero-title">
    <div class="hero__livery" aria-hidden="true">
      <span class="hero__glow"></span>
      <span class="hero__stripes"></span>
      <RacingLines class="hero__lines" :count="10" />
      <span class="hero__watermark ui-outline-text">{{ abbreviation }}</span>
    </div>

    <div class="hero__body">
      <button class="hero__avatar" type="button" :title="t('avatar.open')" :aria-label="t('avatar.open')" @click="emit('open-avatar')">
        <TeamAvatar :src="team.avatar_url" :color="team.avatar_color" :label="team.name" />
        <span class="hero__zoom" aria-hidden="true"><Maximize2 :size="14" /></span>
      </button>

      <div class="hero__text">
        <p class="hero__eyebrow">
          <span class="hero__code">{{ abbreviation }}</span>
          <span class="ui-eyebrow"><Crown :size="13" class="hero__crown" />{{ t('teams.ownerLine', { owner }) }}</span>
        </p>
        <h2 id="team-hero-title" v-split class="ui-display hero__name">{{ team.name }}</h2>
        <p class="hero__desc">{{ team.description || t('teams.noDescription') }}</p>
        <div class="hero__chips">
          <span v-if="team.is_owner" class="ui-chip ui-chip--blue"><Crown :size="12" />{{ t('teamsPage.card.owner') }}</span>
          <span v-else-if="team.is_member" class="ui-chip ui-chip--green"><span class="ui-dot ui-dot--green"></span>{{ t('teamsPage.card.mine') }}</span>
          <span v-if="showApplication" class="ui-chip" :class="applicationChip">{{ t(`teams.applicationStatuses.${team.my_application_status}`) }}</span>
          <span v-if="full" class="ui-chip">{{ t('teamsPage.card.full') }}</span>
          <span v-else class="ui-chip">{{ t('teamsPage.hero.seatsLeft', { count: seatsLeft }) }}</span>
        </div>
      </div>

      <div class="hero__actions">
        <button
          v-if="team.can_join"
          v-magnet
          v-spark
          class="ui-btn ui-btn--primary ui-btn--lg"
          type="button"
          :disabled="busy"
          @click="emit('join', team)"
        >
          <Send :size="17" />{{ t('teams.requestJoin') }}
        </button>
        <button v-if="team.is_member && !team.is_owner" class="ui-btn ui-btn--danger" type="button" :disabled="busy" @click="emit('leave')">
          <LogOut :size="16" />{{ t('teams.leave') }}
        </button>
        <RouterLink v-if="!signedIn" class="ui-btn ui-btn--outline" to="/login">
          <LogIn :size="16" />{{ t('teamsPage.hero.login') }}
        </RouterLink>
        <p v-if="!signedIn" class="hero__note">{{ t('teams.loginToJoin') }}</p>
      </div>
    </div>

    <dl class="hero__stats">
      <div v-reveal="{ delay: 80, y: 12, blur: 0 }" class="hero__stat">
        <dt>{{ t('teamsPage.card.rating') }}</dt>
        <dd class="hero__big"><CountUp :value="formatRating(team.average_rating)" /></dd>
      </div>
      <div v-reveal="{ delay: 160, y: 12, blur: 0 }" class="hero__stat">
        <dt>{{ t('teamsPage.hero.averageSr') }}</dt>
        <dd class="hero__big">
          <CountUp v-if="averageSr !== null" :value="averageSr" :decimals="1" />
          <span v-else class="ui-num">-</span>
        </dd>
      </div>
      <div v-reveal="{ delay: 240, y: 12, blur: 0 }" class="hero__stat hero__stat--seats">
        <dt>{{ t('teamsPage.card.roster') }}</dt>
        <dd class="hero__big ui-num">{{ team.member_count }}<small>/{{ team.member_limit }}</small></dd>
        <SeatMeter class="hero__meter" :count="team.member_count" :limit="team.member_limit" :label="t('teams.membersCount', { count: team.member_count, limit: team.member_limit })" />
      </div>
    </dl>
  </section>
</template>

<style scoped>
.hero {
  --team-vis: color-mix(in srgb, var(--team) 74%, var(--c-text) 26%);
  position: relative;
  display: grid;
  gap: clamp(20px, 3vw, 32px);
  padding: clamp(20px, 3vw, 36px);
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--team-vis) 30%, var(--c-line));
  border-radius: var(--r-xl);
  background: color-mix(in srgb, var(--team) 8%, var(--c-surface-solid));
  box-shadow: var(--shadow-2), 0 40px 90px -50px color-mix(in srgb, var(--team) 80%, transparent);
  isolation: isolate;
}

/* ---------- Livery layer ---------- */
.hero__livery {
  position: absolute;
  inset: 0;
  z-index: -1;
  overflow: hidden;
  /* The layer is its own stacking context; the outlined watermark blends with
     what is inside it, so it carries the banner's surface colour itself. */
  background: inherit;
}

.hero__glow {
  position: absolute;
  top: -40%;
  right: -10%;
  width: 70%;
  aspect-ratio: 1;
  border-radius: 50%;
  background: radial-gradient(circle, color-mix(in srgb, var(--team) 55%, transparent), transparent 66%);
  filter: blur(10px);
  animation: hero-breathe 9s var(--ease-out) infinite alternate;
}

.hero__stripes {
  position: absolute;
  inset: -10% -10% -10% 38%;
  background: linear-gradient(
    112deg,
    transparent 0 30%,
    color-mix(in srgb, var(--team) 85%, transparent) 30% 46%,
    transparent 46% 49%,
    color-mix(in srgb, var(--team) 60%, #fff 40%) 49% 52%,
    transparent 52%
  );
  opacity: 0.55;
  -webkit-mask-image: linear-gradient(180deg, #000 30%, transparent 95%);
  mask-image: linear-gradient(180deg, #000 30%, transparent 95%);
  animation: hero-drift 14s var(--ease-out) infinite alternate;
}

.hero__lines {
  opacity: 0.5;
}

.hero__watermark {
  position: absolute;
  right: clamp(-10px, 1vw, 24px);
  bottom: clamp(56px, 9vw, 96px);
  /* Drawn by .ui-outline-text. */
  --outline-color: color-mix(in srgb, var(--team-vis) 45%, transparent);
  font-family: var(--font-display);
  font-size: clamp(96px, 16vw, 230px);
  font-weight: 800;
  letter-spacing: 0.02em;
  line-height: 0.8;
  user-select: none;
}

/* In the light theme the team's visible colour is the dark one: the same
   switch as .ui-outline-text--dark-ink. */
:root[data-theme='light'] .hero__watermark {
  color: #fff;
  mix-blend-mode: multiply;
}

/* ---------- Body ---------- */
.hero__body {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: clamp(16px, 2.6vw, 32px);
}

.hero__avatar {
  position: relative;
  padding: 0;
  border: 0;
  border-radius: 28px;
  background: transparent;
  cursor: zoom-in;
  -webkit-tap-highlight-color: transparent;
}

.hero__avatar :deep(.team-avatar) {
  width: clamp(92px, 11vw, 132px);
  height: clamp(92px, 11vw, 132px);
  border: 2px solid color-mix(in srgb, var(--team-vis) 70%, transparent);
  border-radius: 28px;
  box-shadow:
    0 0 0 6px color-mix(in srgb, var(--c-surface-solid) 80%, transparent),
    0 24px 50px -16px color-mix(in srgb, var(--team) 85%, transparent);
  transition: transform var(--dur-3) var(--ease-spring);
}

.hero__avatar:hover :deep(.team-avatar) {
  transform: scale(1.04) rotate(-2deg);
}

.hero__zoom {
  position: absolute;
  right: -4px;
  bottom: -4px;
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 1px solid var(--c-line-strong);
  border-radius: 50%;
  background: var(--c-surface-2);
  color: var(--c-text);
  -webkit-backdrop-filter: var(--glass-filter);
  backdrop-filter: var(--glass-filter);
  opacity: 0;
  transform: scale(0.6);
  transition: opacity var(--dur-2), transform var(--dur-3) var(--ease-spring);
}

.hero__avatar:hover .hero__zoom,
.hero__avatar:focus-visible .hero__zoom {
  opacity: 1;
  transform: scale(1);
}

.hero__text {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.hero__eyebrow {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin: 0;
}

.hero__code {
  padding: 5px 10px;
  border-radius: 9px;
  background: var(--team);
  color: var(--team-ink);
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.14em;
  line-height: 1.1;
  box-shadow: 0 8px 20px -8px color-mix(in srgb, var(--team) 90%, transparent);
}

.hero__crown {
  color: var(--bm-gold);
}

.hero__name {
  color: var(--c-text);
  font-size: clamp(26px, 4vw, 52px);
  overflow-wrap: anywhere;
}

.hero__desc {
  max-width: 70ch;
  margin: 0;
  color: var(--c-text-2);
  font-size: 15px;
  line-height: 1.6;
  white-space: pre-line;
}

.hero__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.hero__actions {
  display: grid;
  justify-items: end;
  gap: 10px;
  align-self: start;
}

.hero__note {
  max-width: 24ch;
  margin: 0;
  color: var(--c-text-3);
  font-size: 12.5px;
  text-align: right;
}

/* ---------- Stats ---------- */
/* One capsule: the blur is the strip's own, and clip-path holds every cell inside its rounded corners.
   With a blur on each cell (each its own layer) Chrome drew the cells' square corners past the capsule. */
.hero__stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1px;
  margin: 0;
  overflow: hidden;
  border: 1px solid var(--c-line);
  border-radius: var(--r-lg);
  background: var(--c-line);
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
  clip-path: inset(0 round var(--r-lg));
  isolation: isolate;
}

.hero__stat {
  display: grid;
  align-content: start;
  gap: 6px;
  padding: 16px 18px;
  background: color-mix(in srgb, var(--c-surface-solid) 82%, transparent);
}

.hero__stat dt {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.hero__big {
  margin: 0;
  color: var(--c-text);
  font-size: clamp(24px, 2.6vw, 34px);
  font-weight: 600;
  line-height: 1;
}

.hero__big small {
  color: var(--c-text-3);
  font-size: 0.55em;
}

.hero__meter {
  margin-top: 6px;
}

@keyframes hero-breathe {
  from {
    opacity: 0.65;
    transform: scale(0.94);
  }
  to {
    opacity: 1;
    transform: scale(1.06) translateX(-4%);
  }
}

@keyframes hero-drift {
  from {
    transform: translateX(0);
  }
  to {
    transform: translateX(-6%);
  }
}

@media (max-width: 860px) {
  .hero__body {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .hero__actions {
    grid-column: 1 / -1;
    justify-items: start;
    grid-auto-flow: column;
    justify-content: start;
    align-items: center;
  }

  .hero__note {
    text-align: left;
  }
}

@media (max-width: 560px) {
  .hero__body {
    grid-template-columns: minmax(0, 1fr);
  }

  .hero__actions {
    grid-auto-flow: row;
  }

  .hero__stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .hero__stat--seats {
    grid-column: 1 / -1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero__glow,
  .hero__stripes {
    animation: none;
  }
}
</style>
