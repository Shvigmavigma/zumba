<script setup>
// Weather forecast set by the organiser: the chance of every condition and the
// track temperature.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Thermometer } from 'lucide-vue-next'
import { WEATHER_KEYS, dominantWeatherKey, weatherLabelKey } from '../../raceDisplay'
import { WEATHER_ICONS } from './raceFormat'

const props = defineProps({
  race: { type: Object, required: true }
})
const { t } = useI18n()

const dominant = computed(() => dominantWeatherKey(props.race))
const rows = computed(() => WEATHER_KEYS.map((key) => ({
  key,
  icon: WEATHER_ICONS[key],
  label: t(weatherLabelKey(key)),
  value: Math.round(Number(props.race.weather_chances?.[key] || 0))
})))
const temperature = computed(() => {
  const value = Number(props.race.track_temperature)
  return props.race.track_temperature !== null && Number.isFinite(value) ? `${value.toFixed(1)} °C` : t('common.none')
})
</script>

<template>
  <section class="wx ui-card" aria-labelledby="race-weather-title">
    <header class="ui-card__head">
      <div class="ui-card__title">
        <p class="ui-eyebrow ui-eyebrow--accent">{{ t('racePage.weather.eyebrow') }}</p>
        <h2 id="race-weather-title">{{ t('raceCard.weather') }}</h2>
      </div>
      <div class="wx__temp">
        <Thermometer :size="16" />
        <div>
          <span>{{ t('racePage.weather.track') }}</span>
          <strong class="ui-num">{{ temperature }}</strong>
        </div>
      </div>
    </header>

    <ul class="wx__list">
      <li v-for="(row, index) in rows" :key="row.key" v-reveal="{ delay: index * 50, y: 8, blur: 0 }" class="wx__row" :class="{ 'is-main': row.key === dominant, 'is-zero': !row.value }">
        <component :is="row.icon" class="wx__icon" :size="18" aria-hidden="true" />
        <span class="wx__label">{{ row.label }}</span>
        <span class="ui-meter wx__meter"><span :style="{ '--value': `${row.value}%` }"></span></span>
        <strong class="ui-num">{{ row.value }}%</strong>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.wx__temp {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px 8px 10px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-md);
  background: var(--c-sunken);
  color: var(--bm-amber);
}

.wx__temp div {
  display: grid;
  gap: 2px;
}

.wx__temp span {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.wx__temp strong {
  color: var(--c-text);
  font-size: 16px;
}

.wx__list {
  display: grid;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.wx__row {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) minmax(60px, 0.8fr) 44px;
  align-items: center;
  gap: 12px;
  padding: 8px 10px;
  border-radius: var(--r-sm);
  color: var(--c-text-2);
  font-size: 13.5px;
  transition: background-color var(--dur-2);
}

.wx__row:hover {
  background: var(--c-blue-soft);
}

.wx__row strong {
  color: var(--c-text);
  font-size: 13px;
  text-align: right;
}

.wx__row.is-main {
  background: var(--c-blue-soft);
  color: var(--c-text);
  font-weight: 600;
}

.wx__row.is-main .wx__icon {
  color: var(--bm-amber);
}

.wx__row.is-zero {
  opacity: 0.5;
}

.wx__icon {
  color: var(--c-text-3);
}

.wx__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wx__meter {
  height: 5px;
}
</style>
