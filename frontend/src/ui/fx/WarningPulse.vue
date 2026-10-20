<script setup>
// A red warning triangle that pulses to pull the eye to something the user
// must not miss: it swells a little and throws off a fading echo of itself.
// Set `calm` once the user has dealt with it and the sign stands still.
// Decorative: say what the warning is in the text beside it.
import { TriangleAlert } from 'lucide-vue-next'

defineProps({
  size: { type: Number, default: 18 },
  calm: { type: Boolean, default: false }
})
</script>

<template>
  <span class="warn" :class="{ 'is-calm': calm }" :style="{ '--warn-size': `${size}px` }" aria-hidden="true">
    <TriangleAlert class="warn__echo" :size="size" />
    <TriangleAlert class="warn__sign" :size="size" />
  </span>
</template>

<style scoped>
.warn {
  position: relative;
  display: inline-grid;
  flex: none;
  width: var(--warn-size);
  height: var(--warn-size);
  color: var(--bm-red);
}

.warn__sign,
.warn__echo {
  grid-area: 1 / 1;
  /* The triangle's weight sits low: turn around that point, not the box centre. */
  transform-origin: 50% 62%;
}

.warn__sign {
  animation: warn-beat 1.4s var(--ease-ios) infinite;
}

.warn__echo {
  opacity: 0;
  animation: warn-echo 1.4s var(--ease-out) infinite;
}

.is-calm .warn__sign,
.is-calm .warn__echo {
  animation: none;
}

@keyframes warn-beat {
  0%,
  100% {
    filter: drop-shadow(0 0 0 transparent);
    transform: scale(1);
  }
  18% {
    filter: drop-shadow(0 0 7px color-mix(in srgb, var(--bm-red) 85%, transparent));
    transform: scale(1.18);
  }
  40% {
    filter: drop-shadow(0 0 0 transparent);
    transform: scale(1);
  }
}

@keyframes warn-echo {
  0% {
    opacity: 0.7;
    transform: scale(1);
  }
  70%,
  100% {
    opacity: 0;
    transform: scale(2.3);
  }
}

@media (prefers-reduced-motion: reduce) {
  .warn__sign,
  .warn__echo {
    animation: none;
  }
}
</style>
