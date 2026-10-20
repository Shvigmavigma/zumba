<script setup>
// Rank crest: a faceted hexagon in the rank's metal whose glyph climbs from a
// dot through one, two and three chevrons to a star, a gem and a crown.
import { useId } from 'vue'

defineProps({
  rank: { type: String, default: 'rookie' },
  size: { type: Number, default: 40 },
  /** Accessible name; without it the crest is decorative. */
  label: { type: String, default: '' }
})

const uid = `rank-${useId()}`
</script>

<template>
  <svg
    class="emblem"
    :data-rank="rank"
    :width="size"
    :height="size"
    viewBox="0 0 48 48"
    :role="label ? 'img' : undefined"
    :aria-label="label || undefined"
    :aria-hidden="label ? undefined : 'true'"
  >
    <defs>
      <linearGradient :id="`${uid}-metal`" x1="0.1" y1="0" x2="0.9" y2="1">
        <stop offset="0" style="stop-color: var(--rank-1)" />
        <stop offset="0.5" style="stop-color: var(--rank-2)" />
        <stop offset="1" style="stop-color: var(--rank-3)" />
      </linearGradient>
    </defs>
    <path d="M24 2 43 13v22L24 46 5 35V13Z" :fill="`url(#${uid}-metal)`" />
    <path d="M24 7.5 38.3 15.8v16.4L24 40.5 9.7 32.2V15.8Z" fill="rgba(0, 0, 0, 0.3)" stroke="rgba(255, 255, 255, 0.4)" stroke-width="1" />
    <g class="emblem__glyph">
      <circle v-if="rank === 'rookie'" cx="24" cy="24" r="4.5" />
      <template v-else-if="rank === 'bronze' || rank === 'silver' || rank === 'gold'">
        <polyline points="16,29 24,22 32,29" />
        <polyline v-if="rank !== 'bronze'" points="16,23 24,16 32,23" />
        <polyline v-if="rank === 'gold'" points="16,35 24,28 32,35" />
      </template>
      <polygon v-else-if="rank === 'platinum'" class="is-fill" points="24,13 27.2,20.3 35,21 29,26.2 30.9,34 24,29.8 17.1,34 19,26.2 13,21 20.8,20.3" />
      <template v-else-if="rank === 'diamond'">
        <polygon class="is-fill" points="17,19 31,19 35,23.5 24,35 13,23.5" />
        <polyline class="is-facet" points="13,23.5 35,23.5" />
        <polyline class="is-facet" points="20,19 24,35 28,19" />
      </template>
      <path v-else class="is-fill" d="M13.5 31.5 15.5 18 20.5 24 24 15 27.5 24 32.5 18 34.5 31.5Z" />
    </g>
  </svg>
</template>

<style scoped>
.emblem {
  flex: none;
  overflow: visible;
  filter: drop-shadow(0 4px 10px rgba(0, 0, 0, 0.35)) drop-shadow(0 0 10px var(--rank-glow));
}

.emblem__glyph * {
  fill: none;
  stroke: #fff;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 3.2;
}

.emblem__glyph .is-fill {
  fill: #fff;
  stroke-width: 1.5;
}

.emblem__glyph .is-facet {
  stroke: var(--rank-3);
  stroke-width: 1.2;
}

.emblem__glyph circle {
  fill: #fff;
  stroke: none;
}
</style>
