<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useIntersectionObserver, useMediaQuery } from '@vueuse/core'
import { ArrowDown, CarFront, Droplets, Flag, Lightbulb, Timer } from 'lucide-vue-next'
import { api } from '../api'
import { state } from '../store'
import FormField from '../ui/FormField.vue'
import PageHeader from '../ui/PageHeader.vue'
import SegmentedControl from '../ui/SegmentedControl.vue'
import SwitchToggle from '../ui/SwitchToggle.vue'
import RollingNumber from '../ui/fx/RollingNumber.vue'
import { prefersReducedMotion } from '../ui/motion/env'
import CarPicker from './fuel/CarPicker.vue'
import FuelResults from './fuel/FuelResults.vue'
import NumberField from './fuel/NumberField.vue'
import { fuelCars, presets } from './fuel/fuelData'
import { fuelFixed } from './fuel/fuelFormat'

const { t } = useI18n()

const sim = ref('ACC')
const car = ref('Ferrari 296 GT3 2023')
const carSearch = ref(car.value)
const assetFuelCars = ref({})
const presetIndex = ref(0)
const mode = ref('time')
const unit = ref('L')
const raceHours = ref(1)
const raceMinutes = ref(0)
const raceLaps = ref(20)
const lapMinutes = ref(2)
const lapSeconds = ref(5)
const fuelPerLap = ref(3.2)
const tank = ref(110)
const reserveLaps = ref(1)
const currentFuel = ref('')
const formationLap = ref(false)

const simPresets = computed(() => presets[sim.value] || [])
const carOptions = computed(() => mergeCarLists(fuelCars[sim.value] || [], assetFuelCars.value[sim.value] || []))
const filteredCarOptions = computed(() => {
  const needle = carSearch.value.trim().toLowerCase()
  const filtered = needle
    ? carOptions.value.filter((item) => `${item.label} ${item.class}`.toLowerCase().includes(needle))
    : carOptions.value
  return filtered.slice(0, 24)
})
const selectedPreset = computed(() => simPresets.value[Number(presetIndex.value)] || simPresets.value[0])
const selectedCarPreset = computed(() => carOptions.value.find((item) => item.label === car.value))
const lapSecondsTotal = computed(() => Math.max(0, Number(lapMinutes.value) * 60 + Number(lapSeconds.value)))
const expectedLaps = computed(() => {
  if (mode.value === 'laps') return Math.max(0, Math.ceil(Number(raceLaps.value) || 0))
  const raceSeconds = Math.max(0, Number(raceHours.value) * 3600 + Number(raceMinutes.value) * 60)
  if (!raceSeconds || !lapSecondsTotal.value) return 0
  return Math.ceil(raceSeconds / lapSecondsTotal.value)
})
const totalReserveLaps = computed(() => Math.max(0, Number(reserveLaps.value) || 0) + (formationLap.value ? 1 : 0))
const minimumFuel = computed(() => expectedLaps.value * Math.max(0, Number(fuelPerLap.value) || 0))
const recommendedFuel = computed(() => minimumFuel.value + totalReserveLaps.value * Math.max(0, Number(fuelPerLap.value) || 0))
const pitStops = computed(() => Number(tank.value) > 0 ? Math.max(0, Math.ceil(recommendedFuel.value / Number(tank.value)) - 1) : 0)
const fullTankLaps = computed(() => Number(tank.value) > 0 && Number(fuelPerLap.value) > 0 ? Math.floor(Number(tank.value) / Number(fuelPerLap.value)) : 0)
const stintLaps = computed(() => Math.ceil((expectedLaps.value + totalReserveLaps.value) / (pitStops.value + 1)) || 0)
const startFuel = computed(() => Math.min(recommendedFuel.value, Number(tank.value) || recommendedFuel.value))
const fuelToAdd = computed(() => currentFuel.value === '' ? null : Math.max(0, recommendedFuel.value - (Number(currentFuel.value) || 0)))
const presetHint = computed(() => state.locale === 'en' ? selectedPreset.value?.hintEn : selectedPreset.value?.hintRu)
const warningKey = computed(() => {
  if (!lapSecondsTotal.value || !Number(fuelPerLap.value)) return 'fill'
  if (Number(tank.value) > 0 && recommendedFuel.value > Number(tank.value)) return 'stopNeeded'
  return 'ready'
})

// View-only helpers for the redesigned layout.
const simOptions = computed(() => Object.keys(presets).map((name) => ({ value: name, label: name })))
const unitOptions = computed(() => [
  { value: 'L', label: `L · ${t('fuelPage.units.liters')}` },
  { value: 'gal', label: `gal · ${t('fuelPage.units.gallons')}` }
])
const modeOptions = computed(() => [
  { value: 'time', label: t('fuelPage.timeRace'), icon: Timer },
  { value: 'laps', label: t('fuelPage.lapRace'), icon: Flag }
])
const lapPreview = computed(() => {
  const total = lapSecondsTotal.value
  if (!total) return '—'
  const minutes = Math.floor(total / 60)
  return `${minutes}:${(total - minutes * 60).toFixed(3).padStart(6, '0')}`
})

// On one-column layouts the result sits below the form: a small dock keeps
// the main number in sight until the result panel scrolls into view.
const results = ref(null)
const resultsAhead = ref(false)
const isSingleColumn = useMediaQuery('(max-width: 1180px)')
const showDock = computed(() => isSingleColumn.value && resultsAhead.value)

useIntersectionObserver(results, ([entry]) => {
  if (!entry) return
  resultsAhead.value = !entry.isIntersecting && entry.boundingClientRect.top > 0
}, { threshold: 0.08 })

function scrollToResults() {
  results.value?.$el?.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'start' })
}

function selectSim(value) {
  if (value === sim.value) return
  sim.value = value
  handleSimChange()
}

function handleSimChange() {
  presetIndex.value = 0
  car.value = carOptions.value[0]?.label || ''
  carSearch.value = car.value
  if (!applyCarPreset()) applyPreset()
}

function selectCar(item) {
  car.value = item.label
  carSearch.value = item.label
}

function mergeCarLists(...lists) {
  const seen = new Set()
  return lists.flat().filter((item) => {
    const key = item.label.trim().toLowerCase()
    if (!key || seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function fallbackPresetForClass(simName, className) {
  const normalized = String(className || '').toLowerCase()
  return (presets[simName] || []).find((item) => item.label.toLowerCase() === normalized)
    || (presets[simName] || []).find((item) => normalized.includes(item.label.toLowerCase()) || item.label.toLowerCase().includes(normalized))
    || (presets[simName] || [])[0]
    || { tank: 100, fuel: 3 }
}

function carsFromRaceAssets(config) {
  const result = {}
  Object.keys(presets).forEach((game) => {
    const gameConfig = game === 'ACC' ? config : config?.games?.[game]
    result[game] = (gameConfig?.classes || []).flatMap((assetClass) => {
      const fallback = fallbackPresetForClass(game, assetClass.name)
      return (assetClass.cars || []).map((label) => ({
        label,
        class: assetClass.name,
        tank: fallback.tank,
        fuel: fallback.fuel
      }))
    })
  })
  return result
}

function applyCarPreset() {
  const item = selectedCarPreset.value
  if (!item) return false
  const index = simPresets.value.findIndex((preset) => preset.label === item.class)
  if (index >= 0) presetIndex.value = index
  tank.value = item.tank
  fuelPerLap.value = item.fuel
  return true
}

function applyPreset() {
  const item = selectedPreset.value
  if (!item) return
  tank.value = item.tank
  fuelPerLap.value = item.fuel
}

watch(car, () => {
  applyCarPreset()
})

watch(carSearch, (value) => {
  car.value = value
})

onMounted(async () => {
  try {
    assetFuelCars.value = carsFromRaceAssets(await api('/race-assets'))
  } catch {
    assetFuelCars.value = {}
  }
})
</script>

<template>
  <div class="ui-page ui-shell ui-shell--wide fuel">
    <PageHeader :eyebrow="t('fuelPage.eyebrow')" :title="t('fuelPage.title')" :lead="t('fuelPage.subtitle')" />

    <div class="fuel__layout">
      <form class="fuel__form" novalidate @submit.prevent>
        <!-- 01 · Car -->
        <section v-reveal="{ y: 24 }" class="fuel__card fuel__card--car ui-card" aria-labelledby="fuel-car-title">
          <header class="fuel__card-head">
            <span class="fuel__step ui-num" aria-hidden="true">01</span>
            <div class="fuel__card-title">
              <h2 id="fuel-car-title">{{ t('fuelPage.sections.car') }}</h2>
              <p>{{ t('fuelPage.sections.carText') }}</p>
            </div>
            <CarFront class="fuel__card-icon" :size="20" aria-hidden="true" />
          </header>

          <div class="fuel__group" role="group" :aria-label="t('fuelPage.sim')">
            <span class="fuel__label">{{ t('fuelPage.sim') }}</span>
            <SegmentedControl block :model-value="sim" :options="simOptions" :aria-label="t('fuelPage.sim')" @update:model-value="selectSim" />
          </div>

          <FormField v-slot="{ id, describedBy }" :label="t('fuelPage.car')" :hint="t('fuelPage.hints.car')">
            <CarPicker
              v-model="carSearch"
              :input-id="id"
              :described-by="describedBy"
              :options="filteredCarOptions"
              :selected="car"
              :placeholder="t('fuelPage.carSearch')"
              :empty-text="t('fuelPage.noCars')"
              @select="selectCar"
            />
          </FormField>

          <div class="fuel__row">
            <FormField v-slot="{ id, describedBy }" :label="t('fuelPage.preset')" :hint="t('fuelPage.hints.preset')">
              <select :id="id" v-model="presetIndex" class="ui-select" :aria-describedby="describedBy" @change="applyPreset">
                <option v-for="(item, index) in simPresets" :key="item.label" :value="index">{{ item.label }}</option>
              </select>
            </FormField>
            <div class="fuel__group" role="group" :aria-label="t('fuelPage.unit')">
              <span class="fuel__label">{{ t('fuelPage.unit') }}</span>
              <SegmentedControl v-model="unit" block :options="unitOptions" :aria-label="t('fuelPage.unit')" />
              <p class="fuel__hint">{{ t('fuelPage.hints.unit') }}</p>
            </div>
          </div>
        </section>

        <!-- 02 · Race -->
        <section v-reveal="{ delay: 90, y: 24 }" class="fuel__card ui-card" aria-labelledby="fuel-race-title">
          <header class="fuel__card-head">
            <span class="fuel__step ui-num" aria-hidden="true">02</span>
            <div class="fuel__card-title">
              <h2 id="fuel-race-title">{{ t('fuelPage.sections.race') }}</h2>
              <p>{{ t('fuelPage.sections.raceText') }}</p>
            </div>
            <Flag class="fuel__card-icon" :size="20" aria-hidden="true" />
          </header>

          <SegmentedControl v-model="mode" block :options="modeOptions" :aria-label="t('fuelPage.sections.race')" />

          <Transition name="fuel-swap" mode="out-in">
            <div v-if="mode === 'time'" key="time" class="fuel__row">
              <NumberField v-model="raceHours" :label="t('fuelPage.hours')" :unit="t('fuelPage.units.hours')" min="0" step="1" inputmode="numeric" />
              <NumberField v-model="raceMinutes" :label="t('fuelPage.minutes')" :unit="t('fuelPage.units.minutes')" min="0" step="1" :nudge="5" inputmode="numeric" />
            </div>
            <div v-else key="laps" class="fuel__row">
              <NumberField v-model="raceLaps" :label="t('fuelPage.laps')" :unit="t('fuelPage.units.laps')" min="1" step="1" inputmode="numeric" />
            </div>
          </Transition>

          <div class="fuel__row">
            <NumberField v-model="lapMinutes" :label="t('fuelPage.lapMin')" :unit="t('fuelPage.units.minutes')" min="0" step="1" inputmode="numeric" />
            <NumberField v-model="lapSeconds" :label="t('fuelPage.lapSec')" :unit="t('fuelPage.units.seconds')" min="0" max="59.999" step="0.001" :nudge="0.1" />
          </div>
          <p class="fuel__lap">
            <span class="fuel__lap-label">{{ t('fuelPage.lap') }}</span>
            <strong class="ui-num">{{ lapPreview }}</strong>
            <span class="fuel__lap-hint">{{ t('fuelPage.hints.lapTime') }}</span>
          </p>

          <SwitchToggle v-model="formationLap" :label="t('fuelPage.formation')" :hint="t('fuelPage.hints.formation')" />
        </section>

        <!-- 03 · Fuel -->
        <section v-reveal="{ delay: 180, y: 24 }" class="fuel__card ui-card" aria-labelledby="fuel-burn-title">
          <header class="fuel__card-head">
            <span class="fuel__step ui-num" aria-hidden="true">03</span>
            <div class="fuel__card-title">
              <h2 id="fuel-burn-title">{{ t('fuelPage.sections.fuel') }}</h2>
              <p>{{ t('fuelPage.sections.fuelText') }}</p>
            </div>
            <Droplets class="fuel__card-icon" :size="20" aria-hidden="true" />
          </header>

          <div class="fuel__row">
            <NumberField v-model="fuelPerLap" :label="t('fuelPage.fuelLap')" :hint="t('fuelPage.hints.fuelLap')" :unit="unit" min="0" step="0.01" :nudge="0.05" />
            <NumberField v-model="tank" :label="t('fuelPage.tank')" :hint="t('fuelPage.hints.tank')" :unit="unit" min="0" step="0.1" />
          </div>
          <div class="fuel__row">
            <NumberField v-model="reserveLaps" :label="t('fuelPage.reserve')" :hint="t('fuelPage.hints.reserve')" :unit="t('fuelPage.units.laps')" min="0" step="0.25" :nudge="0.25" />
            <NumberField v-model="currentFuel" :label="t('fuelPage.current')" :hint="t('fuelPage.hints.current')" :unit="unit" min="0" step="0.1" placeholder="—" />
          </div>

          <Transition name="ui-fade" mode="out-in">
            <p v-if="presetHint" :key="presetHint" class="fuel__tip"><Lightbulb :size="17" aria-hidden="true" /><span>{{ presetHint }}</span></p>
          </Transition>
        </section>
      </form>

      <FuelResults
        ref="results"
        v-reveal="{ delay: 140, y: 28 }"
        class="fuel__results"
        :sim="sim"
        :car="car"
        :unit="unit"
        :recommended="recommendedFuel"
        :minimum="minimumFuel"
        :expected="expectedLaps"
        :stops="pitStops"
        :start="startFuel"
        :add="fuelToAdd"
        :full-tank="fullTankLaps"
        :stint="stintLaps"
        :tank="Number(tank) || 0"
        :warning-key="warningKey"
      />
    </div>

    <Transition name="fuel-dock">
      <div v-if="showDock" class="fuel__dock ui-glass ui-glass--strong">
        <span class="fuel__dock-text">
          <span class="fuel__dock-label">{{ t('fuelPage.recommended') }}</span>
          <strong class="fuel__dock-value"><RollingNumber :value="fuelFixed(recommendedFuel)" /> <small>{{ unit }}</small></strong>
        </span>
        <span class="fuel__dock-stops ui-num">{{ t('fuelPage.stops') }}: {{ pitStops }}</span>
        <button class="ui-btn ui-btn--primary ui-btn--sm" type="button" @click="scrollToResults"><ArrowDown :size="15" aria-hidden="true" />{{ t('fuelPage.dock') }}</button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.fuel__layout {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(400px, 0.95fr);
  align-items: start;
  gap: clamp(16px, 2vw, 24px);
}

.fuel__form {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-items: start;
  gap: clamp(14px, 1.6vw, 20px);
}

/* ---------- Input cards ---------- */
.fuel__card {
  gap: 18px;
}

/* The car list opens over the cards below it. */
.fuel__card--car {
  z-index: 3;
}

.fuel__card-head {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: start;
  gap: 14px;
}

.fuel__step {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border: 1px solid var(--c-blue-line);
  border-radius: var(--r-sm);
  background: var(--c-blue-soft);
  color: var(--c-accent-text);
  font-size: 13px;
  font-weight: 700;
}

.fuel__card-title {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.fuel__card-title h2 {
  margin: 0;
  color: var(--c-text);
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  line-height: 1.2;
  text-transform: uppercase;
}

.fuel__card-title p {
  margin: 0;
  color: var(--c-text-3);
  font-size: 13px;
  line-height: 1.45;
}

.fuel__card-icon {
  margin-top: 2px;
  color: var(--c-text-3);
}

.fuel__row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  align-items: start;
  gap: 16px;
}

.fuel__group {
  display: grid;
  align-content: start;
  gap: 8px;
  min-width: 0;
}

.fuel__label {
  color: var(--c-text);
  font-size: 13.5px;
  font-weight: 600;
}

.fuel__hint {
  margin: 0;
  color: var(--c-text-3);
  font-size: 12.5px;
  line-height: 1.45;
}

.fuel__group :deep(.segmented) {
  min-height: 48px;
}

.fuel__group :deep(.segmented__option) {
  min-height: 38px;
}

.fuel__lap {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 12px;
  margin: -4px 0 0;
  padding: 10px 14px;
  border: 1px dashed var(--c-line-strong);
  border-radius: var(--r-md);
}

.fuel__lap-label {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.fuel__lap strong {
  color: var(--bm-cyan);
  font-size: 18px;
  font-weight: 700;
  text-shadow: 0 0 18px color-mix(in srgb, var(--bm-cyan) 40%, transparent);
}

:root[data-theme='light'] .fuel__lap strong {
  color: var(--bm-blue);
  text-shadow: none;
}

.fuel__lap-hint {
  flex: 1 1 220px;
  color: var(--c-text-3);
  font-size: 12.5px;
}

.fuel__tip {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin: 0;
  padding: 12px 14px;
  border: 1px solid color-mix(in srgb, var(--bm-amber) 30%, transparent);
  border-radius: var(--r-md);
  background: color-mix(in srgb, var(--bm-amber) 8%, transparent);
  color: var(--c-text-2);
  font-size: 13.5px;
  line-height: 1.45;
}

.fuel__tip svg {
  flex: 0 0 auto;
  margin-top: 1px;
  color: var(--bm-amber);
}

/* Field swap between timed and fixed-lap races. */
.fuel-swap-enter-active,
.fuel-swap-leave-active {
  transition: opacity var(--dur-2) var(--ease-out), transform var(--dur-3) var(--ease-ios), filter var(--dur-2);
}

.fuel-swap-enter-from {
  opacity: 0;
  filter: blur(4px);
  transform: translateY(8px);
}

.fuel-swap-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

/* ---------- Mobile dock with the main number ---------- */
.fuel__dock {
  position: fixed;
  right: max(12px, var(--gutter));
  bottom: calc(var(--tabbar-h) + 12px + env(safe-area-inset-bottom, 0px));
  left: max(12px, var(--gutter));
  z-index: 60;
  display: flex;
  align-items: center;
  gap: 12px;
  max-width: 560px;
  margin: 0 auto;
  padding: 10px 10px 10px 18px;
  border-radius: var(--r-pill);
  box-shadow: var(--shadow-2);
}

.fuel__dock-text {
  display: grid;
  flex: 1 1 auto;
  gap: 2px;
  min-width: 0;
}

.fuel__dock-label {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 9.5px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.fuel__dock-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
  color: var(--c-text);
  font-size: 22px;
  font-weight: 700;
  line-height: 1;
}

.fuel__dock-value small {
  color: var(--c-accent-text);
  font-family: var(--font-mono);
  font-size: 12px;
}

.fuel__dock-stops {
  color: var(--c-text-2);
  font-size: 12px;
  white-space: nowrap;
}

.fuel-dock-enter-active,
.fuel-dock-leave-active {
  transition: opacity var(--dur-2) var(--ease-out), transform var(--dur-3) var(--ease-ios);
}

.fuel-dock-enter-from,
.fuel-dock-leave-to {
  opacity: 0;
  transform: translateY(24px) scale(0.96);
}

/* ---------- Responsive ---------- */
@media (min-width: 1500px) {
  .fuel__form {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .fuel__card--car {
    grid-column: 1 / -1;
  }
}

@media (min-width: 1181px) and (min-height: 980px) {
  .fuel__results {
    position: sticky;
    top: calc(var(--header-h) + 16px);
  }
}

@media (max-width: 1180px) {
  .fuel__layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .fuel {
    padding-bottom: calc(96px + var(--tabbar-h));
  }
}

@media (min-width: 761px) and (max-width: 1180px) {
  .fuel__form {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .fuel__card--car {
    grid-column: 1 / -1;
  }
}

@media (max-width: 560px) {
  .fuel__dock-stops {
    display: none;
  }

  .fuel__row {
    grid-template-columns: minmax(0, 1fr);
    gap: 14px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .fuel-swap-enter-active,
  .fuel-swap-leave-active,
  .fuel-dock-enter-active,
  .fuel-dock-leave-active {
    transition: none;
  }
}
</style>
