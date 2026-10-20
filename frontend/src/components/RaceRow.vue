<script setup>
// One race in a schedule list: date plate, track artwork, name, class, start
// time, status and grid fill. The whole row opens the race.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { ArrowRight, ExternalLink } from 'lucide-vue-next'
import { gameLabel, isExternalRace, raceOpenHref, statusLabel } from '../i18nLabels'
import { dominantWeatherKey, fillPercent, isRaceRegistered, raceStatusTone, registeredCount, trackImageFor, weatherImageUrl, weatherLabelKey } from '../raceDisplay'
import { formatInTimeZone } from '../timezone'

const props = defineProps({
  race: { type: Object, required: true },
  assets: { type: Object, default: null },
  weatherSettings: { type: Object, default: () => ({}) }
})

const { t } = useI18n()
const router = useRouter()
const external = computed(() => isExternalRace(props.race))
const href = computed(() => raceOpenHref(props.race))
const image = computed(() => trackImageFor(props.assets, props.race))
const weather = computed(() => weatherImageUrl(props.race, props.weatherSettings))
const tone = computed(() => raceStatusTone(props.race.status))
const registered = computed(() => isRaceRegistered(props.race))

function open(event) {
  if (event?.target?.closest?.('a, button, input, select, textarea, summary')) return
  if (external.value) {
    window.open(href.value, '_blank', 'noopener,noreferrer')
    return
  }
  router.push(href.value)
}
</script>

<template>
  <article
    v-spotlight
    class="row"
    :class="{ 'is-registered': registered, 'is-finished': race.status === 'finished' }"
    role="link"
    tabindex="0"
    :aria-label="race.name"
    @click="open"
    @keydown.enter.prevent="open"
  >
    <div class="row__date">
      <strong class="ui-num">{{ formatInTimeZone(race.datetime_start, { day: '2-digit' }) }}</strong>
      <span>{{ formatInTimeZone(race.datetime_start, { month: 'short' }).replace('.', '') }}</span>
    </div>

    <div class="row__thumb" aria-hidden="true">
      <img v-if="image" v-track-art :src="image" alt="" loading="lazy" />
      <span v-else class="row__thumb-fallback">{{ gameLabel(t, race.game) }}</span>
    </div>

    <div class="row__main">
      <div class="row__name">
        <a v-if="external" :href="href" target="_blank" rel="noopener noreferrer">{{ race.name }}</a>
        <RouterLink v-else :to="href">{{ race.name }}</RouterLink>
        <img v-if="weather" class="row__weather" :src="weather" :alt="t(weatherLabelKey(dominantWeatherKey(race)))" :title="t(weatherLabelKey(dominantWeatherKey(race)))" />
      </div>
      <span class="row__sub">{{ race.track }} · {{ gameLabel(t, race.game) }}</span>
    </div>

    <div class="row__tags">
      <span v-if="race.car_class" class="ui-chip ui-chip--blue">{{ race.car_class }}</span>
      <span v-if="race.is_team_event" class="ui-chip">{{ t('raceFilters.teamShort') }}</span>
    </div>

    <div class="row__time">
      <strong class="ui-num">{{ formatInTimeZone(race.datetime_start, { hour: '2-digit', minute: '2-digit' }) }}</strong>
      <small>{{ t('fields.registrationEnd') }} {{ formatInTimeZone(race.datetime_end, { day: '2-digit', month: '2-digit' }) }}</small>
    </div>

    <div class="row__status">
      <span class="row__mobile-time ui-num">{{ formatInTimeZone(race.datetime_start, { hour: '2-digit', minute: '2-digit' }) }} ·</span>
      <span class="ui-dot" :class="[tone ? `ui-dot--${tone}` : '', { 'ui-dot--live': race.status === 'ongoing' || race.status === 'registration_open' }]"></span>
      <span>{{ statusLabel(t, race.status) }}</span>
      <span v-if="registered" class="ui-chip ui-chip--green row__entered">{{ t('home.calendar.registered') }}</span>
    </div>

    <div class="row__fill">
      <template v-if="race.game !== 'LMU'">
        <span class="ui-num">{{ registeredCount(race) }}<small> / {{ race.max_pilots }}</small></span>
        <span class="ui-meter"><span :style="{ '--value': `${fillPercent(race)}%` }"></span></span>
      </template>
      <span v-else class="row__nolimit">{{ t('home.calendar.noLimit') }}</span>
    </div>

    <span class="row__go" aria-hidden="true">
      <ExternalLink v-if="external" :size="17" />
      <ArrowRight v-else :size="17" />
    </span>
  </article>
</template>

<style scoped>
.row {
  display: grid;
  grid-template-columns: 64px 132px minmax(0, 1.6fr) minmax(70px, auto) 96px minmax(150px, 0.9fr) 110px 40px;
  align-items: center;
  gap: 18px;
  padding: 10px 14px 10px 10px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-lg);
  background: var(--c-surface);
  cursor: pointer;
  transition: border-color var(--dur-2), background-color var(--dur-2), transform var(--dur-3) var(--ease-ios);
}

.row:hover {
  border-color: var(--c-blue-line);
  transform: translateY(-2px);
}

.row:active {
  transform: scale(0.995);
}

.row.is-registered {
  border-color: color-mix(in srgb, var(--bm-green) 32%, transparent);
}

.row.is-finished {
  background: color-mix(in srgb, var(--c-surface) 70%, transparent);
}

.row__date {
  display: grid;
  justify-items: center;
  gap: 2px;
  padding: 8px 0;
  border-radius: var(--r-md);
  background: var(--c-sunken);
}

.row__date strong {
  color: var(--c-text);
  font-size: 22px;
  font-weight: 600;
  line-height: 1;
}

.row__date span {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.row__thumb {
  display: grid;
  place-items: center;
  height: 64px;
  overflow: hidden;
  border-radius: var(--r-sm);
  background: linear-gradient(135deg, color-mix(in srgb, var(--bm-blue) 40%, var(--c-elevated)), var(--c-elevated));
}

.row__thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 900ms var(--ease-out);
}

.row:hover .row__thumb img {
  transform: scale(1.08);
}

.row__thumb-fallback {
  color: rgba(255, 255, 255, 0.85);
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 800;
}

.row__main {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.row__name {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.row__name a {
  overflow: hidden;
  color: var(--c-text);
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 700;
  text-decoration: none;
  text-overflow: ellipsis;
  text-transform: uppercase;
  white-space: nowrap;
}

.row__weather {
  width: 22px;
  height: 22px;
  flex: 0 0 auto;
  object-fit: contain;
}

.row__sub {
  overflow: hidden;
  color: var(--c-text-3);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.row__time {
  display: grid;
  gap: 2px;
}

.row__time strong {
  color: var(--c-text);
  font-size: 17px;
  font-weight: 600;
}

.row__time small {
  color: var(--c-text-3);
  font-size: 11px;
  white-space: nowrap;
}

.row__status {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 9px;
  color: var(--c-text);
  font-size: 13.5px;
}

.row__entered {
  min-height: 22px;
}

.row__mobile-time {
  display: none;
  color: var(--c-text-2);
}

.row__fill {
  display: grid;
  gap: 6px;
}

.row__fill .ui-num {
  color: var(--c-text);
  font-size: 14px;
}

.row__fill small {
  color: var(--c-text-3);
}

.row__nolimit {
  color: var(--c-text-3);
  font-size: 12px;
}

.row__go {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border: 1px solid var(--c-line-strong);
  border-radius: 50%;
  color: var(--c-text-2);
  transition: background-color var(--dur-2), color var(--dur-2), transform var(--dur-3) var(--ease-ios), border-color var(--dur-2);
}

.row:hover .row__go {
  border-color: var(--bm-blue);
  background: var(--bm-blue);
  color: #fff;
  transform: translateX(3px);
}

@media (max-width: 1240px) {
  .row {
    grid-template-columns: 58px 104px minmax(0, 1fr) 92px minmax(130px, auto) 40px;
  }

  .row__tags,
  .row__fill {
    display: none;
  }
}

@media (max-width: 760px) {
  .row {
    grid-template-columns: 54px minmax(0, 1fr) 30px;
    grid-template-areas:
      'date main go'
      'date meta go';
    gap: 6px 12px;
    padding: 10px;
  }

  .row__thumb,
  .row__tags,
  .row__fill {
    display: none;
  }

  .row__date {
    grid-area: date;
    align-self: stretch;
    align-content: center;
  }

  .row__main {
    grid-area: main;
  }

  .row__time {
    display: none;
  }

  .row__mobile-time {
    display: inline;
  }

  .row__status {
    grid-area: meta;
    font-size: 12.5px;
  }

  .row__go {
    grid-area: go;
    width: 30px;
    height: 30px;
  }

  .row__name a {
    font-size: 13.5px;
  }
}
</style>
