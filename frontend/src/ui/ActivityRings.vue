<script setup>
// Concentric progress rings in the style of Apple's Activity rings
// (Kokonut UI "Apple activity card"). Rings fill with anime.js on first view.
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { animate } from 'animejs'
import { onceInView, prefersReducedMotion } from './motion/env'

const props = defineProps({
  /** [{ value: 0..1, color, label }] — outermost first. */
  rings: { type: Array, required: true },
  size: { type: Number, default: 132 },
  stroke: { type: Number, default: 12 },
  gap: { type: Number, default: 4 }
})

const root = ref(null)
const progress = ref(props.rings.map(() => 0))
let stop = null
let started = false
let animation = null

const geometry = computed(() => props.rings.map((ring, index) => {
  const radius = props.size / 2 - props.stroke / 2 - index * (props.stroke + props.gap)
  const circumference = 2 * Math.PI * radius
  return { ...ring, radius, circumference }
}))

function fill() {
  const targets = props.rings.map((ring) => Math.max(0, Math.min(1, Number(ring.value) || 0)))
  if (prefersReducedMotion()) {
    progress.value = targets
    return
  }
  const state = { ...progress.value }
  animation?.pause()
  animation = animate(state, {
    ...Object.fromEntries(targets.map((value, index) => [index, value])),
    duration: 1600,
    ease: 'outExpo',
    onUpdate: () => { progress.value = targets.map((_, index) => state[index]) }
  })
}

onMounted(() => {
  stop = onceInView(root.value, () => {
    started = true
    fill()
  })
})
watch(() => props.rings.map((ring) => ring.value).join(','), () => {
  if (started) fill()
})
onBeforeUnmount(() => {
  stop?.()
  animation?.pause()
})
</script>

<template>
  <svg ref="root" class="rings" :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`" role="img" :aria-label="rings.map((ring) => `${ring.label}: ${Math.round((ring.value || 0) * 100)}%`).join(', ')">
    <g :transform="`rotate(-90 ${size / 2} ${size / 2})`">
      <template v-for="(ring, index) in geometry" :key="index">
        <circle class="rings__track" :cx="size / 2" :cy="size / 2" :r="ring.radius" :stroke-width="stroke" :stroke="ring.color" />
        <circle
          class="rings__value"
          :cx="size / 2"
          :cy="size / 2"
          :r="ring.radius"
          :stroke-width="stroke"
          :stroke="ring.color"
          :stroke-dasharray="ring.circumference"
          :stroke-dashoffset="ring.circumference * (1 - progress[index])"
          :style="{ filter: `drop-shadow(0 0 6px ${ring.color})` }"
        />
      </template>
    </g>
  </svg>
</template>

<style scoped>
.rings {
  flex: 0 0 auto;
  overflow: visible;
}

.rings circle {
  fill: none;
  stroke-linecap: round;
}

.rings__track {
  opacity: 0.16;
}
</style>
