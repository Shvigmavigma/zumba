<script>
// One filter per intro on the page; a counter keeps their ids apart.
let introCount = 0
</script>

<script setup>
// The winner's graphic over a finished race's header, as the broadcasts show
// it: a brand-blue LED screen filled with rows of WINNER in the display type,
// drawn in LED lines, rows sliding past each other. From the middle out the
// blue goes black, block by block like pixels. The word in the middle is
// hollow, only its first letter filled in gold. The rows flip over to the
// winner's first name, then the screen clears and the header comes in under it
// (RaceHero.vue). A click or tap skips it. Decorative: hidden from readers.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { INTRO_END_MS, INTRO_TIMING, PIXEL_BLOCK, WINNER_WORD, accentParts, pixelOrder, wallRows, wallScale } from './winnerIntro'

// The black spreads in this many steps, not smoothly.
const PIXEL_STEPS = 16
const BLACK = '#020409'

const props = defineProps({
  /** The winner's first name. */
  name: { type: String, required: true }
})
const emit = defineEmits(['done', 'skip'])

// Enough rows to fill a phone-tall header too; the rest is cut by its edges.
const rows = wallRows({ rows: 17 })
const walls = computed(() => [
  { key: 'winner', word: WINNER_WORD, scale: 1, accent: accentParts(WINNER_WORD) },
  { key: 'name', word: props.name, scale: wallScale(props.name), accent: accentParts(props.name) }
])
const hollowId = `winner-hollow-${++introCount}`
const timing = {
  '--pixels-at': `${INTRO_TIMING.pixelsAt}ms`,
  '--pixels-ms': `${INTRO_TIMING.pixelsMs}ms`,
  '--name-at': `${INTRO_TIMING.nameAt}ms`,
  '--clear-at': `${INTRO_TIMING.clearAt}ms`,
  '--clear-ms': `${INTRO_TIMING.clearMs}ms`,
  '--total': `${INTRO_END_MS}ms`
}

const pixels = ref(null)
let timer = 0
let frame = 0

/**
 * Paints the black, one canvas pixel per block, stretched over the screen
 * without smoothing. Its clock is the canvas's own CSS animation, so it keeps
 * time with the rest of the intro (and stops with it).
 */
function startPixels() {
  const canvas = pixels.value
  const box = canvas?.parentElement?.getBoundingClientRect()
  const context = canvas?.getContext('2d')
  if (!canvas || !context || !box?.width || !box?.height) return
  // An odd count, so one block sits right on the middle.
  const cols = Math.ceil(box.width / PIXEL_BLOCK) | 1
  const rows = Math.ceil(box.height / PIXEL_BLOCK) | 1
  canvas.width = cols
  canvas.height = rows
  canvas.style.width = `${cols * PIXEL_BLOCK}px`
  canvas.style.height = `${rows * PIXEL_BLOCK}px`
  const order = pixelOrder(cols, rows)
  const clock = canvas.getAnimations()[0]
  let shown = -1
  const draw = () => {
    const progress = clock?.effect?.getComputedTiming().progress ?? 1
    const step = Math.floor(progress * PIXEL_STEPS) / PIXEL_STEPS
    if (step !== shown) {
      shown = step
      context.clearRect(0, 0, cols, rows)
      context.fillStyle = BLACK
      for (let index = 0; index < order.length; index += 1) {
        if (order[index] < step) context.fillRect(index % cols, Math.floor(index / cols), 1, 1)
      }
    }
    frame = window.requestAnimationFrame(draw)
  }
  draw()
}

onMounted(() => {
  timer = window.setTimeout(() => emit('done'), INTRO_END_MS)
  startPixels()
})
onBeforeUnmount(() => {
  window.clearTimeout(timer)
  window.cancelAnimationFrame(frame)
})
</script>

<template>
  <div class="intro" :style="timing" aria-hidden="true" @click="emit('skip')">
    <!-- The hollow type: the letters widened by 2px, less the letters themselves. Unlike a
         text stroke it does not show where the font's outlines overlap inside a letter. -->
    <svg class="intro__defs" width="0" height="0" focusable="false">
      <filter :id="hollowId" x="-4%" y="-12%" width="108%" height="124%" color-interpolation-filters="sRGB">
        <feMorphology in="SourceAlpha" operator="dilate" radius="2" result="wide" />
        <feComposite in="wide" in2="SourceAlpha" operator="out" result="ring" />
        <feFlood flood-color="#ffffff" />
        <feComposite in2="ring" operator="in" />
      </filter>
    </svg>
    <canvas ref="pixels" class="intro__pixels"></canvas>
    <div v-for="wall in walls" :key="wall.key" class="intro__wall" :class="`intro__wall--${wall.key}`" :style="{ '--scale': wall.scale }">
      <div v-for="row in rows" :key="row.id" class="intro__row" :style="{ '--dir': row.dir, '--far': row.far }">
        <div class="intro__track">
          <span v-for="item in row.words" :key="item.id" class="intro__word" :class="`is-${item.look}`">
            <template v-if="item.look === 'accent'"><b>{{ wall.accent.first }}</b><span class="intro__hollow" :style="{ filter: `url(#${hollowId}) drop-shadow(0 0 14px rgba(255, 255, 255, 0.3))` }">{{ wall.accent.rest }}</span></template>
            <template v-else>{{ wall.word }}</template>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* The screen: brand blue lit from the middle, LED scan lines and a dark rim. */
.intro {
  --size: clamp(54px, 10vw, 124px);
  position: absolute;
  inset: 0;
  z-index: 6;
  overflow: hidden;
  border-radius: inherit;
  background: radial-gradient(90% 75% at 50% 48%, #2f6cff 0%, var(--bm-blue) 42%, #0a2272 100%);
  cursor: pointer;
  animation: intro-clear var(--clear-ms) ease-in var(--clear-at) forwards;
}

.intro__defs {
  position: absolute;
  width: 0;
  height: 0;
  overflow: hidden;
}

/* The black, block by block (drawn by startPixels), over the blue and under the type. */
.intro__pixels {
  position: absolute;
  top: 50%;
  left: 50%;
  translate: -50% -50%;
  image-rendering: pixelated;
  animation: intro-pixels var(--pixels-ms) linear var(--pixels-at) both;
}

.intro::after {
  position: absolute;
  inset: 0;
  background:
    repeating-linear-gradient(180deg, rgba(0, 8, 40, 0.16) 0 1px, transparent 1px 3px),
    radial-gradient(120% 100% at 50% 50%, transparent 55%, rgba(0, 6, 30, 0.5));
  content: '';
  pointer-events: none;
}

/* Taller than the header: centred on it by hand, so the accent row sits in the middle. */
.intro__wall {
  position: absolute;
  top: 50%;
  left: 0;
  display: grid;
  gap: 0.08em;
  width: 100%;
  translate: 0 -50%;
  font-family: var(--font-display);
  font-size: calc(var(--size) * var(--scale));
  font-weight: 800;
  line-height: 0.92;
  text-transform: uppercase;
  white-space: nowrap;
  animation: intro-wall-out var(--clear-ms) ease-in var(--clear-at) forwards;
}

.intro__row {
  position: relative;
  height: 0.92em;
  transform-origin: 50% 50%;
}

/* Rows wider than the screen, centred on it and sliding along the whole intro. */
.intro__track {
  position: absolute;
  top: 0;
  left: 50%;
  display: flex;
  gap: 0.38em;
  animation: intro-slide var(--total) linear both;
  will-change: transform;
}

/* WINNER lights up from the middle row outwards, then the rows flip off one by one... */
.intro__wall--winner .intro__row {
  animation:
    intro-row-on 300ms cubic-bezier(0.2, 0.9, 0.3, 1) calc(var(--far) * 45ms) backwards,
    intro-row-off 140ms ease-in calc(var(--name-at) + var(--far) * 35ms) forwards;
}

/* ...and flip back on with the winner's name. */
.intro__wall--name .intro__row {
  animation: intro-row-on 240ms cubic-bezier(0.2, 0.9, 0.3, 1) calc(var(--name-at) + 120ms + var(--far) * 35ms) backwards;
}

/* ---------- The LED type ---------- */
.intro__word {
  display: inline-block;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.intro__word.is-lines {
  background-image: repeating-linear-gradient(180deg, rgba(255, 255, 255, 0.86) 0 2px, transparent 2px 4.5px);
}

.intro__word.is-ghost {
  background-image: repeating-linear-gradient(180deg, rgba(255, 255, 255, 0.3) 0 2px, transparent 2px 4.5px);
}

.intro__word.is-solid {
  background-image: repeating-linear-gradient(180deg, #fff 0 2px, rgba(255, 255, 255, 0.74) 2px 4px);
}

/* The word in the middle: hollow, only an outline (the filter above), the first letter filled. */
.intro__word.is-accent {
  background: none;
  color: #fff;
}

.intro__hollow {
  color: #fff;
}

.intro__word.is-accent b {
  -webkit-background-clip: text;
  background-clip: text;
  background-image: repeating-linear-gradient(180deg, #ffe08a 0 2px, #f5a524 2px 4px);
  color: transparent;
  font-weight: inherit;
}

/* Only a clock for the black (see startPixels): it changes nothing itself. */
@keyframes intro-pixels {
  from {
    opacity: 1;
  }
  to {
    opacity: 1;
  }
}

@keyframes intro-slide {
  from {
    transform: translateX(calc(-50% - var(--dir) * 3.5%));
  }
  to {
    transform: translateX(calc(-50% + var(--dir) * 3.5%));
  }
}

@keyframes intro-row-on {
  from {
    opacity: 0;
    transform: scaleY(0.04);
  }
  55% {
    opacity: 1;
  }
}

@keyframes intro-row-off {
  to {
    opacity: 0;
    transform: scaleY(0.04);
  }
}

@keyframes intro-wall-out {
  to {
    opacity: 0;
    transform: scale(1.08);
  }
}

@keyframes intro-clear {
  to {
    opacity: 0;
    visibility: hidden;
  }
}
</style>
