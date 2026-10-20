<script setup>
// Cinematic race hero: track artwork, display name, schedule tiles, a live
// countdown with the start gantry lighting up as the start approaches (all
// five lamps while the race runs), the grid fill meter and one clear
// registration call to action for every state of the race. Once the race is
// decided, the winner's surname stands behind the header in huge dotted type,
// nearly transparent. Opening a finished race plays the winner's broadcast
// graphic first (WinnerIntro.vue): WINNER, then the first name; as it clears,
// the surname drives in at the bottom and the header rises in with it.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  ArrowDown,
  ArrowLeft,
  CalendarClock,
  CheckCircle2,
  ExternalLink,
  Flag,
  Lock,
  LogIn,
  MapPin,
  Maximize2,
  Thermometer,
  Timer,
  Trophy,
  Users
} from 'lucide-vue-next'
import Countdown from '../../ui/fx/Countdown.vue'
import RacingLines from '../../ui/fx/RacingLines.vue'
import StartLights from '../../ui/fx/StartLights.vue'
import WarningPulse from '../../ui/fx/WarningPulse.vue'
import { prefersReducedMotion } from '../../ui/motion/env'
import { gameLabel, statusLabel } from '../../i18nLabels'
import { dominantWeatherKey, fillPercent, raceStatusTone, registeredCount, weatherLabelKey } from '../../raceDisplay'
import { formatInTimeZone, timeZoneShortName } from '../../timezone'
import { WEATHER_ICONS } from './raceFormat'
import { trackImageStyle } from './trackImage'
import { safeHttpUrl } from '../../safeUrl'
import { useRaceMods } from './useRaceMods'
import WinnerIntro from './WinnerIntro.vue'
import { INTRO_TIMING } from './winnerIntro'

const props = defineProps({
  race: { type: Object, required: true },
  trackImage: { type: String, default: '' },
  /** The frame staff chose for the artwork: { zoom, x, y } (trackImage.js). */
  trackFrame: { type: Object, default: null },
  /** open | full | registered | owner-only | login | external | soon | closed | live | finished */
  cta: { type: String, default: 'closed' },
  summary: { type: Object, default: () => ({ winner: null, fastest: null, finishers: 0 }) },
  hasResults: { type: Boolean, default: false }
})
// Staff-entered server links: only web links ever reach the href.
const serverHref = computed(() => safeHttpUrl(props.race.server_link))
const emit = defineEmits(['register', 'open-track', 'show-results'])
const { t } = useI18n()
const { mods, seen: modsSeen, showMods } = useRaceMods(() => props.race)

const now = ref(Date.now())
let clock = 0

const status = computed(() => props.race.status)
const isLive = computed(() => status.value === 'ongoing')
const isFinished = computed(() => status.value === 'finished')
const isUpcoming = computed(() => !isLive.value && !isFinished.value)
const isLmu = computed(() => props.race.game === 'LMU')
const tone = computed(() => raceStatusTone(status.value))
const tz = computed(() => timeZoneShortName(props.race.datetime_start))
const hoursLeft = computed(() => (new Date(props.race.datetime_start).getTime() - now.value) / 3600000)
/** One lamp per remaining day inside the final five; all five in the last six hours. */
const litLamps = computed(() => {
  if (isLive.value || hoursLeft.value <= 6) return 5
  return Math.max(0, Math.min(4, 5 - Math.ceil(hoursLeft.value / 24)))
})
const schedule = computed(() => [
  { key: 'opens', label: t('racePage.hero.opens'), value: props.race.registration_start },
  { key: 'closes', label: t('racePage.hero.closes'), value: props.race.datetime_end },
  { key: 'start', label: t('racePage.hero.start'), value: props.race.datetime_start, highlight: true }
].map((item) => ({ ...item, passed: new Date(item.value).getTime() < now.value })))

const count = computed(() => registeredCount(props.race))
const seatsLeft = computed(() => Math.max(0, Number(props.race.max_pilots || 0) - count.value))
const weatherKey = computed(() => dominantWeatherKey(props.race))
const weatherIcon = computed(() => WEATHER_ICONS[weatherKey.value] || WEATHER_ICONS.clear)
const weatherChance = computed(() => Math.round(Number(props.race.weather_chances?.[weatherKey.value] || 0)))
const hasTemperature = computed(() => Number.isFinite(Number(props.race.track_temperature)) && props.race.track_temperature !== null)
const joinLabel = computed(() => (props.race.championship_id ? t('raceDetails.championshipStageRegister') : t('racePage.hero.join')))

// Decided once, as the header opens: the graphic plays for a finished race with a winner.
const hasIntro = isFinished.value && Boolean(props.summary.winner?.firstName) && !prefersReducedMotion()
const introPlaying = ref(hasIntro)
const introSkipped = ref(false)
const introStyle = hasIntro ? { '--intro-reveal': `${INTRO_TIMING.revealAt}ms` } : null

function skipIntro() {
  introSkipped.value = true
  introPlaying.value = false
}

const artBox = ref(null)
const frameStyle = computed(() => {
  const { objectPosition, ...box } = trackImageStyle(props.trackFrame)
  return { art: objectPosition ? { objectPosition } : {}, box }
})

/** Size of the artwork area, so the framing tool can match its proportions. */
function artSize() {
  const rect = artBox.value?.getBoundingClientRect()
  return rect ? { width: rect.width, height: rect.height } : null
}
defineExpose({ artSize })

function formatMoment(value) {
  return formatInTimeZone(value, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

function formatDay(value) {
  return formatInTimeZone(value, { weekday: 'long', day: 'numeric', month: 'long' })
}

onMounted(() => {
  clock = window.setInterval(() => { now.value = Date.now() }, 30000)
})
onBeforeUnmount(() => window.clearInterval(clock))
</script>

<template>
  <section
    class="hero"
    :class="[`is-${status}`, { 'has-art': trackImage, 'has-intro': hasIntro, 'is-intro-skipped': introSkipped }]"
    :style="introStyle"
    :aria-label="race.name"
  >
    <div class="hero__media" aria-hidden="true">
      <!-- The frame is zoomed, the image inside keeps its slow drift. -->
      <div v-if="trackImage" ref="artBox" class="hero__frame" :style="frameStyle.box">
        <img v-track-art class="hero__art" :src="trackImage" :style="frameStyle.art" alt="" />
      </div>
      <div v-else class="hero__art hero__art--fallback"></div>
    </div>
    <RacingLines class="hero__lines" :count="12" flip />
    <div class="hero__shade" aria-hidden="true"></div>
    <div class="hero__sweep" aria-hidden="true"></div>
    <div v-if="isFinished && summary.winner?.surname" class="hero__surname" aria-hidden="true">{{ summary.winner.surname }}</div>
    <WinnerIntro v-if="introPlaying" :name="summary.winner.firstName" @done="introPlaying = false" @skip="skipIntro" />

    <div class="hero__body">
      <RouterLink class="hero__back" to="/calendar"><ArrowLeft :size="15" />{{ t('racePage.hero.back') }}</RouterLink>

      <div v-reveal="{ y: 10, blur: 0, duration: 700 }" class="hero__chips">
        <span class="ui-chip ui-chip--solid">{{ gameLabel(t, race.game) }}</span>
        <span class="ui-chip" :class="tone ? `ui-chip--${tone}` : ''">
          <span class="ui-dot" :class="[tone ? `ui-dot--${tone}` : '', { 'ui-dot--live': isLive || status === 'registration_open' }]"></span>
          {{ statusLabel(t, status) }}
        </span>
        <span v-if="race.car_class" class="ui-chip ui-chip--blue">{{ race.car_class }}</span>
        <span v-if="race.championship_round" class="ui-chip"><Trophy :size="12" />{{ t('racePage.hero.round', { round: race.championship_round }) }}</span>
        <span v-if="race.is_official" class="ui-chip ui-chip--amber"><Flag :size="12" />{{ t('racePage.hero.official') }}</span>
        <span v-if="race.is_team_event" class="ui-chip"><Users :size="12" />{{ t('raceFilters.teamBadge') }}</span>
        <button v-if="mods.length" class="ui-chip ui-chip--red hero__mods" type="button" @click="showMods">
          <WarningPulse :size="13" :calm="modsSeen" />{{ t('racePage.hero.mods') }}
        </button>
      </div>

      <h1 v-split class="hero__title ui-display">{{ race.name }}</h1>

      <ul v-reveal="{ delay: 120, y: 10 }" class="hero__meta">
        <li>
          <MapPin :size="15" />
          <RouterLink class="hero__track" :to="{ path: '/pilots', query: { tab: 'tracks', track: race.track } }">{{ race.track }}</RouterLink>
        </li>
        <li><CalendarClock :size="15" />{{ formatDay(race.datetime_start) }} · {{ formatInTimeZone(race.datetime_start, { hour: '2-digit', minute: '2-digit' }) }} <small>{{ tz }}</small></li>
        <li><Timer :size="15" />{{ race.has_qualification ? t('raceDetails.withQualification') : t('raceDetails.withoutQualification') }}</li>
      </ul>

      <ol class="hero__schedule">
        <li
          v-for="(item, index) in schedule"
          :key="item.key"
          v-reveal="{ delay: 160 + index * 80, y: 10, blur: 4 }"
          class="hero__slot"
          :class="{ 'is-passed': item.passed, 'is-key': item.highlight }"
        >
          <span class="hero__slot-label">{{ item.label }}</span>
          <strong class="ui-num">{{ formatMoment(item.value) }}</strong>
        </li>
      </ol>

      <div v-if="isUpcoming" v-reveal="{ delay: 260, y: 12 }" class="hero__clock">
        <div class="hero__clock-head">
          <StartLights size="sm" :lit="litLamps" :label="t('racePage.hero.toStart')" />
          <span class="ui-eyebrow">{{ t('racePage.hero.toStart') }}</span>
        </div>
        <Countdown :target="race.datetime_start" />
      </div>

      <div v-else-if="isLive" v-reveal="{ delay: 200, y: 12 }" class="hero__live">
        <StartLights size="md" :lit="5" :label="t('racePage.hero.live')" />
        <div>
          <strong>{{ t('racePage.hero.live') }}</strong>
          <span>{{ t('racePage.hero.liveText') }}</span>
        </div>
      </div>

      <div v-else-if="summary.winner" v-reveal="{ delay: 200, y: 12 }" class="hero__finish">
        <component
          :is="summary.winner.pilotId ? 'RouterLink' : 'div'"
          class="hero__finish-tile is-winner"
          :to="summary.winner.pilotId ? `/pilots/${summary.winner.pilotId}` : undefined"
        >
          <span class="hero__finish-label"><Trophy :size="14" />{{ t('racePage.hero.winner') }}</span>
          <strong>{{ summary.winner.name }}</strong>
          <span class="ui-num">{{ summary.winner.time }}</span>
        </component>
        <div v-if="summary.fastest" class="hero__finish-tile is-fastest">
          <span class="hero__finish-label"><Timer :size="14" />{{ t('racePage.hero.fastestLap') }}</span>
          <strong class="ui-num">{{ summary.fastest.time }}</strong>
          <span>{{ summary.fastest.name }}</span>
        </div>
        <div class="hero__finish-tile is-count">
          <span class="hero__finish-label"><Flag :size="14" />{{ t('racePage.hero.finishers') }}</span>
          <strong class="hero__count">{{ summary.finishers }}</strong>
        </div>
      </div>

      <div v-if="!isLmu && isUpcoming" v-reveal="{ delay: 300, y: 10 }" class="hero__fill">
        <span class="hero__fill-label"><Users :size="15" />{{ race.is_team_event ? t('raceDetails.teams') : t('racePage.hero.grid') }}</span>
        <span class="ui-meter"><span :style="{ '--value': `${fillPercent(race)}%` }"></span></span>
        <strong class="ui-num">{{ count }} / {{ race.max_pilots }}</strong>
      </div>

      <footer v-reveal="{ delay: 340, y: 10 }" class="hero__actions">
        <template v-if="cta === 'open'">
          <button v-magnet v-spark class="ui-btn ui-btn--primary ui-btn--lg" type="button" @click="emit('register')">
            {{ joinLabel }}<ArrowDown :size="17" />
          </button>
          <span v-if="!isLmu" class="hero__note">{{ t('racePage.hero.seatsLeft', { count: seatsLeft }) }}</span>
        </template>
        <template v-else-if="cta === 'registered' || cta === 'registered-closed'">
          <span class="ui-chip ui-chip--green hero__state"><CheckCircle2 :size="14" />{{ race.is_team_event ? t('racePage.hero.teamRegistered') : t('racePage.hero.registered') }}</span>
          <button v-if="cta === 'registered'" class="ui-btn ui-btn--outline ui-btn--lg" type="button" @click="emit('register')">{{ t('racePage.hero.myEntry') }}<ArrowDown :size="17" /></button>
        </template>
        <template v-else-if="cta === 'full'">
          <span class="ui-chip ui-chip--red hero__state"><Lock :size="14" />{{ t('racePage.hero.full') }}</span>
          <button class="ui-btn ui-btn--outline ui-btn--lg" type="button" @click="emit('register')">{{ t('racePage.hero.toForm') }}<ArrowDown :size="17" /></button>
        </template>
        <template v-else-if="cta === 'owner-only'">
          <span class="ui-chip hero__state"><Users :size="14" />{{ t('racePage.hero.ownerOnly') }}</span>
          <button class="ui-btn ui-btn--outline ui-btn--lg" type="button" @click="emit('register')">{{ t('racePage.hero.toForm') }}<ArrowDown :size="17" /></button>
        </template>
        <RouterLink v-else-if="cta === 'login'" v-magnet class="ui-btn ui-btn--primary ui-btn--lg" to="/login">
          <LogIn :size="17" />{{ t('racePage.hero.login') }}
        </RouterLink>
        <a v-else-if="cta === 'external' && serverHref" v-magnet class="ui-btn ui-btn--primary ui-btn--lg" :href="serverHref" target="_blank" rel="noopener noreferrer">
          {{ t('racePage.hero.server') }}<ExternalLink :size="17" />
        </a>
        <span v-else-if="cta === 'soon'" class="ui-chip ui-chip--blue hero__state"><CalendarClock :size="14" />{{ t('racePage.hero.opensAt', { date: formatMoment(race.registration_start) }) }}</span>
        <span v-else-if="cta === 'live'" class="ui-chip ui-chip--red hero__state"><span class="ui-dot ui-dot--red ui-dot--live"></span>{{ t('racePage.hero.live') }}</span>
        <template v-else-if="cta === 'finished'">
          <button v-if="hasResults" v-magnet class="ui-btn ui-btn--primary ui-btn--lg" type="button" @click="emit('show-results')">
            {{ t('racePage.hero.showResults') }}<ArrowDown :size="17" />
          </button>
          <span v-else class="ui-chip hero__state"><Flag :size="14" />{{ t('racePage.hero.finished') }}</span>
        </template>
        <span v-else class="ui-chip hero__state"><Lock :size="14" />{{ t('racePage.hero.closed') }}</span>
      </footer>
    </div>

    <div class="hero__weather" :title="t(weatherLabelKey(weatherKey))">
      <component :is="weatherIcon" :size="18" />
      <span>{{ t(weatherLabelKey(weatherKey)) }} <b class="ui-num">{{ weatherChance }}%</b></span>
      <span v-if="hasTemperature" class="hero__temp ui-num"><Thermometer :size="14" />{{ Number(race.track_temperature).toFixed(0) }}°</span>
    </div>

    <button v-if="trackImage" class="hero__zoom" type="button" @click="emit('open-track')">
      <Maximize2 :size="15" />{{ t('racePage.hero.trackMap') }}
    </button>
  </section>
</template>

<style scoped>
.hero {
  position: relative;
  display: grid;
  min-height: 560px;
  overflow: hidden;
  border: 1px solid var(--c-line);
  border-radius: var(--r-xl);
  background: var(--c-surface);
  box-shadow: var(--shadow-1);
  -webkit-backdrop-filter: var(--glass-filter);
  backdrop-filter: var(--glass-filter);
  isolation: isolate;
}

.hero.is-ongoing {
  border-color: color-mix(in srgb, var(--bm-red) 40%, var(--c-line));
}

.hero__media {
  position: absolute;
  inset: 0 0 0 32%;
  z-index: -3;
  overflow: hidden;
  -webkit-mask-image: linear-gradient(90deg, transparent 0%, #000 42%);
  mask-image: linear-gradient(90deg, transparent 0%, #000 42%);
}

.hero__frame {
  width: 100%;
  height: 100%;
}

.hero__art {
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.78;
  animation: hero-drift 26s var(--ease-out) infinite alternate;
}

.hero__art--fallback {
  background:
    radial-gradient(50% 60% at 70% 40%, color-mix(in srgb, var(--bm-blue) 45%, transparent), transparent 70%),
    repeating-linear-gradient(115deg, transparent 0 22px, color-mix(in srgb, var(--c-text) 4%, transparent) 22px 23px);
}

:root[data-theme='light'] .hero__art {
  opacity: 0.34;
}

.hero__lines {
  z-index: -2;
  opacity: 0.7;
}

.hero__shade {
  position: absolute;
  inset: 0;
  z-index: -1;
  background:
    linear-gradient(90deg, color-mix(in srgb, var(--c-bg) 72%, transparent) 0%, color-mix(in srgb, var(--c-bg) 34%, transparent) 58%, transparent 100%),
    linear-gradient(0deg, color-mix(in srgb, var(--c-bg) 40%, transparent), transparent 40%);
  pointer-events: none;
}

/* A slow light sweep across the plate, like floodlights over a wet track. */
.hero__sweep {
  position: absolute;
  inset: -20% -40%;
  z-index: -1;
  background: linear-gradient(105deg, transparent 42%, color-mix(in srgb, var(--bm-blue-bright) 12%, transparent) 50%, transparent 58%);
  pointer-events: none;
  animation: hero-sweep 9s var(--ease-ios) infinite;
}

/* The winner's surname: the display type filled with a grid of dots, blue into violet,
   fading in from the left and cut by the header's edges. */
.hero__surname {
  position: absolute;
  right: -0.04em;
  /* The baseline a few pixels above the header's lower edge. */
  bottom: -0.05em;
  z-index: -1;
  background: linear-gradient(90deg, var(--bm-blue-bright), #8b5cf6);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  font-family: var(--font-display);
  font-size: clamp(110px, 15vw, 240px);
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1;
  text-transform: uppercase;
  white-space: nowrap;
  -webkit-mask:
    radial-gradient(circle, #000 1.7px, transparent 2.3px) 0 0 / 7px 7px,
    linear-gradient(90deg, rgba(0, 0, 0, 0.15), #000 30%);
  -webkit-mask-composite: source-in;
  mask:
    radial-gradient(circle, #000 1.7px, transparent 2.3px) 0 0 / 7px 7px,
    linear-gradient(90deg, rgba(0, 0, 0, 0.15), #000 30%);
  mask-composite: intersect;
  opacity: 0.36;
  pointer-events: none;
  user-select: none;
  animation: hero-surname-in 1600ms var(--ease-ios) 200ms backwards;
}

:root[data-theme='light'] .hero__surname {
  opacity: 0.26;
}

/* ---------- After the winner's graphic ---------- */
/* The header waits under the graphic, then rises in, one block after another,
   while the surname drives in from the right and settles at the bottom. */
.hero.has-intro .hero__body > *,
.hero.has-intro .hero__weather,
.hero.has-intro .hero__zoom {
  animation: hero-after-intro 700ms var(--ease-ios) backwards;
  animation-delay: calc(var(--intro-reveal) + var(--k, 0) * 55ms);
}

.hero.has-intro .hero__body > :nth-child(2) { --k: 1; }
.hero.has-intro .hero__body > :nth-child(3) { --k: 2; }
.hero.has-intro .hero__body > :nth-child(4) { --k: 3; }
.hero.has-intro .hero__body > :nth-child(5) { --k: 4; }
.hero.has-intro .hero__body > :nth-child(6) { --k: 5; }
.hero.has-intro .hero__body > :nth-child(7) { --k: 6; }
.hero.has-intro .hero__body > :nth-child(n + 8) { --k: 7; }
.hero.has-intro .hero__weather { --k: 2; }
.hero.has-intro .hero__zoom { --k: 6; }

.hero.has-intro .hero__surname {
  animation: hero-surname-drive 1100ms cubic-bezier(0.16, 1, 0.3, 1) var(--intro-reveal) backwards;
}

/* Skipped: everything is simply there. */
.hero.is-intro-skipped .hero__body > *,
.hero.is-intro-skipped .hero__weather,
.hero.is-intro-skipped .hero__zoom,
.hero.is-intro-skipped .hero__surname {
  animation: none;
}

@keyframes hero-after-intro {
  from {
    opacity: 0;
    transform: translate3d(0, 18px, 0);
  }
}

@keyframes hero-surname-drive {
  from {
    opacity: 0;
    transform: translateX(45%) skewX(-10deg);
  }
  40% {
    opacity: 1;
  }
}

@keyframes hero-surname-in {
  from {
    opacity: 0;
    transform: translateX(8%);
  }
}

@keyframes hero-drift {
  from {
    transform: scale(1.04) translate3d(0, 0, 0);
  }
  to {
    transform: scale(1.14) translate3d(-2%, -1%, 0);
  }
}

@keyframes hero-sweep {
  0%,
  35% {
    transform: translateX(-60%);
  }
  75%,
  100% {
    transform: translateX(60%);
  }
}

.hero__body {
  position: relative;
  display: grid;
  align-content: start;
  gap: 18px;
  max-width: 760px;
  padding: clamp(22px, 3.4vw, 44px);
}

.hero__back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  width: max-content;
  color: var(--c-text-2);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-decoration: none;
  text-transform: uppercase;
  transition: color var(--dur-2), gap var(--dur-2) var(--ease-ios);
}

.hero__back:hover {
  gap: 10px;
  color: var(--c-accent-text);
}

.hero__chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.hero__title {
  color: var(--c-text);
  font-size: clamp(30px, 4.6vw, 64px);
  overflow-wrap: anywhere;
  text-wrap: balance;
}

.hero__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
  margin: 0;
  padding: 0;
  list-style: none;
  color: var(--c-text-2);
  font-size: 14px;
}

.hero__meta li {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.hero__meta small {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 11px;
}

.hero__track {
  color: var(--c-text);
  font-weight: 600;
  text-decoration: underline;
  text-decoration-color: var(--c-blue-line);
  text-underline-offset: 4px;
  transition: color var(--dur-2), text-decoration-color var(--dur-2);
}

.hero__track:hover {
  color: var(--c-accent-text);
  text-decoration-color: currentColor;
}

.hero__schedule {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.hero__slot {
  display: grid;
  gap: 6px;
  padding: 12px 14px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-md);
  background: color-mix(in srgb, var(--c-bg) 45%, transparent);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  transition: transform var(--dur-3) var(--ease-ios), border-color var(--dur-2);
}

.hero__slot:hover {
  border-color: var(--c-blue-line);
  transform: translateY(-2px);
}

.hero__slot.is-key {
  border-color: var(--c-blue-line);
  background: color-mix(in srgb, var(--bm-blue) 16%, color-mix(in srgb, var(--c-bg) 50%, transparent));
}

.hero__slot.is-passed {
  opacity: 0.55;
}

.hero__slot-label,
.hero__finish-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.hero__slot strong {
  color: var(--c-text);
  font-size: 15px;
  font-weight: 600;
}

.hero__clock {
  display: grid;
  gap: 10px;
}

.hero__clock-head {
  display: flex;
  align-items: center;
  gap: 12px;
}

.hero__live {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 14px 18px;
  padding: 14px 16px;
  border: 1px solid color-mix(in srgb, var(--bm-red) 34%, transparent);
  border-radius: var(--r-lg);
  background: color-mix(in srgb, var(--bm-red) 9%, color-mix(in srgb, var(--c-bg) 50%, transparent));
}

.hero__live div {
  display: grid;
  gap: 3px;
}

.hero__live strong {
  font-family: var(--font-display);
  font-size: 16px;
  text-transform: uppercase;
}

.hero__live span {
  color: var(--c-text-2);
  font-size: 13.5px;
}

.hero__finish {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr) minmax(0, 0.7fr);
  gap: 8px;
}

.hero__finish-tile {
  position: relative;
  display: grid;
  align-content: start;
  gap: 6px;
  min-width: 0;
  padding: 14px 16px;
  overflow: hidden;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-md);
  background: color-mix(in srgb, var(--c-bg) 50%, transparent);
  color: var(--c-text);
  text-decoration: none;
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  transition: transform var(--dur-3) var(--ease-ios), border-color var(--dur-2);
}

.hero__finish-tile strong {
  overflow: hidden;
  font-size: 16px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* How many finished: in the race title's type, bold but not loud, leaning like the
   standings' place numerals. */
.hero__finish-tile .hero__count {
  justify-self: start;
  padding-right: 0.12em;
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
  transform: skewX(-12deg);
  transform-origin: left bottom;
}

.hero__finish-tile > span:last-child:not(.hero__finish-label) {
  color: var(--c-text-2);
  font-size: 13px;
}

.hero__finish-tile.is-winner {
  border-color: color-mix(in srgb, var(--bm-gold) 45%, transparent);
  background: linear-gradient(135deg, color-mix(in srgb, var(--bm-gold) 18%, transparent), color-mix(in srgb, var(--c-bg) 50%, transparent) 70%);
}

.hero__finish-tile.is-winner .hero__finish-label {
  color: color-mix(in srgb, var(--bm-gold) 80%, var(--c-text));
}

/* Chequered corner on the winner tile. */
.hero__finish-tile.is-winner::after {
  position: absolute;
  top: 0;
  right: 0;
  width: 54px;
  height: 54px;
  background: repeating-conic-gradient(color-mix(in srgb, var(--c-text) 22%, transparent) 0 25%, transparent 0 50%) 0 0 / 12px 12px;
  content: '';
  -webkit-mask-image: linear-gradient(225deg, #000, transparent 70%);
  mask-image: linear-gradient(225deg, #000, transparent 70%);
}

a.hero__finish-tile:hover {
  transform: translateY(-2px);
}

.hero__finish-tile.is-fastest {
  border-color: color-mix(in srgb, #a855f7 40%, transparent);
  background: color-mix(in srgb, #a855f7 12%, color-mix(in srgb, var(--c-bg) 50%, transparent));
}

.hero__finish-tile.is-fastest .hero__finish-label {
  color: #c084fc;
}

.hero__fill {
  display: grid;
  grid-template-columns: auto minmax(80px, 1fr) auto;
  align-items: center;
  gap: 14px;
  max-width: 480px;
}

.hero__fill-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--c-text-2);
  font-size: 13px;
}

.hero__fill strong {
  color: var(--c-text);
  font-size: 14px;
}

.hero__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
  margin-top: 4px;
}

.hero__state {
  min-height: 38px;
  padding: 0 14px;
  font-size: 11.5px;
}

.hero__note {
  color: var(--c-text-2);
  font-family: var(--font-mono);
  font-size: 12px;
}

.hero__weather {
  position: absolute;
  top: 18px;
  right: 18px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-pill);
  background: color-mix(in srgb, var(--c-bg) 52%, transparent);
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
  color: var(--c-text);
  font-size: 13px;
}

.hero__weather > svg {
  color: var(--bm-amber);
}

.hero__weather b {
  font-weight: 600;
}

.hero__temp {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding-left: 10px;
  border-left: 1px solid var(--c-line-strong);
}

.hero__zoom {
  position: absolute;
  right: 18px;
  bottom: 18px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 38px;
  padding: 0 16px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-pill);
  background: color-mix(in srgb, var(--c-bg) 52%, transparent);
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
  color: var(--c-text);
  cursor: pointer;
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 600;
  transition: transform var(--dur-2) var(--ease-ios), border-color var(--dur-2);
}

.hero__zoom:hover {
  border-color: var(--c-blue-line);
  transform: translateY(-2px);
}

.hero__zoom:active {
  transform: scale(0.96);
}

@media (max-width: 900px) {
  .hero__finish {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }

  .hero__finish-tile.is-winner {
    grid-column: 1 / -1;
  }
}

@media (max-width: 760px) {
  .hero {
    min-height: 0;
  }

  .hero__media {
    inset: 0 0 50% 0;
    -webkit-mask-image: linear-gradient(180deg, #000 30%, transparent);
    mask-image: linear-gradient(180deg, #000 30%, transparent);
  }

  .hero__shade {
    background: linear-gradient(180deg, transparent 0%, color-mix(in srgb, var(--c-bg) 55%, transparent) 36%, color-mix(in srgb, var(--c-bg) 82%, transparent) 100%);
  }

  .hero__body {
    padding-top: 74px;
    padding-bottom: 72px;
  }

  .hero__weather {
    top: 14px;
    right: 14px;
  }

  .hero__schedule {
    grid-template-columns: minmax(0, 1fr);
  }

  .hero__slot {
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
  }

  .hero__actions .ui-btn {
    flex: 1 1 auto;
  }

  .hero__zoom {
    right: 14px;
    bottom: 14px;
  }

  .hero__surname {
    font-size: clamp(76px, 24vw, 140px);
  }
}

@media (max-width: 520px) {
  .hero__fill {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .hero__fill .ui-meter {
    grid-column: 1 / -1;
    grid-row: 2;
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero__art,
  .hero__sweep,
  .hero__surname {
    animation: none;
  }
}
</style>
