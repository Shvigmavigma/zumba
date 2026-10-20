<script setup>
// Security foil printed on BMRL licences, like a driving licence hologram: a
// ribbon of BMRL marks and a round seal that run through the rainbow as the
// card tilts (--gx, --gy and --glare come from v-tilt on the card). Higher
// ranks print it brighter. Place it inside a positioned, rounded card.
import { computed } from 'vue'
import { brandingSettings } from '../../brandingSettings'
import { RANK_KEYS } from '../../ranks'

const props = defineProps({
  rank: { type: String, default: 'rookie' }
})

// Logos with transparency make a clean stencil; anything else (an uploaded
// JPG) would print as a rectangle, so the bundled cutout is used instead.
const FALLBACK_MARK = '/assets/bmrl-logo-dark-cutout.png'
// Resting visibility per rank; the tilt glare adds on top.
const FOIL_REST = [0.12, 0.13, 0.15, 0.18, 0.21, 0.24, 0.28]
// The ribbon runs corner to corner behind the content, small at the ends.
const MARKS = [
  { x: 9, y: 90, w: 58 },
  { x: 29, y: 71, w: 74 },
  { x: 50, y: 52, w: 92 },
  { x: 71, y: 33, w: 74 },
  { x: 91, y: 14, w: 58 },
  { x: 22, y: 20, w: 44 },
  { x: 64, y: 88, w: 44 }
].map((mark, index) => ({ ...mark, shift: `${index * 14}%` }))

const markUrl = computed(() => {
  const url = brandingSettings.dark_logo_url || ''
  return /\.(png|webp|svg)(\?|$)/i.test(url) ? url : FALLBACK_MARK
})
const style = computed(() => ({
  '--mark': `url(${JSON.stringify(markUrl.value)})`,
  '--foil-rest': FOIL_REST[Math.max(0, RANK_KEYS.indexOf(props.rank))]
}))
</script>

<template>
  <span class="foil" :style="style" aria-hidden="true">
    <span
      v-for="(mark, index) in MARKS"
      :key="index"
      class="foil__mark foil__layer"
      :style="{ '--x': `${mark.x}%`, '--y': `${mark.y}%`, '--w': `${mark.w}px`, '--shift': mark.shift }"
    ></span>
    <span class="foil__seal">
      <span class="foil__seal-rings foil__layer"></span>
      <span class="foil__seal-mark foil__layer"></span>
    </span>
  </span>
</template>

<style scoped>
.foil {
  position: absolute;
  inset: 0;
  z-index: -1;
  overflow: hidden;
  border-radius: inherit;
  pointer-events: none;
}

/* Shared rainbow foil: the tilt moves it, a slow hue drift keeps it alive on
   touch screens where nothing tilts. */
.foil__layer {
  position: absolute;
  background: linear-gradient(115deg, #ff7ad9, #a78bfa, #60a5fa, #4fd8ea, #6ee7b7, #fde68a, #fb923c, #ff7ad9)
    calc(var(--gx, 50%) + var(--shift, 0%)) var(--gy, 50%) / 420% 420%;
  mix-blend-mode: screen;
  opacity: calc(var(--foil-rest, 0.12) + var(--glare, 0) * 0.22);
  animation: foil-drift 7s ease-in-out infinite alternate;
  transition: opacity 400ms var(--ease-out);
}

@keyframes foil-drift {
  to {
    filter: hue-rotate(80deg);
  }
}

.foil__mark {
  top: var(--y);
  left: var(--x);
  width: var(--w);
  aspect-ratio: 1061 / 250;
  -webkit-mask: var(--mark) center / contain no-repeat;
  mask: var(--mark) center / contain no-repeat;
  transform: translate(-50%, -50%) rotate(-14deg);
}

.foil__seal {
  position: absolute;
  right: -24px;
  bottom: -30px;
  width: 132px;
  aspect-ratio: 1;
}

/* Fine guilloche-like rings, fading out towards the rim. */
.foil__seal-rings {
  inset: 0;
  border-radius: 50%;
  -webkit-mask:
    repeating-radial-gradient(circle, #000 0 1.1px, transparent 1.1px 4.4px),
    radial-gradient(circle, #000 55%, transparent 71%);
  -webkit-mask-composite: source-in;
  mask:
    repeating-radial-gradient(circle, #000 0 1.1px, transparent 1.1px 4.4px) intersect,
    radial-gradient(circle, #000 55%, transparent 71%);
}

.foil__seal-mark {
  top: 50%;
  left: 50%;
  width: 62%;
  aspect-ratio: 1061 / 250;
  -webkit-mask: var(--mark) center / contain no-repeat;
  mask: var(--mark) center / contain no-repeat;
  opacity: calc(var(--foil-rest, 0.12) + 0.06 + var(--glare, 0) * 0.26);
  transform: translate(-50%, -50%) rotate(-14deg);
}

@media (prefers-reduced-motion: reduce) {
  .foil__layer {
    animation: none;
  }
}
</style>
