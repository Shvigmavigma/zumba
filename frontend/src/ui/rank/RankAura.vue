<script setup>
// Rank finish for a pilot card or row, laid over its host (which must be
// position: relative). Rookies get nothing; bronze and silver a metal rim;
// gold a glow and a passing sheen; platinum a flowing pearl rim; diamond and
// champion a spinning prismatic rim with sparks. On the big pilot cards gold
// also gets a glint (`glint`): a highlight slides a short way along the rim
// and bursts into sparks that fly on in its direction. The season champion is
// not a rank and gets a finish of their own instead (SeasonChampionAura).
// Pure CSS, decorative only.
import { computed } from 'vue'
import { RANK_KEYS, SEASON_FINISH } from '../../ranks'
import SeasonChampionAura from './SeasonChampionAura.vue'
import { hopVars, seededRandom } from './sparks'

const props = defineProps({
  rank: { type: String, default: 'rookie' },
  /** Offsets the animations so neighbouring cards do not flash in sync. */
  seed: { type: Number, default: 0 },
  /** 'lg' for big surfaces such as the profile hero. */
  size: { type: String, default: 'md' },
  /** Gold only: a highlight slides along the rim and bursts into sparks. For the big pilot cards. */
  glint: { type: Boolean, default: false },
  /** The host is dark in both themes (licence plates), whatever the site theme. */
  onDark: { type: Boolean, default: false }
})

const SHEEN_CYCLE_S = 7
// The glint slides for the first GLINT_RUN_PART of its cycle (see the
// glint-run and glint-show keyframes), bursts there and rests for the remainder.
const GLINT_RUN_PART = 0.16
const level = computed(() => Math.max(0, RANK_KEYS.indexOf(props.rank)))
const delay = computed(() => `${-((Math.abs(props.seed) * 1.37) % SHEEN_CYCLE_S).toFixed(2)}s`)
const SPARKS = [
  { x: '10%', y: '18%', d: '0s' },
  { x: '88%', y: '26%', d: '1.4s' },
  { x: '62%', y: '86%', d: '2.5s' }
]

// Each cycle the glint starts somewhere else on the rim (--x0..5, % of its
// length), so it never bursts twice in one spot.
const glintRun = computed(() => {
  if (!props.glint || props.rank !== 'gold') return null
  const rnd = seededRandom(Math.abs(props.seed) * 104729 + 17)
  const between = (min, max) => min + rnd() * (max - min)
  const s = (value) => `${value.toFixed(2)}s`
  const isLarge = props.size === 'lg'
  const reach = isLarge ? 1 : 0.75
  const cycle = between(4.8, 7)
  const start = -between(0, cycle)
  const burst = start + cycle * GLINT_RUN_PART
  return {
    style: { ...hopVars(rnd, 0, 100), '--cycle': s(cycle), '--start': s(start), '--burst': s(burst) },
    sparks: Array.from({ length: isLarge ? 11 : 7 }, () => ({
      // The glint breaks up: its pieces fly on along the rim, fanning a little into the card.
      '--a': `${between(1, 32).toFixed(0)}deg`,
      '--fall': `${between(3, 12).toFixed(0)}deg`,
      '--dist': `${(between(34, 96) * reach).toFixed(0)}px`,
      '--len': `${(between(9, 20) * reach).toFixed(0)}px`,
      '--w': `${between(1.2, 2.2).toFixed(1)}px`,
      '--fly': s(burst + between(0, 0.08))
    }))
  }
})
</script>

<template>
  <SeasonChampionAura v-if="rank === SEASON_FINISH" :size="size" />
  <span v-else-if="level > 0" class="aura" :class="[`aura--${size}`, { 'aura--on-dark': onDark }]" :data-rank="rank" :style="{ '--aura-delay': delay }" aria-hidden="true">
    <span class="aura__rim"></span>
    <span v-if="level >= 3" class="aura__sheen"></span>
    <template v-if="level >= 5">
      <i v-for="(spark, index) in SPARKS" :key="index" class="aura__spark" :style="{ '--sx': spark.x, '--sy': spark.y, '--sd': spark.d }"></i>
    </template>
    <template v-if="glintRun">
      <span class="aura__glint-rim" :style="glintRun.style"><i class="aura__glint"></i></span>
      <i class="aura__glint-spill" :style="glintRun.style"></i>
      <span class="aura__burst" :style="glintRun.style">
        <span class="aura__burst-glow"></span>
        <i v-for="(spark, index) in glintRun.sparks" :key="index" class="aura__burst-spark" :style="spark"></i>
      </span>
    </template>
  </span>
</template>

<style scoped>
.aura {
  /* Scales the rim glint and its burst. */
  --glint-size: 0.75;
  position: absolute;
  inset: 0;
  z-index: 2;
  overflow: hidden;
  /* Hosts that cannot pass a radius by inheritance (table rows) set the variable. */
  border-radius: var(--aura-radius, inherit);
  box-shadow: inset 0 0 18px -10px var(--rank-glow);
  pointer-events: none;
}

.aura--lg {
  --glint-size: 1;
}

.aura[data-rank='gold'],
.aura[data-rank='platinum'] {
  box-shadow: inset 0 0 28px -10px var(--rank-glow);
}

.aura[data-rank='diamond'],
.aura[data-rank='champ'] {
  box-shadow: inset 0 0 34px -10px var(--rank-glow);
}

/* The rim is a gradient clipped to a thin ring along the host's border. */
.aura__rim {
  position: absolute;
  inset: 0;
  padding: 1px;
  border-radius: inherit;
  background: var(--rank-metal);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask: linear-gradient(#000 0 0) content-box exclude, linear-gradient(#000 0 0);
}

.aura--lg .aura__rim {
  padding: 1.5px;
}

.aura[data-rank='platinum'] .aura__rim {
  background: linear-gradient(120deg, var(--rank-1), var(--rank-2), #c4b5fd, var(--rank-1), var(--rank-2), var(--rank-1));
  background-size: 300% 300%;
  animation: aura-flow 6s linear infinite;
}

.aura[data-rank='diamond'] .aura__rim,
.aura[data-rank='champ'] .aura__rim {
  padding: 1.5px;
  background: conic-gradient(from var(--rank-angle), var(--rank-1), var(--rank-2), var(--rank-3), var(--rank-2), var(--rank-1));
  animation: aura-spin 6s linear infinite;
}

.aura[data-rank='champ'] .aura__rim {
  background: conic-gradient(from var(--rank-angle), #ffe08a, #ff7ad9, #b05cff, #4fd8ea, #ffe08a);
  animation-duration: 4.5s;
}

.aura--lg[data-rank='diamond'] .aura__rim,
.aura--lg[data-rank='champ'] .aura__rim {
  padding: 2px;
}

/* A band of light that crosses the card now and then. */
.aura__sheen {
  position: absolute;
  inset: -10% -40%;
  background: linear-gradient(105deg, transparent 42%, color-mix(in srgb, var(--rank-1) 20%, transparent) 50%, transparent 58%);
  mix-blend-mode: screen;
  transform: translateX(-70%);
  animation: aura-sheen 7s ease-in-out var(--aura-delay) infinite;
}

.aura__spark {
  position: absolute;
  top: var(--sy);
  left: var(--sx);
  width: 9px;
  height: 9px;
  background: var(--rank-1);
  clip-path: polygon(50% 0, 61% 39%, 100% 50%, 61% 61%, 50% 100%, 39% 61%, 0 50%, 39% 39%);
  filter: drop-shadow(0 0 5px var(--rank-glow));
  opacity: 0;
  animation: aura-twinkle 3.6s ease-in-out var(--sd) infinite;
}

/* ---------- Gold: the glint on the rim ---------- */
/* The moving pieces ride the aura's own outline (its border box with the
   rounded corners), clockwise, turned along it: their x axis is the direction
   of travel and their y axis points into the card. Browsers without box
   motion paths simply do not show them. */
.aura__glint-rim,
.aura__glint-spill,
.aura__burst {
  /* How far the glint slides before it bursts: a part of the rim plus a fixed
     stretch, so it stays short on big cards and visible on small ones. */
  --run: calc(9% + 90px * var(--glint-size));
  display: none;
}

@supports (offset-path: border-box) {
  .aura__glint-rim,
  .aura__glint-spill,
  .aura__burst {
    display: block;
  }
}

.aura__glint,
.aura__glint-spill,
.aura__burst {
  position: absolute;
  top: 0;
  left: 0;
  offset-path: border-box;
  offset-rotate: auto;
}

/* The highlight is light on the frame itself: only the rim line shows
   through this layer, and a soft spot of light slides underneath it, so the
   glint has the frame's shape (corners included) and fades out at both ends. */
.aura__glint-rim {
  position: absolute;
  inset: 0;
  padding: calc(2.5px * var(--glint-size) + 0.5px);
  border-radius: inherit;
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask: linear-gradient(#000 0 0) content-box exclude, linear-gradient(#000 0 0);
}

/* The spot of light: brightest near its front, with a longer tail behind. */
.aura__glint {
  width: calc(150px * var(--glint-size));
  height: calc(70px * var(--glint-size));
  border-radius: 50%;
  background: radial-gradient(ellipse at 72% 50%, #fff 0%, #fff3c4 20%, rgba(255, 201, 77, 0.9) 40%, rgba(250, 204, 21, 0) 72%);
  opacity: 0;
  /* The bright front rides the path. */
  offset-anchor: 72% 50%;
  transform-origin: 72% 50%;
  animation:
    glint-run calc(var(--cycle) * 6) linear var(--start) infinite,
    glint-show var(--cycle) linear var(--start) infinite;
}

/* A little of that light spills off the frame into the card. */
.aura__glint-spill {
  width: calc(96px * var(--glint-size));
  height: calc(16px * var(--glint-size));
  border-radius: 0 0 50% 50% / 0 0 100% 100%;
  background: radial-gradient(ellipse at 66% 0%, rgba(255, 236, 170, 0.36), rgba(250, 204, 21, 0.12) 45%, transparent 72%);
  opacity: 0;
  offset-anchor: 66% 0;
  transform-origin: 66% 0;
  animation:
    glint-run calc(var(--cycle) * 6) linear var(--start) infinite,
    glint-show var(--cycle) linear var(--start) infinite;
}

/* Where the glint ends its slide and breaks up. Its strength is a plain
   transform: unlike the scale property, that is applied inside the motion
   path and does not move the spot. */
.aura__burst {
  width: 0;
  height: 0;
  animation: burst-hop calc(var(--cycle) * 6) step-end var(--start) infinite;
}

/* A low bloom lying along the rim, not a ball of light. */
.aura__burst-glow {
  position: absolute;
  top: 0;
  left: calc(-36px * var(--glint-size));
  width: calc(72px * var(--glint-size));
  height: calc(18px * var(--glint-size));
  border-radius: 0 0 50% 50% / 0 0 100% 100%;
  background: radial-gradient(ellipse at 50% 0%, rgba(255, 247, 214, 0.85), rgba(250, 204, 21, 0.3) 45%, transparent 72%);
  opacity: 0;
  transform-origin: 50% 0;
  animation: burst-glow var(--cycle) linear var(--burst) infinite;
}

/* A streak lying along its flight path (it turns around the burst point). */
.aura__burst-spark {
  position: absolute;
  top: 0;
  left: 0;
  width: var(--len);
  height: var(--w);
  margin-top: calc(var(--w) / -2);
  border-radius: var(--w);
  background: linear-gradient(90deg, rgba(234, 179, 8, 0), #ffc94d 50%, #fff7d6);
  box-shadow: 0 0 7px rgba(250, 204, 21, 0.85);
  opacity: 0;
  transform-origin: 0 50%;
  animation: burst-spark var(--cycle) linear var(--fly) infinite;
}

/* On a light surface pale gold vanishes: strike the glint and its sparks in
   deeper amber. Hosts that are dark in both themes (onDark) keep the bright ones. */
:root[data-theme='light'] .aura:not(.aura--on-dark) .aura__glint {
  background: radial-gradient(ellipse at 72% 50%, #a16207 0%, #c58a04 16%, rgba(217, 154, 6, 0.85) 34%, rgba(202, 138, 4, 0) 70%);
}

:root[data-theme='light'] .aura:not(.aura--on-dark) .aura__glint-spill {
  background: radial-gradient(ellipse at 66% 0%, rgba(217, 154, 6, 0.42), rgba(234, 179, 8, 0.14) 45%, transparent 72%);
}

:root[data-theme='light'] .aura:not(.aura--on-dark) .aura__burst-glow {
  background: radial-gradient(ellipse at 50% 0%, rgba(217, 154, 6, 0.75), rgba(234, 179, 8, 0.3) 45%, transparent 72%);
}

:root[data-theme='light'] .aura:not(.aura--on-dark) .aura__burst-spark {
  background: linear-gradient(90deg, rgba(202, 138, 4, 0), #d99a06 50%, #a16207);
  box-shadow: 0 0 6px rgba(202, 138, 4, 0.55);
}

/* Six cycles, each from its own start. The slide takes the first 16% of a
   cycle, gathering speed towards the burst; the glide to the next start
   happens while the glint is invisible. */
@keyframes glint-run {
  0% {
    offset-distance: calc(var(--x0) * 1%);
    animation-timing-function: cubic-bezier(0.45, 0, 0.85, 0.7);
  }
  2.667% {
    offset-distance: calc(var(--x0) * 1% + var(--run));
  }
  16.667% {
    offset-distance: calc(var(--x1) * 1%);
    animation-timing-function: cubic-bezier(0.45, 0, 0.85, 0.7);
  }
  19.333% {
    offset-distance: calc(var(--x1) * 1% + var(--run));
  }
  33.333% {
    offset-distance: calc(var(--x2) * 1%);
    animation-timing-function: cubic-bezier(0.45, 0, 0.85, 0.7);
  }
  36% {
    offset-distance: calc(var(--x2) * 1% + var(--run));
  }
  50% {
    offset-distance: calc(var(--x3) * 1%);
    animation-timing-function: cubic-bezier(0.45, 0, 0.85, 0.7);
  }
  52.667% {
    offset-distance: calc(var(--x3) * 1% + var(--run));
  }
  66.667% {
    offset-distance: calc(var(--x4) * 1%);
    animation-timing-function: cubic-bezier(0.45, 0, 0.85, 0.7);
  }
  69.333% {
    offset-distance: calc(var(--x4) * 1% + var(--run));
  }
  83.333% {
    offset-distance: calc(var(--x5) * 1%);
    animation-timing-function: cubic-bezier(0.45, 0, 0.85, 0.7);
  }
  86% {
    offset-distance: calc(var(--x5) * 1% + var(--run));
  }
  100% {
    offset-distance: calc(var(--x0) * 1%);
  }
}

/* One cycle: the glint fades in, slides, swells where it bursts (16%) and is
   gone at once: the sparks carry on, the glint does not. */
@keyframes glint-show {
  0% {
    opacity: 0;
    transform: scale(0.6);
  }
  4% {
    opacity: 1;
    transform: scale(1);
  }
  14.5% {
    opacity: 1;
    transform: scale(1);
  }
  16% {
    opacity: 1;
    transform: scale(1.45);
  }
  17.5%,
  100% {
    opacity: 0;
    transform: scale(0.5);
  }
}

@keyframes burst-hop {
  0%,
  100% {
    offset-distance: calc(var(--x0) * 1% + var(--run));
    transform: scale(var(--k0));
  }
  16.667% {
    offset-distance: calc(var(--x1) * 1% + var(--run));
    transform: scale(var(--k1));
  }
  33.333% {
    offset-distance: calc(var(--x2) * 1% + var(--run));
    transform: scale(var(--k2));
  }
  50% {
    offset-distance: calc(var(--x3) * 1% + var(--run));
    transform: scale(var(--k3));
  }
  66.667% {
    offset-distance: calc(var(--x4) * 1% + var(--run));
    transform: scale(var(--k4));
  }
  83.333% {
    offset-distance: calc(var(--x5) * 1% + var(--run));
    transform: scale(var(--k5));
  }
}

/* Starts as the glint arrives (see --burst) and is gone within half a second. */
@keyframes burst-glow {
  0% {
    opacity: 0;
    transform: scale(0.4, 0.5);
  }
  1.5% {
    opacity: 0.9;
    transform: scale(1);
  }
  4% {
    opacity: 0.45;
  }
  6% {
    opacity: 0.65;
  }
  12%,
  100% {
    opacity: 0;
    transform: scale(1.2, 0.7);
  }
}

@keyframes burst-spark {
  0% {
    opacity: 0;
    transform: rotate(var(--a)) translateX(0) scaleX(0.4);
    animation-timing-function: cubic-bezier(0.12, 0.7, 0.3, 1);
  }
  2% {
    opacity: 1;
  }
  16%,
  100% {
    opacity: 0;
    transform: rotate(calc(var(--a) + var(--fall))) translateX(var(--dist)) scaleX(0.9);
  }
}

@keyframes aura-spin {
  to {
    --rank-angle: 360deg;
  }
}

@keyframes aura-flow {
  to {
    background-position: 300% 0;
  }
}

@keyframes aura-sheen {
  0%,
  62% {
    transform: translateX(-70%);
  }
  100% {
    transform: translateX(70%);
  }
}

@keyframes aura-twinkle {
  0%,
  68%,
  100% {
    opacity: 0;
    transform: scale(0.3) rotate(0deg);
  }
  82% {
    opacity: 0.95;
    transform: scale(1) rotate(45deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .aura__rim,
  .aura__sheen,
  .aura__spark {
    animation: none;
  }

  .aura__sheen,
  .aura__spark,
  .aura__glint-rim,
  .aura__glint-spill,
  .aura__burst {
    display: none;
  }
}
</style>
