<script setup>
import { computed, ref } from 'vue'
import { Calculator, Fuel, Gauge, TimerReset } from 'lucide-vue-next'
import { state } from '../store'

const presets = {
  ACC: [
    { label: 'GT3', tank: 110, fuel: 3.2, hintRu: 'Проверь расход в MFD после серии боевых кругов.', hintEn: 'Check consumption in the MFD after a race-pace run.' },
    { label: 'GT4', tank: 80, fuel: 2.6, hintRu: 'Для GT4 расход обычно ниже, но трасса сильно влияет.', hintEn: 'GT4 usually burns less fuel, but track layout matters.' },
    { label: 'Cup', tank: 100, fuel: 3.0, hintRu: 'Для Cup лучше брать запас не меньше одного круга.', hintEn: 'For Cup races, keep at least one lap of reserve.' }
  ],
  AC: [
    { label: 'GT', tank: 100, fuel: 3.1, hintRu: 'Для AC и модов проверь бак в настройках машины.', hintEn: 'For AC and mods, verify tank capacity in the car setup.' },
    { label: 'Touring', tank: 70, fuel: 2.4, hintRu: 'Для туринговых машин чаще хватает меньшего бака.', hintEn: 'Touring cars often need a smaller tank.' }
  ],
  iRacing: [
    { label: 'GT3', tank: 110, fuel: 3.1, hintRu: 'Бак и расход смотри в Garage -> Fuel.', hintEn: 'Check tank and consumption in Garage -> Fuel.' },
    { label: 'Prototype', tank: 75, fuel: 4.4, hintRu: 'Для прототипов расход выше, проверь race control calculator.', hintEn: 'Prototypes burn more fuel; cross-check race control calculator.' }
  ],
  LMU: [
    { label: 'Hypercar', tank: 70, fuel: 4.6, hintRu: 'Здесь считается обычное топливо, не Virtual Energy.', hintEn: 'This calculates fuel, not Virtual Energy.' },
    { label: 'LMGT3', tank: 100, fuel: 3.4, hintRu: 'Для LMGT3 бери расход с боевого темпа.', hintEn: 'For LMGT3, use race-pace consumption.' }
  ]
}

const cars = {
  ACC: ['Ferrari 296 GT3', 'BMW M4 GT3', 'Porsche 992 GT3R', 'McLaren 720S Evo GT3', 'Mercedes-AMG GT3 Evo'],
  AC: ['GT3 car', 'GT2 car', 'Touring car'],
  iRacing: ['Ferrari 296 GT3', 'BMW M4 GT3', 'Porsche 963 GTP', 'Dallara P217'],
  LMU: ['Hypercar', 'LMGT3']
}

const sim = ref('ACC')
const car = ref('Ferrari 296 GT3')
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

const copy = computed(() => state.locale === 'en' ? {
  title: 'Fuel calculator',
  subtitle: 'Works locally in the browser. No API requests.',
  sim: 'Simulator',
  car: 'Car',
  preset: 'Class / preset',
  unit: 'Units',
  timeRace: 'Timed race',
  lapRace: 'Fixed laps',
  hours: 'Duration, hours',
  minutes: 'Duration, minutes',
  laps: 'Race laps',
  lapMin: 'Average lap, minutes',
  lapSec: 'Average lap, seconds',
  fuelLap: 'Fuel per lap',
  tank: 'Tank capacity',
  reserve: 'Reserve, laps',
  current: 'Fuel now',
  formation: 'Add formation lap',
  result: 'Result',
  recommended: 'Recommended',
  expected: 'Race laps',
  minimum: 'Minimum',
  stops: 'Pit stops',
  start: 'Start fuel',
  add: 'Add',
  ready: 'Calculation ready. Use race pace, not your best qualifying lap.',
  fill: 'Fill average lap and fuel per lap.',
  stopNeeded: 'Fuel does not fit in one tank; plan a pit stop.',
  formula: 'Formula: fuel = laps x fuel per lap + reserve.',
  check: 'Check consumption after 3-5 race-pace laps in the selected car.',
  fullTank: 'Full tank',
  stint: 'Stint'
} : {
  title: 'Калькулятор топлива',
  subtitle: 'Работает локально в браузере. API-запросов нет.',
  sim: 'Симулятор',
  car: 'Машина',
  preset: 'Класс / пресет',
  unit: 'Единицы',
  timeRace: 'Гонка по времени',
  lapRace: 'Гонка по кругам',
  hours: 'Длительность, часы',
  minutes: 'Длительность, минуты',
  laps: 'Кругов в гонке',
  lapMin: 'Средний круг, минуты',
  lapSec: 'Средний круг, секунды',
  fuelLap: 'Расход за круг',
  tank: 'Объем бака',
  reserve: 'Запас, круги',
  current: 'Топливо сейчас',
  formation: 'Добавить прогревочный круг',
  result: 'Результат',
  recommended: 'Рекомендовано',
  expected: 'Гоночные круги',
  minimum: 'Минимум',
  stops: 'Пит-стопы',
  start: 'Стартовая заправка',
  add: 'Долить',
  ready: 'Расчет готов. Используй боевой темп, а не лучший квалификационный круг.',
  fill: 'Заполни средний круг и расход.',
  stopNeeded: 'На старт весь объем не помещается: нужен пит-стоп.',
  formula: 'Формула: топливо = круги x расход за круг + запас.',
  check: 'Проверь расход после 3-5 боевых кругов в выбранной машине.',
  fullTank: 'Полный бак',
  stint: 'Стинт'
})

const simPresets = computed(() => presets[sim.value] || [])
const carOptions = computed(() => cars[sim.value] || [])
const selectedPreset = computed(() => simPresets.value[Number(presetIndex.value)] || simPresets.value[0])
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
const warning = computed(() => {
  if (!lapSecondsTotal.value || !Number(fuelPerLap.value)) return copy.value.fill
  if (Number(tank.value) > 0 && recommendedFuel.value > Number(tank.value)) return copy.value.stopNeeded
  return copy.value.ready
})

function formatFuel(value) {
  if (!Number.isFinite(value)) return `0 ${unit.value}`
  const fixed = value >= 100 ? value.toFixed(0) : value.toFixed(1)
  return `${fixed} ${unit.value}`
}

function handleSimChange() {
  presetIndex.value = 0
  car.value = carOptions.value[0] || ''
  applyPreset()
}

function applyPreset() {
  const item = selectedPreset.value
  if (!item) return
  tank.value = item.tank
  fuelPerLap.value = item.fuel
}
</script>

<template>
  <section class="section fuel-page">
    <div class="section-header">
      <div>
        <h1>{{ copy.title }}</h1>
        <p class="muted">{{ copy.subtitle }}</p>
      </div>
    </div>

    <div class="fuel-layout">
      <form class="card form fuel-form" @submit.prevent>
        <div class="form-row">
          <label class="field">
            <span>{{ copy.sim }}</span>
            <select v-model="sim" @change="handleSimChange">
              <option v-for="name in Object.keys(presets)" :key="name" :value="name">{{ name }}</option>
            </select>
          </label>
          <label class="field">
            <span>{{ copy.car }}</span>
            <input v-model="car" list="fuel-car-options" maxlength="80" />
            <datalist id="fuel-car-options">
              <option v-for="name in carOptions" :key="name" :value="name" />
            </datalist>
          </label>
        </div>

        <div class="form-row">
          <label class="field">
            <span>{{ copy.preset }}</span>
            <select v-model="presetIndex" @change="applyPreset">
              <option v-for="(item, index) in simPresets" :key="item.label" :value="index">{{ item.label }}</option>
            </select>
          </label>
          <label class="field">
            <span>{{ copy.unit }}</span>
            <select v-model="unit">
              <option value="L">L</option>
              <option value="gal">gal</option>
            </select>
          </label>
        </div>

        <div class="fuel-mode-switch">
          <label class="toggle-field"><input v-model="mode" type="radio" value="time" />{{ copy.timeRace }}</label>
          <label class="toggle-field"><input v-model="mode" type="radio" value="laps" />{{ copy.lapRace }}</label>
        </div>

        <div v-if="mode === 'time'" class="form-row">
          <label class="field"><span>{{ copy.hours }}</span><input v-model.number="raceHours" type="number" min="0" step="1" /></label>
          <label class="field"><span>{{ copy.minutes }}</span><input v-model.number="raceMinutes" type="number" min="0" step="1" /></label>
        </div>
        <div v-else class="form-row">
          <label class="field"><span>{{ copy.laps }}</span><input v-model.number="raceLaps" type="number" min="1" step="1" /></label>
        </div>

        <div class="form-row">
          <label class="field"><span>{{ copy.lapMin }}</span><input v-model.number="lapMinutes" type="number" min="0" step="1" /></label>
          <label class="field"><span>{{ copy.lapSec }}</span><input v-model.number="lapSeconds" type="number" min="0" max="59.999" step="0.001" /></label>
        </div>

        <div class="form-row">
          <label class="field"><span>{{ copy.fuelLap }}</span><input v-model.number="fuelPerLap" type="number" min="0" step="0.01" /></label>
          <label class="field"><span>{{ copy.tank }}</span><input v-model.number="tank" type="number" min="0" step="0.1" /></label>
        </div>

        <div class="form-row">
          <label class="field"><span>{{ copy.reserve }}</span><input v-model.number="reserveLaps" type="number" min="0" step="0.25" /></label>
          <label class="field"><span>{{ copy.current }}</span><input v-model="currentFuel" type="number" min="0" step="0.1" /></label>
        </div>

        <label class="toggle-field fuel-wide-toggle"><input v-model="formationLap" type="checkbox" />{{ copy.formation }}</label>
        <p class="fuel-note">{{ presetHint }}</p>
      </form>

      <aside class="card fuel-results">
        <div class="fuel-results-head">
          <h2>{{ copy.result }}</h2>
          <span>{{ sim }}<template v-if="car"> / {{ car }}</template></span>
        </div>

        <div class="fuel-metric is-primary">
          <Fuel :size="22" />
          <span>{{ copy.recommended }}</span>
          <strong>{{ formatFuel(recommendedFuel) }}</strong>
        </div>

        <div class="fuel-metrics-grid">
          <div class="fuel-metric">
            <TimerReset :size="20" />
            <span>{{ copy.expected }}</span>
            <strong>{{ expectedLaps }}</strong>
          </div>
          <div class="fuel-metric">
            <Calculator :size="20" />
            <span>{{ copy.minimum }}</span>
            <strong>{{ formatFuel(minimumFuel) }}</strong>
          </div>
          <div class="fuel-metric">
            <Gauge :size="20" />
            <span>{{ copy.stops }}</span>
            <strong>{{ pitStops }}</strong>
          </div>
          <div class="fuel-metric">
            <Fuel :size="20" />
            <span>{{ copy.start }}</span>
            <strong>{{ formatFuel(startFuel) }}</strong>
          </div>
        </div>

        <div class="fuel-summary">
          <p>{{ warning }}</p>
          <p>{{ copy.formula }}</p>
          <p>{{ copy.check }}</p>
          <p>{{ copy.add }}: <strong>{{ fuelToAdd === null ? '-' : formatFuel(fuelToAdd) }}</strong></p>
          <p>{{ copy.fullTank }}: <strong>{{ fullTankLaps }}</strong>. {{ copy.stint }}: <strong>{{ stintLaps }}</strong>.</p>
        </div>
      </aside>
    </div>
  </section>
</template>
