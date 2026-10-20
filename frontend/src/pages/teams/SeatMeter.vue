<script setup>
// Roster capacity as a row of grid slots: one segment per seat, taken seats
// light up in the team colour one after another, like start lights.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { onceInView } from '../../ui/motion/env'
import { MAX_SEAT_SEGMENTS } from './teamUtils'

const props = defineProps({
  count: { type: Number, default: 0 },
  limit: { type: Number, default: 0 },
  label: { type: String, default: '' }
})

const root = ref(null)
const lit = ref(false)
let stop = null

const taken = computed(() => Math.max(0, Math.min(props.count, props.limit)))
const segmented = computed(() => props.limit > 0 && props.limit <= MAX_SEAT_SEGMENTS)
const percent = computed(() => (props.limit ? Math.round((taken.value / props.limit) * 100) : 0))
const isFull = computed(() => props.limit > 0 && props.count >= props.limit)

onMounted(() => {
  stop = onceInView(root.value, () => { lit.value = true })
})

onBeforeUnmount(() => stop?.())
</script>

<template>
  <span
    ref="root"
    class="seats"
    :class="{ 'is-lit': lit, 'is-full': isFull, 'is-bar': !segmented }"
    role="meter"
    :aria-valuemin="0"
    :aria-valuemax="limit"
    :aria-valuenow="taken"
    :aria-label="label || `${count}/${limit}`"
  >
    <template v-if="segmented">
      <i v-for="seat in limit" :key="seat" class="seats__slot" :class="{ 'is-taken': seat <= taken }" :style="{ '--i': seat }"></i>
    </template>
    <i v-else class="seats__bar" :style="{ '--value': lit ? `${percent}%` : '0%' }"></i>
  </span>
</template>

<style scoped>
.seats {
  --seat-on: color-mix(in srgb, var(--team, var(--bm-blue)) 78%, var(--c-text) 22%);
  display: flex;
  align-items: center;
  gap: 3px;
  width: 100%;
  height: 8px;
}

.seats__slot {
  flex: 1 1 0;
  height: 100%;
  min-width: 3px;
  border-radius: 3px;
  background: color-mix(in srgb, var(--c-text) 10%, transparent);
  transition:
    background-color 420ms var(--ease-out),
    box-shadow 420ms var(--ease-out),
    transform 520ms var(--ease-spring);
  transition-delay: calc(var(--i) * 55ms);
}

.seats.is-lit .seats__slot.is-taken {
  background: var(--seat-on);
  box-shadow: 0 0 10px color-mix(in srgb, var(--seat-on) 55%, transparent);
  transform: scaleY(1.15);
}

.seats.is-full.is-lit .seats__slot.is-taken {
  --seat-on: color-mix(in srgb, var(--bm-amber) 85%, var(--c-text));
}

.seats.is-bar {
  position: relative;
  overflow: hidden;
  border-radius: var(--r-pill);
  background: color-mix(in srgb, var(--c-text) 10%, transparent);
}

.seats__bar {
  position: absolute;
  inset: 0 auto 0 0;
  width: var(--value, 0%);
  border-radius: inherit;
  background: var(--seat-on);
  box-shadow: 0 0 12px color-mix(in srgb, var(--seat-on) 55%, transparent);
  transition: width 1.1s var(--ease-out);
}

@media (prefers-reduced-motion: reduce) {
  .seats__slot,
  .seats__bar {
    transition: none;
  }
}
</style>
