<script setup>
// Flowing racing lines (after Kokonut UI's "Background Paths"): a bundle of
// curves is drawn in, then light pulses travel along them. Drawn with anime.js.
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { animate, createDrawable, stagger, utils } from 'animejs'
import { prefersReducedMotion } from '../motion/env'

const props = defineProps({
  count: { type: Number, default: 14 },
  /** Mirror the bundle horizontally. */
  flip: { type: Boolean, default: false }
})

const svg = ref(null)
const paths = Array.from({ length: props.count }, (_, index) => {
  const y = 120 + index * 14
  const bend = 140 + index * 6
  return {
    d: `M-80 ${y + 90} C 260 ${y - bend}, 520 ${y + bend * 0.9}, 820 ${y - 20} S 1180 ${y - bend * 0.55}, 1300 ${y - 10}`,
    width: 0.6 + index * 0.06,
    opacity: 0.06 + index * 0.022
  }
})
let animations = []

onMounted(() => {
  if (prefersReducedMotion() || !svg.value) return
  const lines = createDrawable(svg.value.querySelectorAll('.lines__base'))
  animations.push(animate(lines, {
    draw: ['0 0', '0 1'],
    duration: 1800,
    delay: stagger(60),
    ease: 'inOutQuart'
  }))
  const pulses = createDrawable(svg.value.querySelectorAll('.lines__pulse'))
  pulses.forEach((pulse, index) => {
    animations.push(animate(pulse, {
      draw: ['0 0.04', '0.96 1'],
      duration: utils.random(5200, 9000),
      delay: 1400 + index * 260,
      loop: true,
      ease: 'inOutSine'
    }))
  })
})

onBeforeUnmount(() => {
  animations.forEach((animation) => animation.revert?.() ?? animation.pause())
  animations = []
})
</script>

<template>
  <svg ref="svg" class="lines" :class="{ 'lines--flip': flip }" viewBox="0 0 1200 520" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs>
      <linearGradient id="lines-pulse" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="var(--bm-cyan)" stop-opacity="0" />
        <stop offset="0.5" stop-color="var(--bm-cyan)" />
        <stop offset="1" stop-color="var(--bm-blue-bright)" />
      </linearGradient>
    </defs>
    <path v-for="(path, index) in paths" :key="`b${index}`" class="lines__base" :d="path.d" :stroke-width="path.width" :stroke-opacity="path.opacity" />
    <path v-for="(path, index) in paths.filter((_, i) => i % 3 === 1)" :key="`p${index}`" class="lines__pulse" :d="path.d" stroke="url(#lines-pulse)" />
  </svg>
</template>

<style scoped>
.lines {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.lines--flip {
  transform: scaleX(-1);
}

.lines__base {
  fill: none;
  stroke: var(--c-accent-text);
}

.lines__pulse {
  fill: none;
  stroke-linecap: round;
  stroke-width: 1.6;
  opacity: 0.75;
  filter: drop-shadow(0 0 6px var(--bm-cyan));
}

:root[data-theme='light'] .lines__pulse {
  opacity: 0.55;
}

@media (prefers-reduced-motion: reduce) {
  .lines__pulse {
    display: none;
  }
}
</style>
