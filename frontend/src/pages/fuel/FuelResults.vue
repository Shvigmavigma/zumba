<script setup>
// Result panel of the fuel calculator, laid out like a telemetry screen:
// fuel gauge and the recommended amount, a status line, the readouts with a
// one-line explanation each and the stint plan. Display only: every number
// comes from the page.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { AlertTriangle, Calculator, CarFront, CheckCircle2, Droplet, Fuel, Gauge, Info, TimerReset, Wrench } from 'lucide-vue-next'
import RollingNumber from '../../ui/fx/RollingNumber.vue'
import FuelGauge from './FuelGauge.vue'
import { fuelFixed } from './fuelFormat'

const props = defineProps({
  sim: { type: String, default: '' },
  car: { type: String, default: '' },
  unit: { type: String, default: 'L' },
  recommended: { type: Number, default: 0 },
  minimum: { type: Number, default: 0 },
  expected: { type: Number, default: 0 },
  stops: { type: Number, default: 0 },
  start: { type: Number, default: 0 },
  /** null while "fuel now" is empty. */
  add: { type: Number, default: null },
  fullTank: { type: Number, default: 0 },
  stint: { type: Number, default: 0 },
  tank: { type: Number, default: 0 },
  /** 'fill' | 'stopNeeded' | 'ready' */
  warningKey: { type: String, default: 'ready' }
})

const { t } = useI18n()
const MAX_STINTS = 8

const STATUS = {
  ready: { icon: CheckCircle2, className: 'ui-alert--success' },
  fill: { icon: Info, className: 'ui-alert--info' },
  stopNeeded: { icon: AlertTriangle, className: 'is-amber' }
}

const status = computed(() => STATUS[props.warningKey] || STATUS.ready)
const gaugeFill = computed(() => (props.tank > 0 ? props.start / props.tank : 0))
const percent = computed(() => Math.round(Math.max(0, Math.min(1, gaugeFill.value)) * 100))
const stintCount = computed(() => props.stops + 1)
const shownStints = computed(() => Math.min(stintCount.value, MAX_STINTS))
const lapsUnit = computed(() => t('fuelPage.units.laps'))

const tiles = computed(() => [
  { key: 'expected', icon: TimerReset, label: t('fuelPage.expected'), value: String(props.expected), unit: lapsUnit.value, explain: t('fuelPage.explain.expected') },
  { key: 'stops', icon: Wrench, label: t('fuelPage.stops'), value: String(props.stops), unit: '', explain: t('fuelPage.explain.stops'), warn: props.stops > 0 },
  { key: 'minimum', icon: Calculator, label: t('fuelPage.minimum'), value: fuelFixed(props.minimum), unit: props.unit, explain: t('fuelPage.explain.minimum') },
  { key: 'start', icon: Fuel, label: t('fuelPage.start'), value: fuelFixed(props.start), unit: props.unit, explain: t('fuelPage.explain.start') },
  {
    key: 'add',
    icon: Droplet,
    label: t('fuelPage.add'),
    value: props.add === null ? '—' : fuelFixed(props.add),
    unit: props.add === null ? '' : props.unit,
    explain: props.add === null ? t('fuelPage.explain.addEmpty') : t('fuelPage.explain.add'),
    muted: props.add === null
  },
  { key: 'fullTank', icon: Gauge, label: t('fuelPage.fullTank'), value: String(props.fullTank), unit: lapsUnit.value, explain: t('fuelPage.explain.fullTank') }
])
</script>

<template>
  <aside class="out ui-card" aria-labelledby="fuel-result-title">
    <header class="out__head">
      <div class="out__heading">
        <p class="ui-eyebrow ui-eyebrow--accent"><span class="ui-dot ui-dot--blue ui-dot--live" aria-hidden="true"></span>{{ t('fuelPage.telemetry') }}</p>
        <h2 id="fuel-result-title" class="ui-title out__title">{{ t('fuelPage.result') }}</h2>
      </div>
      <span class="ui-chip ui-chip--blue">{{ sim }}</span>
    </header>
    <p v-if="car" class="out__car"><CarFront :size="16" aria-hidden="true" /><span>{{ car }}</span></p>

    <div class="out__hero">
      <FuelGauge
        class="out__gauge"
        :fill="gaugeFill"
        :over="warningKey === 'stopNeeded'"
        :label="t('fuelPage.gauge.aria', { percent })"
        :value="tank > 0 ? `${percent}%` : '—'"
        :caption="tank > 0 ? t('fuelPage.gauge.label') : t('fuelPage.gauge.noTank')"
      />
      <div class="out__main">
        <span class="out__label">{{ t('fuelPage.recommended') }}</span>
        <strong class="out__big"><RollingNumber :value="fuelFixed(recommended)" /><small>{{ unit }}</small></strong>
        <p class="out__explain">{{ t('fuelPage.explain.recommended') }}</p>
      </div>
    </div>

    <Transition name="ui-fade" mode="out-in">
      <p :key="warningKey" class="ui-alert out__status" :class="status.className" aria-live="polite">
        <component :is="status.icon" :size="18" aria-hidden="true" />{{ t(`fuelPage.${warningKey}`) }}
      </p>
    </Transition>

    <dl class="out__grid">
      <div v-for="(tile, index) in tiles" :key="tile.key" v-reveal="{ delay: 80 + index * 60, y: 10, blur: 4 }" class="out__tile" :class="{ 'is-muted': tile.muted, 'is-warn': tile.warn }">
        <dt><component :is="tile.icon" :size="15" aria-hidden="true" />{{ tile.label }}</dt>
        <dd><RollingNumber :value="tile.value" /><small v-if="tile.unit">{{ tile.unit }}</small></dd>
        <p>{{ tile.explain }}</p>
      </div>
    </dl>

    <section class="out__plan" :aria-label="t('fuelPage.plan.title')">
      <header class="out__plan-head">
        <span class="out__label">{{ t('fuelPage.plan.title') }}</span>
        <span class="ui-num">{{ t('fuelPage.plan.summary', { stints: stintCount, laps: stint }) }}</span>
      </header>
      <div class="out__track">
        <span v-for="n in shownStints" :key="n" class="out__stint" :style="{ '--i': n }" :title="`${t('fuelPage.stint')} ${n}`">
          <i v-if="n > 1" class="out__pit" :title="t('fuelPage.plan.pit')" aria-hidden="true"></i>
          <b class="ui-num">{{ n }}</b>
        </span>
      </div>
      <p v-if="stintCount > MAX_STINTS" class="out__more ui-num">{{ t('fuelPage.plan.many', { count: stintCount - MAX_STINTS }) }}</p>
      <p class="out__explain">{{ t('fuelPage.stint') }}: <strong class="ui-num">{{ stint }}</strong> {{ lapsUnit }} — {{ t('fuelPage.explain.stint') }}</p>
    </section>

    <footer class="out__notes">
      <p>{{ t('fuelPage.formula') }}</p>
      <p>{{ t('fuelPage.check') }}</p>
    </footer>
  </aside>
</template>

<style scoped>
.out {
  container-type: inline-size;
  gap: 18px;
  overflow: hidden;
}

/* Faint telemetry grid behind the panel. */
.out::before {
  position: absolute;
  inset: 0;
  z-index: -1;
  background:
    linear-gradient(var(--c-line) 1px, transparent 1px) 0 0 / 100% 28px,
    radial-gradient(80% 60% at 100% 0%, color-mix(in srgb, var(--bm-blue) 22%, transparent), transparent 70%);
  content: '';
  opacity: 0.6;
  -webkit-mask-image: linear-gradient(180deg, #000, transparent 55%);
  mask-image: linear-gradient(180deg, #000, transparent 55%);
  pointer-events: none;
}

.out__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.out__heading {
  display: grid;
  gap: 8px;
}

.out__title {
  font-size: 20px;
}

.out__car {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: -6px 0 0;
  color: var(--c-text-2);
  font-size: 14px;
  font-weight: 550;
}

.out__car svg {
  flex: 0 0 auto;
  color: var(--c-accent-text);
}

.out__car span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ---------- Hero: gauge + recommended ---------- */
.out__hero {
  display: grid;
  grid-template-columns: minmax(0, 210px) minmax(0, 1fr);
  align-items: center;
  gap: 18px;
  padding: 16px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-lg);
  background: var(--c-sunken);
}

.out__main {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.out__label {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.out__big {
  display: flex;
  align-items: baseline;
  gap: 8px;
  color: var(--c-text);
  font-size: clamp(44px, 9cqi, 72px);
  font-weight: 700;
  line-height: 1;
  text-shadow: 0 0 34px color-mix(in srgb, var(--bm-blue) 55%, transparent);
}

.out__big small {
  color: var(--c-accent-text);
  font-family: var(--font-mono);
  font-size: 0.32em;
  font-weight: 700;
  text-shadow: none;
}

.out__explain {
  margin: 0;
  color: var(--c-text-3);
  font-size: 12.5px;
  line-height: 1.45;
}

.out__explain strong {
  color: var(--c-text);
}

.out__status {
  align-items: center;
}

.out__status.is-amber {
  border-color: color-mix(in srgb, var(--bm-amber) 40%, transparent);
  background: color-mix(in srgb, var(--bm-amber) 12%, transparent);
  color: color-mix(in srgb, var(--bm-amber) 70%, var(--c-text));
}

.out__status.ui-alert--success svg {
  color: var(--bm-green);
}

.out__status.ui-alert--info svg {
  color: var(--c-accent-text);
}

/* ---------- Readouts ---------- */
.out__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 8px;
  margin: 0;
}

.out__tile {
  display: grid;
  align-content: start;
  gap: 6px;
  padding: 12px 14px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  background: var(--c-surface-2);
  transition: border-color var(--dur-2), transform var(--dur-3) var(--ease-ios);
}

.out__tile:hover {
  border-color: var(--c-blue-line);
  transform: translateY(-2px);
}

.out__tile dt {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--c-text-2);
  font-size: 12.5px;
  font-weight: 600;
}

.out__tile dt svg {
  flex: 0 0 auto;
  color: var(--c-accent-text);
}

.out__tile dd {
  display: flex;
  align-items: baseline;
  gap: 5px;
  margin: 0;
  color: var(--c-text);
  font-size: 26px;
  font-weight: 700;
  line-height: 1;
}

.out__tile dd small {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
}

.out__tile p {
  margin: 0;
  color: var(--c-text-3);
  font-size: 12px;
  line-height: 1.4;
}

.out__tile.is-warn {
  border-color: color-mix(in srgb, var(--bm-amber) 40%, transparent);
}

.out__tile.is-warn dt svg,
.out__tile.is-warn dd {
  color: color-mix(in srgb, var(--bm-amber) 80%, var(--c-text));
}

.out__tile.is-muted dd {
  color: var(--c-text-3);
}

/* ---------- Stint plan ---------- */
.out__plan {
  display: grid;
  gap: 10px;
  padding: 14px 16px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-lg);
  background: var(--c-sunken);
}

.out__plan-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  color: var(--c-text);
  font-size: 13px;
  font-weight: 600;
}

.out__track {
  display: flex;
  gap: 14px;
}

.out__stint {
  position: relative;
  display: grid;
  flex: 1 1 0;
  place-items: center;
  min-width: 0;
  height: 30px;
  border-radius: 9px;
  background: linear-gradient(90deg, var(--bm-blue), color-mix(in srgb, var(--bm-blue) 55%, var(--bm-cyan)));
  box-shadow: 0 6px 18px -6px color-mix(in srgb, var(--bm-blue) 70%, transparent), inset 0 1px 0 rgba(255, 255, 255, 0.2);
  color: #fff;
  font-size: 12px;
  transform-origin: left center;
  animation: out-stint 640ms var(--ease-ios) both;
  animation-delay: calc(var(--i) * 70ms);
}

/* Pit stop marker between two stints. */
.out__pit {
  position: absolute;
  top: -5px;
  bottom: -5px;
  left: -10px;
  width: 6px;
  border-radius: 3px;
  background: var(--bm-amber);
  box-shadow: 0 0 10px color-mix(in srgb, var(--bm-amber) 60%, transparent);
}

.out__more {
  margin: -4px 0 0;
  color: var(--c-text-3);
  font-size: 12px;
}

/* ---------- Notes ---------- */
.out__notes {
  display: grid;
  gap: 4px;
  padding-top: 14px;
  border-top: 1px dashed var(--c-line-strong);
}

.out__notes p {
  margin: 0;
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 11.5px;
  line-height: 1.5;
}

@keyframes out-stint {
  from {
    opacity: 0;
    transform: scaleX(0.3);
  }
  to {
    opacity: 1;
    transform: scaleX(1);
  }
}

@container (max-width: 460px) {
  .out__hero {
    grid-template-columns: minmax(0, 1fr);
    justify-items: center;
    text-align: center;
  }

  .out__gauge {
    width: min(100%, 220px);
  }

  .out__main {
    justify-items: center;
  }

  .out__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .out__tile dd {
    font-size: 22px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .out__stint {
    animation: none;
  }
}
</style>
