<script setup>
// The season champion's signature (see seasonChampion.js): tilted layers of
// bold, half-transparent "BMRL CHAMPION #1" drifting slowly, every other row
// the opposite way. Shared by the champion's backdrop (banner, licences,
// podium) and the finish laid over the champion's rows and cards in lists.
// Fills its positioned parent from the centre; the parent clips it.
import { computed } from 'vue'

const props = defineProps({
  /** 'hero' for the profile banner, 'card' for licences and cards, 'row' for list rows. */
  size: { type: String, default: 'hero' }
})

// rows: enough to cover the host once the block is tilted (a long list row
// needs many: its ends sit far above and below the centre line).
// phrases: one half of a row's loop; two identical halves make it seamless,
// and one half must be about twice as wide as the host.
// loop: seconds for a row to drift one half, slow enough to read as floating.
const LAYOUT = {
  hero: { rows: 24, phrases: 4, loop: 190 },
  card: { rows: 12, phrases: 4, loop: 130 },
  row: { rows: 18, phrases: 8, loop: 150 }
}
// Rows differ a little in speed and phase so the phrases never line up.
const LOOP_SPREAD = 0.3
const OUTLINE_EVERY = 3

const layout = computed(() => LAYOUT[props.size] || LAYOUT.hero)
const rows = computed(() =>
  Array.from({ length: layout.value.rows }, (_, index) => {
    const duration = layout.value.loop * (1 - LOOP_SPREAD / 2 + (((index * 37) % 100) / 100) * LOOP_SPREAD)
    return {
      down: index % 2 === 1,
      outline: index % OUTLINE_EVERY === 1,
      style: { '--loop': `${duration.toFixed(0)}s`, '--phase': `${-((index * 0.618) % 1) * duration}s` }
    }
  })
)
</script>

<template>
  <span class="layers" :class="`layers--${size}`" aria-hidden="true">
    <span v-for="(row, index) in rows" :key="index" class="layers__row" :class="{ 'is-down': row.down, 'is-outline': row.outline }">
      <span class="layers__track" :style="row.style">
        <b v-for="phrase in layout.phrases * 2" :key="phrase">BMRL CHAMPION <i>#1</i></b>
      </span>
    </span>
  </span>
</template>

<style scoped>
/* The block is anchored at the host's centre and tilted; each row is a
   zero-width anchor there, with its track running out both ways. */
.layers {
  --row-size: 46px;
  position: absolute;
  top: 50%;
  left: 50%;
  display: grid;
  width: 0;
  /* One blend for the whole block: under it the black fill of the outlined
     rows reads as nothing (see .ui-outline-text for the recipe). */
  mix-blend-mode: screen;
  transform: translateY(-50%) rotate(-14deg);
}

.layers--card {
  --row-size: 21px;
}

.layers--row {
  --row-size: 15px;
}

.layers__row {
  position: relative;
  height: calc(var(--row-size) * 1.5);
}

.layers__track {
  position: absolute;
  top: 0;
  left: 0;
  display: flex;
  width: max-content;
  animation: season-drift var(--loop) linear var(--phase) infinite;
}

/* Every other row floats the opposite way. */
.is-down .layers__track {
  animation-direction: reverse;
}

.layers__track b {
  padding-right: 0.8em;
  color: rgba(255, 255, 255, 0.05);
  font-family: var(--font-display);
  font-size: var(--row-size);
  font-weight: 900;
  line-height: 1.5;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  white-space: nowrap;
}

.layers__track i {
  color: rgba(245, 200, 76, 0.2);
  font-style: normal;
}

/* Outlined rows: the stroke goes down first and the opaque black fill covers
   the lines the font's overlapping contours would leave inside the letters.
   The stroke is twice the visible width, its inner half is under the fill. */
.is-outline .layers__track b {
  color: #000;
  -webkit-text-stroke: 2px rgba(245, 200, 76, 0.17);
  paint-order: stroke fill;
}

.is-outline .layers__track i {
  color: #000;
  -webkit-text-stroke-color: rgba(255, 243, 196, 0.32);
}

/* The track is two halves wide; between a quarter and three quarters of the
   way it always covers the host, and the two ends of the loop look the same. */
@keyframes season-drift {
  from {
    transform: translateX(-25%);
  }
  to {
    transform: translateX(-75%);
  }
}

/* On a phone the banner is a tall, narrow column: smaller letters keep a whole phrase in view. */
@media (max-width: 600px) {
  .layers--hero {
    --row-size: 38px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .layers__track {
    animation-play-state: paused;
  }
}
</style>
