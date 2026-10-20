<script setup>
// Live countdown to a moment (race start, registration close) with rolling digits.
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import RollingNumber from './RollingNumber.vue'

const props = defineProps({
  target: { type: [String, Date, Number], default: null },
  size: { type: String, default: 'md' }
})
const emit = defineEmits(['done'])
const { t } = useI18n()

const now = ref(Date.now())
let timer = 0

const targetMs = computed(() => {
  const value = props.target instanceof Date ? props.target.getTime() : new Date(props.target).getTime()
  return Number.isFinite(value) ? value : null
})
const remaining = computed(() => (targetMs.value === null ? 0 : Math.max(0, targetMs.value - now.value)))
const parts = computed(() => {
  const total = Math.floor(remaining.value / 1000)
  return [
    { key: 'days', value: Math.floor(total / 86400), label: t('ui.countdown.days') },
    { key: 'hours', value: Math.floor((total % 86400) / 3600), label: t('ui.countdown.hours') },
    { key: 'minutes', value: Math.floor((total % 3600) / 60), label: t('ui.countdown.minutes') },
    { key: 'seconds', value: total % 60, label: t('ui.countdown.seconds') }
  ]
})

function tick() {
  now.value = Date.now()
  if (targetMs.value !== null && remaining.value === 0) {
    window.clearInterval(timer)
    timer = 0
    emit('done')
  }
}

function startTimer() {
  window.clearInterval(timer)
  timer = window.setInterval(tick, 1000)
  tick()
}

onMounted(startTimer)
watch(targetMs, startTimer)
onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <div class="countdown" :class="`countdown--${size}`" role="timer" aria-live="off">
    <div v-for="part in parts" :key="part.key" class="countdown__tile">
      <RollingNumber class="countdown__value" :value="String(part.value).padStart(2, '0')" />
      <span class="countdown__label">{{ part.label }}</span>
    </div>
  </div>
</template>

<style scoped>
.countdown {
  display: inline-grid;
  grid-auto-flow: column;
  gap: 8px;
}

.countdown__tile {
  display: grid;
  justify-items: center;
  gap: 6px;
  min-width: 64px;
  padding: 12px 10px 10px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-md);
  background: color-mix(in srgb, var(--c-bg) 55%, transparent);
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
}

.countdown__value {
  color: var(--c-text);
  font-size: 30px;
  font-weight: 600;
}

.countdown__label {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.countdown--sm .countdown__tile {
  min-width: 48px;
  padding: 8px 6px 7px;
  border-radius: var(--r-sm);
}

.countdown--sm .countdown__value {
  font-size: 20px;
}

@media (max-width: 520px) {
  .countdown {
    gap: 6px;
  }

  .countdown__tile {
    min-width: 0;
    padding: 10px 8px 8px;
  }

  .countdown__value {
    font-size: 24px;
  }
}
</style>
