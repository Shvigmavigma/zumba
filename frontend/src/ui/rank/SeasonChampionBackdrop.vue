<script setup>
// The season champion's own backdrop (see seasonChampion.js): a dark plate
// with the drifting title layers, a large animated "#1" behind the avatar and
// a gold rim. The title is won over a season, not earned through RER, so this
// looks nothing like the rank scenes and stays dark in both themes.
// Decorative only; place it in a positioned, rounded card.
import SeasonTitleLayers from './SeasonTitleLayers.vue'

defineProps({
  /** 'hero' for the profile banner, 'card' for licences and podium cards. */
  size: { type: String, default: 'hero' },
  /** The avatar's centre (CSS lengths): the "#1" stands behind it. */
  cx: { type: String, default: '50%' },
  cy: { type: String, default: '50%' }
})
</script>

<template>
  <div class="season" :class="`season--${size}`" :style="{ '--cx': cx, '--cy': cy }" aria-hidden="true">
    <SeasonTitleLayers :size="size" />
    <span class="season__one"><b>#1</b></span>
    <span class="season__rim season-rim"></span>
  </div>
</template>

<style scoped>
.season {
  --gold-1: #fff3c4;
  --gold-2: #f5c84c;
  --gold-3: #8a6614;
  --one-size: clamp(170px, 18vw, 230px);
  /* Where the card's text sits: the layers are dimmed there so it stays easy to read. */
  --shade-x: 36%;
  position: absolute;
  inset: 0;
  overflow: hidden;
  /* Keeps the plate's own dark surface behind the blended title layers. */
  isolation: isolate;
  border-radius: inherit;
  background:
    radial-gradient(46% 95% at var(--cx) var(--cy), rgba(245, 200, 76, 0.2), transparent 70%),
    radial-gradient(55% 80% at 100% 0%, rgba(245, 200, 76, 0.08), transparent 70%),
    linear-gradient(135deg, #111217 0%, #06070a 55%, #0b0b0e 100%);
  pointer-events: none;
}

.season--card {
  --one-size: 100px;
  --shade-x: 50%;
}

/* A soft shadow over the layers behind the card's text. */
.season::after {
  position: absolute;
  inset: 0;
  background: radial-gradient(52% 120% at var(--shade-x) 50%, rgba(6, 7, 10, 0.62), transparent 78%);
  content: '';
}

/* ---------- The #1 behind the avatar ---------- */
.season__one {
  position: absolute;
  top: var(--cy);
  left: var(--cx);
  font-family: var(--font-display);
  font-size: var(--one-size);
  font-weight: 900;
  line-height: 1;
  letter-spacing: -0.05em;
  white-space: nowrap;
  /* Above the shade: drawn after it. Centred on the avatar, a little larger than it. */
  z-index: 1;
  transform: translate(-50%, -52%) rotate(-8deg);
}

.season__one b {
  display: block;
  background: linear-gradient(105deg, var(--gold-3) 0%, var(--gold-2) 30%, var(--gold-1) 46%, var(--gold-2) 62%, var(--gold-3) 100%);
  background-size: 260% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  filter: drop-shadow(0 0 22px rgba(245, 200, 76, 0.4));
  opacity: 0.48;
  animation:
    season-one-shine 5.5s linear infinite,
    season-one-breathe 4.5s ease-in-out infinite alternate;
}

@keyframes season-one-shine {
  from {
    background-position: 130% 0;
  }
  to {
    background-position: -130% 0;
  }
}

@keyframes season-one-breathe {
  from {
    transform: scale(1);
    opacity: 0.38;
  }
  to {
    transform: scale(1.06);
    opacity: 0.6;
  }
}

/* Above the shade (the rim itself is .season-rim in ranks.css). */
.season__rim {
  z-index: 1;
}

@media (prefers-reduced-motion: reduce) {
  .season__one b {
    animation-play-state: paused;
  }
}
</style>
