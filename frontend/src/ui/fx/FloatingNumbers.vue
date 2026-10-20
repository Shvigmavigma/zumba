<script setup>
// Faint pilot numbers scattered behind a panel. Each one drifts slowly in
// place and now and then flips to a new number, digit by digit, like a
// timing board. Purely decorative: hidden from assistive technology.
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { prefersReducedMotion } from '../motion/env'
import { randomPlate, scatter, scrambleFrame } from './floatingNumbers'

const props = defineProps({
  count: { type: Number, default: 16 }
})

const FLIP_PAUSE_MS = [650, 1500]
const FLIP_DURATION_MS = 760
const FRAME_MS = 45
const SECOND_FLIP_CHANCE = 0.35

function between(min, max) {
  return min + Math.random() * (max - min)
}

// Big numbers read as car plates, small ones as "#077" tags; the faintest and
// smallest are softened so the field has some depth.
const spots = scatter(props.count).map((spot, index) => {
  const big = Math.random() < 0.45
  const size = big ? between(44, 78) : between(18, 30)
  return {
    id: index,
    big,
    style: {
      '--x': `${spot.x}%`,
      '--y': `${spot.y}%`,
      '--size': `${size}px`,
      '--alpha': (big ? between(0.05, 0.09) : between(0.08, 0.14)).toFixed(3),
      '--blur': `${size < 22 ? 0.6 : 0}px`,
      '--rot': `${between(-7, 7).toFixed(1)}deg`,
      '--dx': `${between(8, 20).toFixed(1)}px`,
      '--dy': `${between(6, 16).toFixed(1)}px`,
      '--dur': `${between(9, 17).toFixed(1)}s`,
      '--delay': `${(-between(0, 17)).toFixed(1)}s`
    }
  }
})

function plateFor(spot) {
  return spot.big ? randomPlate() : `#${randomPlate()}`
}

const texts = ref(spots.map(plateFor))
const flipping = ref(new Set())
const frameTimers = new Map()
let nextFlip = 0

function setText(index, value) {
  texts.value = texts.value.map((text, i) => (i === index ? value : text))
}

function flip(index) {
  if (frameTimers.has(index)) return
  const target = plateFor(spots[index])
  const startedAt = Date.now()
  flipping.value = new Set([...flipping.value, index])
  const timer = window.setInterval(() => {
    const progress = Math.min(1, (Date.now() - startedAt) / FLIP_DURATION_MS)
    setText(index, scrambleFrame(target, progress))
    if (progress < 1) return
    window.clearInterval(timer)
    frameTimers.delete(index)
    flipping.value = new Set([...flipping.value].filter((item) => item !== index))
  }, FRAME_MS)
  frameTimers.set(index, timer)
}

function randomIndex() {
  return Math.floor(Math.random() * spots.length)
}

function scheduleFlip() {
  nextFlip = window.setTimeout(() => {
    // A background tab gets no flips; timers there are throttled anyway.
    if (!document.hidden && spots.length) {
      flip(randomIndex())
      if (Math.random() < SECOND_FLIP_CHANCE) flip(randomIndex())
    }
    scheduleFlip()
  }, between(...FLIP_PAUSE_MS))
}

onMounted(() => {
  if (!prefersReducedMotion()) scheduleFlip()
})

onBeforeUnmount(() => {
  window.clearTimeout(nextFlip)
  frameTimers.forEach((timer) => window.clearInterval(timer))
  frameTimers.clear()
})
</script>

<template>
  <div class="fnums" aria-hidden="true">
    <span
      v-for="(spot, index) in spots"
      :key="spot.id"
      class="fnum"
      :class="[spot.big ? 'fnum--plate' : 'fnum--tag', { 'is-flipping': flipping.has(index) }]"
      :style="spot.style"
    >{{ texts[index] }}</span>
  </div>
</template>

<style scoped>
.fnums {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  user-select: none;
}

.fnum {
  position: absolute;
  top: var(--y);
  left: var(--x);
  color: var(--c-text);
  font-size: var(--size);
  line-height: 1;
  white-space: nowrap;
  opacity: var(--alpha);
  filter: blur(var(--blur));
  transform: translate(-50%, -50%) rotate(var(--rot));
  animation: fnum-drift var(--dur) ease-in-out var(--delay) infinite alternate;
  transition: opacity 500ms var(--ease-out), color 500ms var(--ease-out);
}

.fnum--plate {
  font-family: var(--font-display);
  font-weight: 800;
  letter-spacing: -0.02em;
}

.fnum--tag {
  font-family: var(--font-mono);
  font-weight: 600;
  letter-spacing: 0.06em;
}

/* A flipping number briefly catches the light. */
.fnum.is-flipping {
  color: var(--bm-cyan);
  opacity: calc(var(--alpha) * 2.4);
  transition-duration: 150ms;
}

/* Drift uses `translate`, separate from the centring and tilt in `transform`. */
@keyframes fnum-drift {
  0% {
    translate: 0 0;
  }
  35% {
    translate: var(--dx) calc(var(--dy) * -1);
  }
  70% {
    translate: calc(var(--dx) * -0.6) var(--dy);
  }
  100% {
    translate: calc(var(--dx) * 0.3) calc(var(--dy) * -0.4);
  }
}

@media (prefers-reduced-motion: reduce) {
  .fnum {
    animation: none;
  }
}
</style>
