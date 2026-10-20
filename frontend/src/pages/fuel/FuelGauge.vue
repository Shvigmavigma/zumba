<script setup>
// Analogue fuel gauge (E … F): the arc fills and the needle swings with a
// spring to the share of the tank used at the start. Amber when the race
// needs more than one tank.
import { computed, onBeforeUnmount, onMounted, ref, useId } from 'vue'
import { onceInView } from '../../ui/motion/env'

const props = defineProps({
  /** Share of the tank, 0..1. */
  fill: { type: Number, default: 0 },
  /** The race needs more fuel than the tank holds. */
  over: { type: Boolean, default: false },
  label: { type: String, default: '' },
  value: { type: String, default: '' },
  caption: { type: String, default: '' }
})

const CX = 100
const CY = 100
const R = 80
const START = 150
const SWEEP = 240
const ARC = `M ${point(START, R).join(' ')} A ${R} ${R} 0 1 1 ${point(START + SWEEP, R).join(' ')}`
const TICKS = Array.from({ length: 9 }, (_, index) => {
  const angle = START + (SWEEP * index) / 8
  const major = index % 4 === 0
  const [x1, y1] = point(angle, major ? 58 : 62)
  const [x2, y2] = point(angle, 67)
  return { x1, y1, x2, y2, major }
})
const LABELS = [
  { text: 'E', at: point(START, 48) },
  { text: '½', at: point(START + SWEEP / 2, 47) },
  { text: 'F', at: point(START + SWEEP, 48) }
]

const gradientId = `fuel-gauge-${useId()}`
const root = ref(null)
const shown = ref(false)
let stop = null

const level = computed(() => (shown.value ? Math.max(0, Math.min(1, Number(props.fill) || 0)) : 0))
const needle = computed(() => START + SWEEP * level.value)

function point(angle, radius) {
  const rad = (angle * Math.PI) / 180
  return [Number((CX + radius * Math.cos(rad)).toFixed(2)), Number((CY + radius * Math.sin(rad)).toFixed(2))]
}

onMounted(() => {
  stop = onceInView(root.value, () => {
    shown.value = true
  })
})
onBeforeUnmount(() => stop?.())
</script>

<template>
  <figure ref="root" class="gauge" :class="{ 'is-over': over }">
    <svg class="gauge__svg" viewBox="0 0 200 160" role="img" :aria-label="label">
      <defs>
        <linearGradient :id="gradientId" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" class="gauge__stop-a" />
          <stop offset="100%" class="gauge__stop-b" />
        </linearGradient>
      </defs>
      <path class="gauge__track" :d="ARC" pathLength="100" />
      <path class="gauge__value" :d="ARC" pathLength="100" :stroke="`url(#${gradientId})`" stroke-dasharray="100 100" :stroke-dashoffset="100 - level * 100" :opacity="level > 0.002 ? 1 : 0" />
      <line v-for="(tick, index) in TICKS" :key="index" class="gauge__tick" :class="{ 'is-major': tick.major }" :x1="tick.x1" :y1="tick.y1" :x2="tick.x2" :y2="tick.y2" />
      <text v-for="item in LABELS" :key="item.text" class="gauge__mark" :x="item.at[0]" :y="item.at[1]" text-anchor="middle" dominant-baseline="middle">{{ item.text }}</text>
      <g class="gauge__needle" :style="{ transform: `rotate(${needle}deg)` }">
        <line :x1="CX - 10" :y1="CY" :x2="CX + 60" :y2="CY" />
      </g>
      <circle class="gauge__hub" :cx="CX" :cy="CY" r="6.5" />
      <text class="gauge__value-text" :x="CX" y="134" text-anchor="middle">{{ value }}</text>
    </svg>
    <figcaption v-if="caption" class="gauge__caption">{{ caption }}</figcaption>
  </figure>
</template>

<style scoped>
.gauge {
  display: grid;
  justify-items: center;
  gap: 2px;
  margin: 0;
}

.gauge__svg {
  width: 100%;
  max-width: 230px;
  height: auto;
  overflow: visible;
}

.gauge__track,
.gauge__value {
  fill: none;
  stroke-linecap: round;
  stroke-width: 12;
}

.gauge__track {
  stroke: color-mix(in srgb, var(--c-text) 9%, transparent);
}

.gauge__value {
  filter: drop-shadow(0 0 6px color-mix(in srgb, var(--bm-cyan) 55%, transparent));
  transition: stroke-dashoffset 1.3s var(--ease-out);
}

.gauge__stop-a {
  stop-color: var(--bm-blue);
}

.gauge__stop-b {
  stop-color: var(--bm-cyan);
}

.is-over .gauge__stop-a {
  stop-color: var(--bm-amber);
}

.is-over .gauge__stop-b {
  stop-color: var(--bm-red);
}

.is-over .gauge__value {
  filter: drop-shadow(0 0 7px color-mix(in srgb, var(--bm-amber) 60%, transparent));
}

.gauge__tick {
  stroke: var(--c-text-3);
  stroke-linecap: round;
  stroke-width: 1.2;
}

.gauge__tick.is-major {
  stroke: var(--c-text-2);
  stroke-width: 2;
}

.gauge__mark {
  fill: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
}

.gauge__needle {
  transform-box: view-box;
  transform-origin: 100px 100px;
  transition: transform 1.4s var(--ease-spring);
}

.gauge__needle line {
  stroke: var(--bm-red);
  stroke-linecap: round;
  stroke-width: 3;
  filter: drop-shadow(0 0 4px color-mix(in srgb, var(--bm-red) 60%, transparent));
}

.gauge__hub {
  fill: var(--c-surface-solid);
  stroke: var(--c-text-2);
  stroke-width: 2;
}

.gauge__value-text {
  fill: var(--c-text);
  font-family: var(--font-mono);
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.gauge__caption {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-align: center;
  text-transform: uppercase;
}

@media (prefers-reduced-motion: reduce) {
  .gauge__value,
  .gauge__needle {
    transition: none;
  }
}
</style>
