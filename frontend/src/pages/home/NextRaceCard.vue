<script setup>
// The next race on the grid: track artwork, schedule, a live countdown and a
// start gantry whose lamps light up as the start approaches (one per day,
// all five in the final hours).
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowUpRight, CalendarClock, ExternalLink, Flag, MapPin, Thermometer, Users } from 'lucide-vue-next'
import { api } from '../../api'
import EmptyState from '../../ui/EmptyState.vue'
import Countdown from '../../ui/fx/Countdown.vue'
import StartLights from '../../ui/fx/StartLights.vue'
import { gameLabel, isExternalRace, raceOpenHref } from '../../i18nLabels'
import { dominantWeatherKey, fillPercent, isRaceRegistered, loadRaceAssets, registeredCount, trackImageFor, weatherImageUrl, weatherLabelKey } from '../../raceDisplay'
import { state } from '../../store'
import { formatInTimeZone, timeZoneShortName } from '../../timezone'

const props = defineProps({
  weatherSettings: { type: Object, default: () => ({}) }
})

const { t } = useI18n()
const race = ref(null)
const assets = ref(null)
const loading = ref(true)
const error = ref('')
const now = ref(Date.now())
let clock = 0

const isLive = computed(() => race.value?.status === 'ongoing')
const trackImage = computed(() => trackImageFor(assets.value, race.value))
const weatherImage = computed(() => (race.value ? weatherImageUrl(race.value, props.weatherSettings) : ''))
const weatherKey = computed(() => (race.value ? dominantWeatherKey(race.value) : 'clear'))
const registered = computed(() => isRaceRegistered(race.value))
const external = computed(() => race.value && isExternalRace(race.value))
const tz = computed(() => timeZoneShortName(race.value?.datetime_start))
const hoursLeft = computed(() => (race.value ? (new Date(race.value.datetime_start).getTime() - now.value) / 3600000 : 0))
/** One lamp per remaining day inside the final five; all five in the last six hours. */
const litLamps = computed(() => {
  if (isLive.value) return 5
  if (hoursLeft.value <= 6) return 5
  return Math.max(0, Math.min(4, 5 - Math.ceil(hoursLeft.value / 24)))
})
const schedule = computed(() => {
  if (!race.value) return []
  return [
    { key: 'opens', label: t('home.next.opens'), value: race.value.registration_start },
    { key: 'closes', label: t('home.next.closes'), value: race.value.datetime_end },
    { key: 'start', label: t('home.next.start'), value: race.value.datetime_start, highlight: true }
  ].map((item) => ({ ...item, passed: new Date(item.value).getTime() < now.value }))
})

function formatMoment(value) {
  return formatInTimeZone(value, { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function formatDay(value) {
  return formatInTimeZone(value, { weekday: 'short', day: 'numeric', month: 'long' })
}

// A race stays "ongoing" until staff close it; one left open for days must not
// hold the home card. 24 hours still covers endurance events.
const LIVE_WINDOW_MS = 24 * 3600000

function pickNextRace(list) {
  const live = list.find((item) => item.status === 'ongoing' && Date.now() - new Date(item.datetime_start).getTime() < LIVE_WINDOW_MS)
  if (live) return live
  return [...list].sort((a, b) => new Date(a.datetime_start) - new Date(b.datetime_start))
    .find((item) => new Date(item.datetime_start).getTime() > Date.now() - 3 * 3600000) || null
}

onMounted(async () => {
  clock = window.setInterval(() => { now.value = Date.now() }, 60000)
  try {
    const params = new URLSearchParams({ status_filter: 'not_finished', include_championship: 'true', limit: '100', offset: '0' })
    const [list, loadedAssets] = await Promise.all([
      api(`/races?${params.toString()}`),
      loadRaceAssets().catch(() => null)
    ])
    race.value = pickNextRace(list)
    assets.value = loadedAssets
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => window.clearInterval(clock))
</script>

<template>
  <article v-if="race" v-spotlight class="next ui-glass" :class="{ 'is-live': isLive }">
    <div class="next__media" aria-hidden="true">
      <img v-if="trackImage" v-track-art class="next__image" :src="trackImage" alt="" />
      <div v-else class="next__image next__image--fallback"></div>
    </div>
    <div class="next__shade" aria-hidden="true"></div>

    <div class="next__body">
      <header class="next__head">
        <span class="ui-chip ui-chip--solid">{{ gameLabel(t, race.game) }}</span>
        <span v-if="isLive" class="ui-chip ui-chip--red"><span class="ui-dot ui-dot--red ui-dot--live"></span>{{ t('home.next.live') }}</span>
        <span v-else class="ui-eyebrow ui-eyebrow--accent">{{ t('home.next.eyebrow') }}</span>
        <span v-if="race.championship_round" class="ui-eyebrow">· {{ t('home.next.round', { round: race.championship_round }) }}</span>
      </header>

      <h2 v-split class="next__title ui-display">{{ race.name }}</h2>

      <ul class="next__meta">
        <li><MapPin :size="15" />{{ race.track }}</li>
        <li><CalendarClock :size="15" />{{ formatDay(race.datetime_start) }} · {{ formatInTimeZone(race.datetime_start, { hour: '2-digit', minute: '2-digit' }) }} <small>{{ tz }}</small></li>
        <li v-if="race.car_class"><span class="ui-chip ui-chip--blue">{{ race.car_class }}</span></li>
        <li v-if="race.is_official"><span class="ui-chip ui-chip--amber"><Flag :size="12" />{{ t('home.next.official') }}</span></li>
        <li v-if="race.is_team_event"><span class="ui-chip">{{ t('home.next.team') }}</span></li>
      </ul>

      <ol class="next__schedule">
        <li v-for="(item, index) in schedule" :key="item.key" v-reveal="{ delay: 120 + index * 80, y: 10, blur: 4 }" class="next__slot" :class="{ 'is-passed': item.passed, 'is-key': item.highlight }">
          <span class="next__slot-label">{{ item.label }}</span>
          <strong class="ui-num">{{ formatMoment(item.value) }}</strong>
        </li>
      </ol>

      <div v-if="!isLive" class="next__clock">
        <div class="next__clock-head">
          <StartLights size="sm" :lit="litLamps" :label="t('home.next.toStart')" />
          <span class="ui-eyebrow">{{ t('home.next.toStart') }}</span>
        </div>
        <Countdown :target="race.datetime_start" />
      </div>

      <div v-if="race.game !== 'LMU'" class="next__grid-fill">
        <span class="next__fill-label"><Users :size="15" />{{ t('home.next.pilots') }}</span>
        <span class="ui-meter"><span :style="{ '--value': `${fillPercent(race)}%` }"></span></span>
        <strong class="ui-num">{{ registeredCount(race) }} / {{ race.max_pilots }}</strong>
      </div>

      <footer class="next__actions">
        <a v-if="external" v-magnet class="ui-btn ui-btn--primary ui-btn--lg" :href="raceOpenHref(race)" target="_blank" rel="noopener noreferrer">
          {{ t('home.next.openServer') }}<ExternalLink :size="17" />
        </a>
        <template v-else-if="registered">
          <span class="ui-chip ui-chip--green next__entered"><span class="ui-dot ui-dot--green"></span>{{ t('home.next.registered') }}</span>
          <RouterLink class="ui-btn ui-btn--primary ui-btn--lg" :to="raceOpenHref(race)">{{ t('home.next.openRace') }}<ArrowUpRight :size="17" /></RouterLink>
        </template>
        <RouterLink v-else-if="race.status === 'registration_open'" v-magnet v-spark class="ui-btn ui-btn--primary ui-btn--lg" :to="raceOpenHref(race)">
          {{ t('home.next.join') }}<ArrowUpRight :size="17" />
        </RouterLink>
        <RouterLink v-else class="ui-btn ui-btn--primary ui-btn--lg" :to="raceOpenHref(race)">{{ t('home.next.openRace') }}<ArrowUpRight :size="17" /></RouterLink>
        <RouterLink class="ui-btn ui-btn--outline ui-btn--lg" to="/calendar">{{ t('home.next.allRaces') }}</RouterLink>
        <RouterLink v-if="!state.user && race.status === 'registration_open'" class="next__login" to="/login">* {{ t('home.next.loginToJoin') }}</RouterLink>
      </footer>
    </div>

    <div v-if="weatherImage || race.track_temperature !== null" class="next__weather" :title="t(weatherLabelKey(weatherKey))">
      <img v-if="weatherImage" :src="weatherImage" :alt="t(weatherLabelKey(weatherKey))" />
      <span v-if="race.track_temperature !== null && race.track_temperature !== undefined" class="ui-num">
        <Thermometer :size="14" />{{ Number(race.track_temperature).toFixed(0) }}°
      </span>
    </div>
  </article>

  <div v-else class="next next--empty ui-glass">
    <EmptyState v-if="loading" loading :title="t('ui.common.loading')" compact />
    <EmptyState v-else :icon="Flag" :title="error || t('home.next.noneTitle')" :text="error ? '' : t('home.next.noneText')">
      <RouterLink class="ui-btn ui-btn--outline ui-btn--sm" to="/calendar">{{ t('home.calendar.openCalendar') }}</RouterLink>
    </EmptyState>
  </div>
</template>

<style scoped>
.next {
  position: relative;
  display: grid;
  min-height: 540px;
  overflow: hidden;
  border-radius: var(--r-xl);
}

.next--empty {
  min-height: 0;
  padding: 10px;
}

/* A live race has no countdown block; let the card hug its content. */
.next.is-live {
  min-height: 0;
}

.next__media {
  position: absolute;
  inset: 0 0 0 30%;
  z-index: 0;
  overflow: hidden;
  -webkit-mask-image: linear-gradient(90deg, transparent 0%, #000 38%);
  mask-image: linear-gradient(90deg, transparent 0%, #000 38%);
}

.next__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.75;
  animation: next-drift 24s var(--ease-out) infinite alternate;
}

.next__image--fallback {
  background:
    radial-gradient(50% 60% at 70% 40%, color-mix(in srgb, var(--bm-blue) 45%, transparent), transparent 70%),
    repeating-linear-gradient(115deg, transparent 0 22px, color-mix(in srgb, var(--c-text) 4%, transparent) 22px 23px);
}

:root[data-theme='light'] .next__image {
  opacity: 0.32;
}

.next__shade {
  position: absolute;
  inset: 0;
  z-index: 0;
  background: linear-gradient(90deg, color-mix(in srgb, var(--c-bg) 70%, transparent) 0%, color-mix(in srgb, var(--c-bg) 35%, transparent) 55%, transparent 100%);
  pointer-events: none;
}

@keyframes next-drift {
  from {
    transform: scale(1.04) translate3d(0, 0, 0);
  }
  to {
    transform: scale(1.12) translate3d(-2%, -1%, 0);
  }
}

.next__body {
  position: relative;
  z-index: 1;
  display: grid;
  align-content: start;
  gap: 18px;
  max-width: 680px;
  padding: clamp(22px, 3.2vw, 40px);
}

.next__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.next__title {
  color: var(--c-text);
  font-size: clamp(28px, 4.2vw, 56px);
  text-wrap: balance;
}

.next__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 18px;
  margin: 0;
  padding: 0;
  list-style: none;
  color: var(--c-text-2);
  font-size: 14px;
}

.next__meta li {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.next__meta small {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 11px;
}

.next__schedule {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.next__slot {
  display: grid;
  gap: 6px;
  padding: 12px 14px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-md);
  background: color-mix(in srgb, var(--c-bg) 45%, transparent);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
}

.next__slot.is-key {
  border-color: var(--c-blue-line);
  background: color-mix(in srgb, var(--bm-blue) 16%, color-mix(in srgb, var(--c-bg) 50%, transparent));
}

.next__slot.is-passed {
  opacity: 0.55;
}

.next__slot-label {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.next__slot strong {
  color: var(--c-text);
  font-size: 15px;
  font-weight: 600;
}

.next__clock {
  display: grid;
  gap: 10px;
}

.next__clock-head {
  display: flex;
  align-items: center;
  gap: 12px;
}

.next__grid-fill {
  display: grid;
  grid-template-columns: auto minmax(80px, 1fr) auto;
  align-items: center;
  gap: 14px;
  max-width: 460px;
}

.next__fill-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--c-text-2);
  font-size: 13px;
}

.next__grid-fill strong {
  color: var(--c-text);
  font-size: 14px;
}

.next__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 12px;
  margin-top: 4px;
}

/* As tall as the buttons beside it, so the row reads as one set of three. */
.next__entered {
  justify-content: center;
  gap: 10px;
  min-height: 54px;
  padding: 0 24px;
  font-size: 12.5px;
  letter-spacing: 0.1em;
}

.next__entered .ui-dot {
  width: 9px;
  height: 9px;
}

.next__login {
  flex-basis: 100%;
  color: var(--c-accent-text);
  font-size: 13px;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.next__weather {
  position: absolute;
  top: 18px;
  right: 18px;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px 6px 6px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-pill);
  background: color-mix(in srgb, var(--c-bg) 50%, transparent);
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
  color: var(--c-text);
  font-size: 13px;
}

.next__weather img {
  width: 30px;
  height: 30px;
  object-fit: contain;
}

.next__weather span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

@media (max-width: 760px) {
  .next {
    min-height: 0;
  }

  .next__media {
    inset: 0 0 45% 0;
    -webkit-mask-image: linear-gradient(180deg, #000 30%, transparent);
    mask-image: linear-gradient(180deg, #000 30%, transparent);
  }

  .next__shade {
    background: linear-gradient(180deg, transparent 0%, color-mix(in srgb, var(--c-bg) 55%, transparent) 40%, color-mix(in srgb, var(--c-bg) 80%, transparent) 100%);
  }

  .next__body {
    padding-top: 120px;
  }

  .next__schedule {
    grid-template-columns: minmax(0, 1fr);
  }

  .next__slot {
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
  }

  .next__actions .ui-btn,
  .next__entered {
    flex: 1 1 auto;
  }
}

@media (prefers-reduced-motion: reduce) {
  .next__image {
    animation: none;
  }
}
</style>
