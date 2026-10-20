<script setup>
// The evening's schedule inside the race briefing: briefing, practice,
// qualification and the race as a timeline on a plate of its own, so a pilot
// who is signing up sees when to be on the server. The race row is lit and
// its dot beats. Shows nothing until staff give the sessions their times.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Clock3 } from 'lucide-vue-next'
import { formatTimeRangeInTimeZone, timeZoneShortName } from '../../timezone'
import { raceSessions } from './sessionSchedule'

const MINUTES_IN_HOUR = 60

const props = defineProps({
  race: { type: Object, required: true }
})
const { t } = useI18n()

const labels = computed(() => ({
  briefing: t('raceDetails.briefing'),
  practice: t('raceDetails.practice'),
  qualification: t('fields.qualification'),
  race_session: t('raceDetails.raceSession')
}))
const sessions = computed(() => raceSessions(props.race).map((session) => ({
  ...session,
  label: labels.value[session.key],
  time: formatTimeRangeInTimeZone(session.start, session.end, props.race.datetime_start).replace(' - ', ' – '),
  length: lengthLabel(session.minutes)
})))
const zone = computed(() => timeZoneShortName(props.race.datetime_start))

function lengthLabel(minutes) {
  if (!minutes) return ''
  const hours = Math.floor(minutes / MINUTES_IN_HOUR)
  const rest = minutes % MINUTES_IN_HOUR
  if (!hours) return t('racePage.brief.minutes', { count: rest })
  return rest ? t('racePage.brief.hoursMinutes', { hours, minutes: rest }) : t('racePage.brief.hours', { hours })
}
</script>

<template>
  <section v-if="sessions.length" class="schedule" aria-labelledby="race-schedule-title">
    <header class="schedule__head">
      <span class="schedule__icon"><Clock3 :size="18" /></span>
      <h3 id="race-schedule-title" class="schedule__title">{{ t('racePage.brief.schedule') }}</h3>
      <span v-if="zone" class="ui-chip ui-chip--blue schedule__zone">{{ zone }}</span>
    </header>
    <ol class="schedule__list">
      <li v-for="session in sessions" :key="session.key" class="schedule__row" :class="{ 'is-main': session.main }">
        <span class="schedule__dot" aria-hidden="true"></span>
        <span class="schedule__what">
          <strong>{{ session.label }}</strong>
          <small v-if="session.length">{{ session.length }}</small>
        </span>
        <b class="schedule__time ui-num">{{ session.time }}</b>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.schedule {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--c-blue-line);
  border-radius: var(--r-lg);
  background:
    linear-gradient(165deg, var(--c-blue-soft), transparent 62%),
    var(--c-surface-solid);
}

.schedule__head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.schedule__icon {
  display: grid;
  flex: none;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 11px;
  background: var(--bm-blue);
  color: #fff;
}

.schedule__title {
  flex: 1 1 auto;
  min-width: 0;
  margin: 0;
  font-family: var(--font-display);
  font-size: 15px;
  letter-spacing: 0.01em;
  text-transform: uppercase;
}

.schedule__zone {
  flex: none;
}

.schedule__list {
  display: grid;
  margin: 0;
  padding: 0;
  list-style: none;
}

.schedule__row {
  position: relative;
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border: 1px solid transparent;
  border-radius: var(--r-sm);
}

.schedule__dot {
  position: relative;
  z-index: 1;
  justify-self: center;
  width: 9px;
  height: 9px;
  border: 2px solid var(--c-text-3);
  border-radius: 50%;
  background: var(--c-surface-solid);
}

/* The line that joins a session's dot to the next one. */
.schedule__row:not(:last-child)::after {
  position: absolute;
  top: calc(50% + 7px);
  bottom: calc(-50% + 7px);
  left: 18.5px;
  width: 1px;
  background: var(--c-line-strong);
  content: '';
}

.schedule__what {
  display: grid;
  gap: 1px;
  min-width: 0;
}

.schedule__what strong {
  color: var(--c-text);
  font-size: 15px;
  font-weight: 600;
}

.schedule__what small {
  color: var(--c-text-3);
  font-size: 12px;
}

.schedule__time {
  color: var(--c-text);
  font-size: 15.5px;
  font-weight: 600;
  white-space: nowrap;
}

/* ---------- The race itself: lit, with a dot that beats ---------- */
.schedule__row.is-main {
  border-color: var(--c-blue-line);
  background: color-mix(in srgb, var(--bm-blue) 20%, transparent);
}

.schedule__row.is-main .schedule__what strong {
  font-weight: 700;
}

.schedule__row.is-main .schedule__time {
  color: var(--c-accent-text);
  font-size: 17px;
}

.schedule__row.is-main .schedule__dot {
  border-color: var(--bm-blue-bright);
  background: var(--bm-blue-bright);
}

.schedule__row.is-main .schedule__dot::after {
  position: absolute;
  inset: -2px;
  border-radius: 50%;
  background: var(--bm-blue-bright);
  content: '';
  animation: schedule-beat 2.2s var(--ease-out) infinite;
}

@keyframes schedule-beat {
  0% {
    opacity: 0.65;
    transform: scale(1);
  }
  70%,
  100% {
    opacity: 0;
    transform: scale(3.2);
  }
}

@media (prefers-reduced-motion: reduce) {
  .schedule__row.is-main .schedule__dot::after {
    animation: none;
    opacity: 0;
  }
}
</style>
