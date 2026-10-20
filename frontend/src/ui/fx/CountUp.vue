<script setup>
// Number that counts up when it first scrolls into view and eases between
// later values (React Bits' CountUp, driven by anime.js).
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { animate } from 'animejs'
import { onceInView, prefersReducedMotion } from '../motion/env'

const props = defineProps({
  value: { type: [Number, String], default: 0 },
  duration: { type: Number, default: 1600 },
  decimals: { type: Number, default: 0 },
  /** Group thousands with a thin space, like a timing screen. */
  group: { type: Boolean, default: true },
  prefix: { type: String, default: '' },
  suffix: { type: String, default: '' }
})

const root = ref(null)
const shown = ref(0)
const started = ref(false)
let animation = null
let stopObserving = null

const target = computed(() => {
  const number = Number(props.value)
  return Number.isFinite(number) ? number : 0
})

const isNumeric = computed(() => Number.isFinite(Number(props.value)))

const text = computed(() => {
  const fixed = shown.value.toFixed(props.decimals)
  if (!props.group) return fixed
  const [whole, fraction] = fixed.split('.')
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
  return fraction ? `${grouped},${fraction}` : grouped
})

function run(from, to) {
  animation?.pause()
  if (prefersReducedMotion()) {
    shown.value = to
    return
  }
  const counter = { value: from }
  animation = animate(counter, {
    value: to,
    duration: props.duration,
    ease: 'outExpo',
    onUpdate: () => { shown.value = counter.value }
  })
}

onMounted(() => {
  stopObserving = onceInView(root.value, () => {
    started.value = true
    run(0, target.value)
  })
})

watch(target, (to, from) => {
  if (started.value) run(Number.isFinite(from) ? shown.value : 0, to)
})

onBeforeUnmount(() => {
  animation?.pause()
  stopObserving?.()
})
</script>

<template>
  <span ref="root" class="count-up ui-num">
    <template v-if="isNumeric">{{ prefix }}{{ text }}{{ suffix }}</template>
    <template v-else>{{ value }}</template>
  </span>
</template>
