<script setup>
// The BMRL signature: a five-light start gantry. It can run the real start
// procedure (lights on one by one, then "lights out"), show a fixed number of
// lit lamps, or loop as a loading indicator.
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { reducedMotion } from '../motion/env'

const props = defineProps({
  /** Controlled number of lit lamps (0–5) when no sequence is running. */
  lit: { type: Number, default: 0 },
  /** Run the start procedure once on mount. */
  sequence: { type: Boolean, default: false },
  /** Loop the procedure (used as a loader). */
  loop: { type: Boolean, default: false },
  /** Delay between lamps in ms. */
  interval: { type: Number, default: 260 },
  size: { type: String, default: 'md' },
  /** Two lamps per pod, like a real gantry. */
  double: { type: Boolean, default: false },
  label: { type: String, default: '' }
})
const emit = defineEmits(['lights-out'])

const LAMPS = 5
const running = ref(false)
const runLit = ref(0)
const flash = ref(false)
let timers = []

const litCount = computed(() => (running.value ? runLit.value : Math.max(0, Math.min(LAMPS, props.lit))))

function clearTimers() {
  timers.forEach((timer) => window.clearTimeout(timer))
  timers = []
}

function later(fn, ms) {
  timers.push(window.setTimeout(fn, ms))
}

function runSequence() {
  clearTimers()
  if (reducedMotion.value) {
    running.value = false
    emit('lights-out')
    return
  }
  running.value = true
  runLit.value = 0
  for (let index = 1; index <= LAMPS; index += 1) {
    later(() => { runLit.value = index }, props.interval * index)
  }
  const hold = props.interval * LAMPS + 420 + Math.round(Math.random() * 240)
  later(() => {
    runLit.value = 0
    flash.value = true
    emit('lights-out')
  }, hold)
  later(() => {
    flash.value = false
    if (props.loop) runSequence()
    else running.value = false
  }, hold + (props.loop ? 700 : 300))
}

onMounted(() => {
  if (props.sequence || props.loop) runSequence()
})

watch(() => props.sequence, (value) => {
  if (value && !running.value) runSequence()
})

watch(() => props.loop, (value) => {
  if (value) runSequence()
  else {
    clearTimers()
    running.value = false
  }
})

onBeforeUnmount(clearTimers)
</script>

<template>
  <div
    class="lights"
    :class="[`lights--${size}`, { 'is-double': double, 'is-flash': flash }]"
    role="img"
    :aria-label="label || `${litCount} / ${LAMPS}`"
  >
    <span v-for="index in LAMPS" :key="index" class="lights__pod">
      <span v-for="row in (double ? 2 : 1)" :key="row" class="lights__lamp" :class="{ 'is-on': index <= litCount }"></span>
    </span>
  </div>
</template>

<style scoped>
.lights {
  --lamp: 14px;
  --gap: 8px;
  display: inline-flex;
  width: max-content;
  align-items: center;
  gap: var(--gap);
  padding: calc(var(--gap) * 0.75);
  border: 1px solid var(--c-line);
  border-radius: var(--r-pill);
  background: color-mix(in srgb, #000 55%, transparent);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

:root[data-theme='light'] .lights {
  background: #0b111d;
}

.lights--sm {
  --lamp: 8px;
  --gap: 5px;
}

.lights--lg {
  --lamp: 22px;
  --gap: 12px;
}

.lights.is-double {
  border-radius: calc(var(--lamp) * 0.9);
}

.lights__pod {
  display: grid;
  gap: calc(var(--gap) * 0.6);
}

.lights__lamp {
  position: relative;
  width: var(--lamp);
  height: var(--lamp);
  border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, #2a1418, #12080a 70%);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.05), inset 0 -2px 4px rgba(0, 0, 0, 0.6);
  transition: background 120ms linear, box-shadow 160ms linear, transform 300ms var(--ease-spring);
}

.lights__lamp.is-on {
  background: radial-gradient(circle at 38% 32%, #ffd6d9 0, #ff3347 28%, #c10016 70%, #6a000b 100%);
  box-shadow:
    0 0 calc(var(--lamp) * 0.7) rgba(255, 40, 60, 0.85),
    0 0 calc(var(--lamp) * 1.8) rgba(255, 30, 50, 0.45),
    inset 0 0 0 1px rgba(255, 255, 255, 0.25);
  transform: scale(1.06);
}

.lights.is-flash .lights__lamp {
  animation: lights-out 420ms var(--ease-out);
}

@keyframes lights-out {
  0% {
    box-shadow: 0 0 calc(var(--lamp) * 1.4) rgba(255, 255, 255, 0.35);
  }
  100% {
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.05), inset 0 -2px 4px rgba(0, 0, 0, 0.6);
  }
}
</style>
