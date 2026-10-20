<script setup>
// Backdrop of the track records header: a blueprint grid and the track's own
// speed trace with its three sectors (trackTelemetry.js). The page keys it by
// track, so on every switch the trace is drawn again, a glint runs along it
// and a band of light crosses the header once; after that it stands still.
import { computed, useId } from 'vue'
import { speedTrace } from './trackTelemetry'

const WIDTH = 1000
const HEIGHT = 200

const props = defineProps({
  /** Track name: the trace is made from it. */
  track: { type: String, default: '' }
})

const fillId = useId()
const trace = computed(() => speedTrace(props.track, { width: WIDTH, height: HEIGHT }))
/** Where each sector starts, as a share of the chart's width. */
const sectorStarts = computed(() => [0, ...trace.value.sectors].map((x) => `${(x / WIDTH) * 100}%`))
</script>

<template>
  <div class="backdrop" aria-hidden="true">
    <span class="backdrop__grid"></span>
    <div class="backdrop__chart">
      <svg class="backdrop__svg" :viewBox="`0 0 ${WIDTH} ${HEIGHT}`" preserveAspectRatio="none">
        <defs>
          <linearGradient :id="fillId" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="var(--bm-blue-bright)" stop-opacity="0.2" />
            <stop offset="1" stop-color="var(--bm-blue-bright)" stop-opacity="0" />
          </linearGradient>
        </defs>
        <line v-for="x in trace.sectors" :key="x" class="backdrop__sector" :x1="x" y1="0" :x2="x" :y2="HEIGHT" />
        <path class="backdrop__area" :d="trace.area" :fill="`url(#${fillId})`" />
        <path class="backdrop__line" :d="trace.line" pathLength="1" />
        <path class="backdrop__glint" :d="trace.line" pathLength="1" />
      </svg>
      <span v-for="(left, index) in sectorStarts" :key="left" class="backdrop__mark" :style="{ left }">S{{ index + 1 }}</span>
    </div>
    <span class="backdrop__sweep"></span>
  </div>
</template>

<style scoped>
.backdrop {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

/* Blueprint grid, strongest where nothing else is and gone under the text. */
.backdrop__grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(to right, color-mix(in srgb, var(--c-text) 7%, transparent) 1px, transparent 1px),
    linear-gradient(to bottom, color-mix(in srgb, var(--c-text) 7%, transparent) 1px, transparent 1px);
  background-size: 44px 44px;
  -webkit-mask-image: linear-gradient(to bottom, #000 0%, #000 42%, transparent 78%);
  mask-image: linear-gradient(to bottom, #000 0%, #000 42%, transparent 78%);
}

/* The chart lives in the free space: above the text, left of the track. */
.backdrop__chart {
  position: absolute;
  top: 16px;
  right: 40%;
  bottom: 44%;
  left: 0;
  -webkit-mask-image: linear-gradient(to right, #000 0%, #000 72%, transparent 100%);
  mask-image: linear-gradient(to right, #000 0%, #000 72%, transparent 100%);
}

.backdrop__svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
}

.backdrop__sector,
.backdrop__line,
.backdrop__glint {
  fill: none;
  vector-effect: non-scaling-stroke;
}

.backdrop__sector {
  stroke: color-mix(in srgb, var(--c-text) 22%, transparent);
  stroke-dasharray: 3 5;
  stroke-width: 1;
  animation: backdrop-fade 600ms var(--ease-out) 500ms backwards;
}

.backdrop__area {
  animation: backdrop-fade 900ms var(--ease-out) 350ms backwards;
}

.backdrop__line {
  stroke: color-mix(in srgb, var(--c-accent-text) 70%, transparent);
  stroke-dasharray: 1;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.6;
  animation: backdrop-draw 1100ms var(--ease-out) backwards;
}

/* A short bright piece of the same line that runs its length once. */
.backdrop__glint {
  opacity: 0;
  stroke: var(--bm-cyan);
  stroke-dasharray: 0.07 1;
  stroke-linecap: round;
  stroke-width: 2.4;
  filter: drop-shadow(0 0 5px var(--bm-cyan));
  animation: backdrop-glint 1300ms var(--ease-ios) 150ms;
}

.backdrop__mark {
  position: absolute;
  top: 0;
  padding-left: 6px;
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.12em;
  animation: backdrop-fade 600ms var(--ease-out) 500ms backwards;
}

.backdrop__sweep {
  position: absolute;
  inset: -20% -40%;
  background: linear-gradient(105deg, transparent 44%, color-mix(in srgb, var(--bm-blue-bright) 16%, transparent) 50%, transparent 56%);
  opacity: 0;
  animation: backdrop-sweep 1000ms var(--ease-ios);
}

@keyframes backdrop-draw {
  from {
    stroke-dashoffset: 1;
  }
}

@keyframes backdrop-fade {
  from {
    opacity: 0;
  }
}

@keyframes backdrop-glint {
  0% {
    opacity: 0;
    stroke-dashoffset: 0.07;
  }
  15%,
  80% {
    opacity: 1;
  }
  100% {
    opacity: 0;
    stroke-dashoffset: -1;
  }
}

@keyframes backdrop-sweep {
  0% {
    opacity: 1;
    transform: translateX(-55%);
  }
  100% {
    opacity: 1;
    transform: translateX(55%);
  }
}

/* Stacked header on phones: the chart sits behind the track, fainter. */
@media (max-width: 760px) {
  .backdrop__chart {
    right: 0;
    bottom: auto;
    height: 150px;
    opacity: 0.3;
  }

  .backdrop__mark {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .backdrop__sector,
  .backdrop__area,
  .backdrop__line,
  .backdrop__glint,
  .backdrop__mark,
  .backdrop__sweep {
    animation: none;
  }
}
</style>
