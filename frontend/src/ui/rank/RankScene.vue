<script setup>
// A living backdrop that is different for every rank. The first three stay on
// the track and grow hotter: bronze embers drifting off hot brakes, silver
// showers of titanium sparks thrown from the floor, gold a bed of bright
// embers and glints (its sparks fly off the glint that runs along the rim, see
// RankAura). Then liquid platinum pearls, a diamond night sky with shooting
// stars and a champion's nebula with orbiting bodies and fireworks.
// Rookies get none.
// Pure CSS animation; particle layouts come from a seeded random so a card
// looks the same on every render. Decorative only.
import { computed } from 'vue'
import { hopVars, seededRandom } from './sparks'

const props = defineProps({
  rank: { type: String, default: 'rookie' },
  /** 'hero' for the profile banner, 'card' for licences (fewer, smaller). */
  size: { type: String, default: 'hero' },
  seed: { type: Number, default: 1 },
  /** Focal point (CSS length) for the champion's nebula and orbits; usually the avatar. */
  cx: { type: String, default: '' },
  cy: { type: String, default: '' },
  /** The host is dark in both themes (licence plates), whatever the site theme. */
  onDark: { type: Boolean, default: false }
})

const CENTRES = { hero: { x: 'calc(100% - 90px)', y: '50%', k: 1 }, card: { x: '78%', y: '50%', k: 0.5 } }

const centre = computed(() => {
  const base = CENTRES[props.size] || CENTRES.hero
  return { ...base, x: props.cx || base.x, y: props.cy || base.y }
})
const isCard = computed(() => props.size === 'card')

const parts = computed(() => {
  const rnd = seededRandom(props.seed * 7919 + props.rank.length * 131)
  const between = (min, max) => min + rnd() * (max - min)
  const count = (hero, card) => (isCard.value ? card : hero)
  const list = (n, make) => Array.from({ length: n }, (_, index) => make(index))
  const s = (value) => `${value.toFixed(2)}s`
  // Spark streaks are shorter on the small licence card.
  const streak = isCard.value ? 0.7 : 1
  // Emitters get clearly different periods and starting phases, so they drift
  // against each other instead of firing together.
  const cycles = (n, minDur, maxDur) =>
    list(n, (index) => {
      const dur = minDur + ((index + between(0.15, 0.85)) / n) * (maxDur - minDur)
      return { dur, delay: -dur * ((index + between(0.1, 0.9)) / n) }
    })

  switch (props.rank) {
    case 'bronze':
      return {
        embers: list(count(36, 14), () => ({
          '--x': `${between(2, 98)}%`,
          '--s': `${between(2.5, 6).toFixed(1)}px`,
          '--rise': between(55, 105).toFixed(0),
          '--sway': `${between(-40, 40).toFixed(0)}px`,
          '--a': between(0.55, 0.95).toFixed(2),
          '--dur': s(between(5, 11)),
          '--delay': s(-between(0, 11))
        }))
      }
    case 'silver': {
      // Skid-plate strikes: now and then the floor touches down somewhere and
      // throws a short cone of sparks back and up, then the emitter moves on.
      // A few cooling flecks drift up in between, so the scene never stands still.
      return {
        sprays: cycles(count(3, 2), 4.6, 7.8).map(({ dur, delay }) => ({
          // In the wide profile banner the right side lies behind the frosted
          // rating cards, so emitters keep mostly to the open part.
          // (--x0..5 are % of the scene width, read by the emitter-hop keyframes.)
          style: { ...hopVars(rnd, ...count([3, 58], [4, 66])), '--dur': s(dur), '--delay': s(delay) },
          sparks: list(count(11, 7), () => ({
            '--a': `${(-between(10, 58)).toFixed(0)}deg`,
            '--fall': `${between(5, 16).toFixed(0)}deg`,
            '--dist': between(45, 125).toFixed(0),
            '--len': `${(between(14, 34) * streak).toFixed(0)}px`,
            '--w': `${between(1.2, 2.2).toFixed(1)}px`,
            '--dur': s(dur),
            '--delay': s(delay + between(0, 0.35))
          }))
        })),
        embers: list(count(12, 5), () => ({
          '--x': `${between(2, 98)}%`,
          '--s': `${between(2, 4).toFixed(1)}px`,
          '--rise': between(45, 95).toFixed(0),
          '--sway': `${between(10, 60).toFixed(0)}px`,
          '--a': between(0.4, 0.75).toFixed(2),
          '--dur': s(between(6, 12)),
          '--delay': s(-between(0, 12))
        }))
      }
    }
    case 'gold':
      return {
        embers: list(count(16, 7), () => ({
          '--x': `${between(2, 98)}%`,
          '--s': `${between(3, 7).toFixed(1)}px`,
          '--rise': between(60, 108).toFixed(0),
          '--sway': `${between(-36, 36).toFixed(0)}px`,
          '--a': between(0.6, 0.95).toFixed(2),
          '--dur': s(between(5, 10)),
          '--delay': s(-between(0, 10))
        })),
        glints: list(count(4, 2), () => ({
          '--x': `${between(12, 96)}%`,
          '--y': `${between(10, 70)}%`,
          '--s': `${between(8, 14).toFixed(0)}px`,
          '--dur': s(between(3, 5)),
          '--delay': s(-between(0, 5))
        }))
      }
    case 'platinum':
      return {
        blobs: ['#67e8f9', '#c4b5fd', '#6ee7b7', '#e0f2fe'].slice(0, count(4, 3)).map((color) => ({
          '--c': `radial-gradient(circle at 35% 35%, ${color}, transparent 70%)`,
          '--x': `${between(8, 70)}%`,
          '--y': `${between(15, 85)}%`,
          '--s': between(240, 380).toFixed(0),
          '--dx': `${between(-120, 60).toFixed(0)}px`,
          '--dy': `${between(-60, 60).toFixed(0)}px`,
          '--dur': s(between(14, 22)),
          '--delay': s(-between(0, 22))
        })),
        pearls: list(count(10, 5), () => ({
          '--x': `${between(35, 98)}%`,
          '--y': `${between(8, 92)}%`,
          '--s': `${between(3, 7).toFixed(1)}px`,
          '--dx': `${between(-18, 18).toFixed(0)}px`,
          '--dy': `${between(-14, 14).toFixed(0)}px`,
          '--dur': s(between(5, 9)),
          '--delay': s(-between(0, 9))
        }))
      }
    case 'diamond':
      return {
        stars: list(count(72, 26), () => ({
          '--x': `${between(1, 99)}%`,
          '--y': `${between(2, 98)}%`,
          '--s': `${between(1, 2.4).toFixed(1)}px`,
          '--a': between(0.5, 1).toFixed(2),
          '--dur': s(between(2, 5)),
          '--delay': s(-between(0, 5))
        })),
        sparkles: list(count(8, 3), () => ({
          '--x': `${between(4, 97)}%`,
          '--y': `${between(8, 92)}%`,
          '--s': `${between(11, isCard.value ? 14 : 22).toFixed(0)}px`,
          '--dur': s(between(3, 6)),
          '--delay': s(-between(0, 6))
        })),
        comets: list(count(4, 1), () => ({
          '--x': `${between(55, 100)}%`,
          '--y': `${between(-5, 35)}%`,
          '--dur': s(between(7, 12)),
          '--delay': s(between(0, 8))
        }))
      }
    case 'champ': {
      const colors = ['#ffe08a', '#ff7ad9', '#4fd8ea']
      return {
        orbits: [
          { d: 220, tilt: -18, dur: 6, c: '#ffe08a' },
          { d: 300, tilt: 24, dur: 9, c: '#ff7ad9' },
          { d: 380, tilt: -36, dur: 13, c: '#4fd8ea' }
        ].slice(0, count(3, 2)).map((orbit) => ({
          '--d': orbit.d,
          '--tilt': `${orbit.tilt}deg`,
          '--dur': `${orbit.dur}s`,
          '--delay': s(-between(0, orbit.dur)),
          '--c': orbit.c
        })),
        bursts: list(count(3, 1), (index) => ({
          style: {
            '--bx': `calc(${centre.value.x} + ${(between(60, 420) * centre.value.k).toFixed(0)}px)`,
            '--by': `${between(18, 82).toFixed(0)}%`
          },
          sparks: list(12, (spark) => ({
            '--a': `${spark * 30 + between(-8, 8)}deg`,
            '--r': (between(60, 110) * centre.value.k).toFixed(0),
            '--c': colors[spark % colors.length],
            '--dur': '5s',
            '--delay': `${index * 1.7}s`
          }))
        }))
      }
    }
    default:
      return {}
  }
})
</script>

<template>
  <div
    v-if="rank !== 'rookie'"
    class="scene"
    :class="[`scene--${size}`, { 'scene--on-dark': onDark }]"
    :data-rank="rank"
    :style="{ '--cx': centre.x, '--cy': centre.y, '--k': centre.k }"
    aria-hidden="true"
  >
    <!-- Bronze: embers off hot brakes. -->
    <template v-if="rank === 'bronze'">
      <span class="heat"></span>
      <i v-for="(item, index) in parts.embers" :key="index" class="ember" :style="item"></i>
    </template>

    <!-- Silver: titanium sparks thrown from the floor. -->
    <template v-else-if="rank === 'silver'">
      <span class="heat"></span>
      <span v-for="(spray, index) in parts.sprays" :key="index" class="spray" :style="spray.style">
        <span class="spray__flash"></span>
        <i v-for="(spark, sparkIndex) in spray.sparks" :key="sparkIndex" class="spark" :style="spark"></i>
      </span>
      <i v-for="(item, index) in parts.embers" :key="`e${index}`" class="ember" :style="item"></i>
    </template>

    <!-- Gold: a bed of embers and glints. -->
    <template v-else-if="rank === 'gold'">
      <span class="heat"></span>
      <i v-for="(item, index) in parts.embers" :key="`e${index}`" class="ember" :style="item"></i>
      <i v-for="(item, index) in parts.glints" :key="`g${index}`" class="glint" :style="item"></i>
    </template>

    <!-- Platinum: liquid pearl. -->
    <template v-else-if="rank === 'platinum'">
      <i v-for="(item, index) in parts.blobs" :key="`l${index}`" class="blob" :style="item"></i>
      <i v-for="(item, index) in parts.pearls" :key="`p${index}`" class="pearl" :style="item"></i>
    </template>

    <!-- Diamond: a clear night sky. -->
    <template v-else-if="rank === 'diamond'">
      <i v-for="(item, index) in parts.stars" :key="`s${index}`" class="star" :style="item"></i>
      <i v-for="(item, index) in parts.sparkles" :key="`k${index}`" class="sparkle" :style="item"></i>
      <i v-for="(item, index) in parts.comets" :key="`c${index}`" class="comet" :style="item"></i>
    </template>

    <!-- Champion: nebula, orbits and fireworks around the crest. -->
    <template v-else-if="rank === 'champ'">
      <span class="nebula"></span>
      <span v-for="(item, index) in parts.orbits" :key="`o${index}`" class="orbit" :style="item">
        <span class="orbit__ring"></span>
        <span class="orbit__spin"><i class="orbit__body"></i></span>
      </span>
      <span v-for="(burst, index) in parts.bursts" :key="`f${index}`" class="burst" :style="burst.style">
        <i v-for="(spark, sparkIndex) in burst.sparks" :key="sparkIndex" class="burst__spark" :style="spark"></i>
      </span>
    </template>
  </div>
</template>

<style scoped>
.scene {
  position: absolute;
  inset: 0;
  overflow: hidden;
  border-radius: inherit;
  pointer-events: none;
  /* Lets particles travel in cqh/cqw: fractions of the scene, not of themselves. */
  container-type: size;
}

.scene i {
  position: absolute;
  display: block;
}

/* ---------- Bronze: embers ---------- */
/* Glow off the track surface; silver and gold recolour it. */
.heat {
  position: absolute;
  right: 0;
  bottom: -35%;
  left: 0;
  height: 70%;
  background: radial-gradient(60% 60% at 30% 100%, rgba(255, 122, 30, 0.3), transparent 70%);
  animation: heat 4s ease-in-out infinite alternate;
}

.scene[data-rank='silver'] .heat {
  background: radial-gradient(70% 55% at 34% 100%, rgba(203, 213, 225, 0.22), transparent 70%);
}

.scene[data-rank='gold'] .heat {
  bottom: -40%;
  height: 95%;
  background: radial-gradient(75% 62% at 50% 100%, rgba(250, 190, 40, 0.34), transparent 72%);
  animation-duration: 2.6s;
}

.ember {
  bottom: -12px;
  left: var(--x);
  width: var(--s);
  height: var(--s);
  border-radius: 50%;
  background: radial-gradient(circle, #fff4d6 0 22%, #ffb057 48%, rgba(197, 106, 32, 0) 72%);
  filter: drop-shadow(0 0 4px rgba(255, 140, 40, 0.85));
  opacity: 0;
  animation: ember-rise var(--dur) linear var(--delay) infinite;
}

/* Cooling flecks between silver showers, a bed of bright embers for gold. */
.scene[data-rank='silver'] .ember {
  background: radial-gradient(circle, #fff 0 24%, #cbd5e1 50%, rgba(148, 163, 184, 0) 72%);
  filter: drop-shadow(0 0 4px rgba(226, 232, 240, 0.8));
}

.scene[data-rank='gold'] .ember {
  background: radial-gradient(circle, #fffbe6 0 22%, #ffd24d 48%, rgba(234, 179, 8, 0) 72%);
  filter: drop-shadow(0 0 5px rgba(250, 204, 21, 0.9));
}

@keyframes heat {
  to {
    opacity: 0.6;
  }
}

@keyframes ember-rise {
  0% {
    opacity: 0;
    transform: translate3d(0, 0, 0) scale(1);
  }
  12% {
    opacity: var(--a);
  }
  45% {
    transform: translate3d(var(--sway), calc(var(--rise) * -0.45cqh), 0) scale(0.9);
  }
  78% {
    opacity: calc(var(--a) * 0.6);
  }
  100% {
    opacity: 0;
    transform: translate3d(calc(var(--sway) * -0.5), calc(var(--rise) * -1cqh), 0) scale(0.35);
  }
}

/* ---------- Silver: titanium sparks ---------- */
/* An emitter is a point on the floor. It never fires twice from one spot:
   while it rests it hops to its next place (--x0..5, % of the scene width)
   and changes strength (--k0..5). A spark is a streak lying along its flight
   path (it turns around the emitter), bright head first. */
.spray {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 0;
  animation: emitter-hop calc(var(--dur) * 6) step-end var(--delay) infinite;
}

.spark {
  top: 0;
  left: 0;
  width: var(--len);
  height: var(--w);
  margin-top: calc(var(--w) / -2);
  border-radius: var(--w);
  background: linear-gradient(90deg, rgba(148, 163, 184, 0), rgba(226, 232, 240, 0.8) 55%, #fff);
  box-shadow: 0 0 6px rgba(226, 232, 240, 0.75);
  opacity: 0;
  transform-origin: 0 50%;
  animation: spark-fly var(--dur) linear var(--delay) infinite;
}

/* One step per shower cycle; the jump lands while every spark is invisible. */
@keyframes emitter-hop {
  0%,
  100% {
    transform: translateX(calc(var(--x0) * 1cqw)) scale(var(--k0));
  }
  16.667% {
    transform: translateX(calc(var(--x1) * 1cqw)) scale(var(--k1));
  }
  33.333% {
    transform: translateX(calc(var(--x2) * 1cqw)) scale(var(--k2));
  }
  50% {
    transform: translateX(calc(var(--x3) * 1cqw)) scale(var(--k3));
  }
  66.667% {
    transform: translateX(calc(var(--x4) * 1cqw)) scale(var(--k4));
  }
  83.333% {
    transform: translateX(calc(var(--x5) * 1cqw)) scale(var(--k5));
  }
}

/* Where the floor touches down: a low glint lying on the track, gone in a blink. */
.spray__flash {
  position: absolute;
  bottom: 0;
  left: calc(-30px * var(--k));
  width: calc(60px * var(--k));
  height: calc(11px * var(--k));
  border-radius: 50% 50% 0 0 / 100% 100% 0 0;
  background: radial-gradient(ellipse at 50% 100%, rgba(255, 255, 255, 0.75), rgba(203, 213, 225, 0.26) 45%, transparent 72%);
  opacity: 0;
  transform-origin: 50% 100%;
  animation: spray-flash var(--dur) linear var(--delay) infinite;
}

/* The shower takes about a second at the start of the cycle; the emitter rests for the remainder. */
@keyframes spark-fly {
  0% {
    opacity: 0;
    transform: rotate(var(--a)) translateX(0) scaleX(0.4);
    animation-timing-function: cubic-bezier(0.12, 0.7, 0.3, 1);
  }
  2.5% {
    opacity: 1;
  }
  18%,
  100% {
    opacity: 0;
    transform: rotate(calc(var(--a) + var(--fall))) translateX(calc(var(--dist) * 1cqh)) scaleX(1);
  }
}

@keyframes spray-flash {
  0% {
    opacity: 0;
    transform: scale(0.3, 0.6);
  }
  1.5% {
    opacity: 0.85;
    transform: scale(1);
  }
  4% {
    opacity: 0.35;
  }
  6% {
    opacity: 0.6;
  }
  12%,
  100% {
    opacity: 0;
    transform: scale(1.25, 0.7);
  }
}

/* ---------- Gold: glints ---------- */
.glint {
  top: var(--y);
  left: var(--x);
  width: var(--s);
  height: var(--s);
  background: #fff3b8;
  clip-path: polygon(50% 0, 61% 39%, 100% 50%, 61% 61%, 50% 100%, 39% 61%, 0 50%, 39% 39%);
  filter: drop-shadow(0 0 6px rgba(234, 179, 8, 0.9));
  animation: twinkle var(--dur) ease-in-out var(--delay) infinite;
}

/* On a light surface white-hot sparks vanish: strike them in darker metal.
   Hosts that are dark in both themes (onDark) keep the bright ones. */
:root[data-theme='light'] .scene:not(.scene--on-dark) .spark {
  background: linear-gradient(90deg, rgba(100, 116, 139, 0), rgba(100, 116, 139, 0.75) 55%, #475569);
  box-shadow: 0 0 5px rgba(100, 116, 139, 0.4);
}

:root[data-theme='light'] .scene[data-rank='silver']:not(.scene--on-dark) .ember {
  background: radial-gradient(circle, #64748b 0 30%, rgba(100, 116, 139, 0.5) 55%, rgba(100, 116, 139, 0) 72%);
  filter: none;
}

/* ---------- Platinum: liquid pearl ---------- */
.blob {
  top: var(--y);
  left: var(--x);
  width: calc(var(--s) * var(--k) * 1px);
  aspect-ratio: 1;
  border-radius: 42% 58% 63% 37% / 41% 44% 56% 59%;
  background: var(--c);
  filter: blur(calc(24px * var(--k)));
  mix-blend-mode: screen;
  opacity: 0.46;
  transform: translate(-50%, -50%);
  animation:
    blob-move var(--dur) ease-in-out var(--delay) infinite alternate,
    blob-morph calc(var(--dur) * 0.6) ease-in-out var(--delay) infinite alternate;
}

.pearl {
  top: var(--y);
  left: var(--x);
  width: var(--s);
  height: var(--s);
  border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, #fff 0 25%, #a5f3fc 60%, rgba(196, 181, 253, 0.6));
  box-shadow: 0 0 8px rgba(165, 243, 252, 0.7);
  opacity: 0.75;
  animation: pearl-float var(--dur) ease-in-out var(--delay) infinite alternate;
}

@keyframes blob-move {
  to {
    transform: translate(calc(-50% + var(--dx)), calc(-50% + var(--dy))) rotate(160deg);
  }
}

@keyframes blob-morph {
  50% {
    border-radius: 63% 37% 42% 58% / 55% 38% 62% 45%;
  }
  100% {
    border-radius: 38% 62% 50% 50% / 60% 52% 48% 40%;
  }
}

@keyframes pearl-float {
  to {
    opacity: 0.35;
    transform: translate3d(var(--dx), var(--dy), 0);
  }
}

/* ---------- Diamond: night sky ---------- */
.star {
  top: var(--y);
  left: var(--x);
  width: var(--s);
  height: var(--s);
  border-radius: 50%;
  background: #e0e7ff;
  box-shadow: 0 0 6px rgba(165, 180, 252, 0.9);
  opacity: 0.2;
  animation: star-twinkle var(--dur) ease-in-out var(--delay) infinite;
}

.sparkle {
  top: var(--y);
  left: var(--x);
  width: var(--s);
  height: var(--s);
  background: linear-gradient(135deg, #fff, #93c5fd, #c084fc);
  clip-path: polygon(50% 0, 61% 39%, 100% 50%, 61% 61%, 50% 100%, 39% 61%, 0 50%, 39% 39%);
  filter: drop-shadow(0 0 6px rgba(147, 197, 253, 0.95));
  animation: sparkle-turn var(--dur) ease-in-out var(--delay) infinite;
}

/* A short streak with a bright head, crossing now and then. */
.comet {
  top: var(--y);
  left: var(--x);
  width: calc(150px * var(--k));
  height: 1.5px;
  border-radius: 2px;
  background: linear-gradient(90deg, transparent, rgba(199, 210, 254, 0.95));
  box-shadow: 0 0 6px rgba(165, 180, 252, 0.8);
  opacity: 0;
  transform-origin: right center;
  animation: comet-fly var(--dur) linear var(--delay) infinite;
}

@keyframes star-twinkle {
  50% {
    opacity: var(--a);
    transform: scale(1.5);
  }
}

@keyframes sparkle-turn {
  0%,
  100% {
    opacity: 0.2;
    transform: scale(0.4) rotate(0deg);
  }
  50% {
    opacity: 0.95;
    transform: scale(1) rotate(90deg);
  }
}

@keyframes comet-fly {
  0% {
    opacity: 0;
    transform: rotate(150deg) translateX(0);
  }
  2% {
    opacity: 1;
  }
  11% {
    opacity: 0;
    transform: rotate(150deg) translateX(65cqw);
  }
  100% {
    opacity: 0;
    transform: rotate(150deg) translateX(65cqw);
  }
}

/* ---------- Champion: nebula, orbits, fireworks ---------- */
.nebula {
  position: absolute;
  top: var(--cy);
  left: var(--cx);
  width: calc(600px * var(--k));
  aspect-ratio: 1;
  border-radius: 50%;
  background: conic-gradient(from 0deg, rgba(176, 92, 255, 0.55), rgba(255, 122, 217, 0.42), rgba(255, 224, 138, 0.36), rgba(79, 216, 234, 0.42), rgba(176, 92, 255, 0.55));
  filter: blur(calc(34px * var(--k)));
  opacity: 0.78;
  transform: translate(-50%, -50%);
  -webkit-mask: radial-gradient(circle, #000 22%, transparent 68%);
  mask: radial-gradient(circle, #000 22%, transparent 68%);
  animation: nebula-spin 30s linear infinite;
}

/* Tilted orbits: a circle squashed into an ellipse, a body riding its edge. */
.orbit {
  position: absolute;
  top: var(--cy);
  left: var(--cx);
  width: calc(var(--d) * var(--k) * 1px);
  aspect-ratio: 1;
  transform: translate(-50%, -50%) rotate(var(--tilt)) scaleY(0.34);
}

.orbit__ring,
.orbit__spin {
  position: absolute;
  inset: 0;
  border-radius: 50%;
}

.orbit__ring {
  border: 1.5px solid rgba(255, 224, 138, 0.36);
  box-shadow: 0 0 12px rgba(176, 92, 255, 0.35);
}

.orbit__spin {
  animation: nebula-spin-plain var(--dur) linear var(--delay) infinite;
}

.orbit__body {
  top: 0;
  left: 50%;
  width: 12px;
  height: 12px;
  margin: -6px 0 0 -6px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 0 10px 3px var(--c), 0 0 26px 8px var(--c);
}

.burst {
  position: absolute;
  top: var(--by);
  left: var(--bx);
}

.burst__spark {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--c);
  box-shadow: 0 0 10px 2px var(--c);
  opacity: 0;
  animation: burst-fly var(--dur) ease-out var(--delay) infinite;
}

@keyframes nebula-spin {
  to {
    transform: translate(-50%, -50%) rotate(360deg);
  }
}

@keyframes nebula-spin-plain {
  to {
    transform: rotate(360deg);
  }
}

@keyframes burst-fly {
  0% {
    opacity: 0;
    transform: rotate(var(--a)) translateX(0) scale(1);
  }
  3% {
    opacity: 1;
  }
  32% {
    opacity: 0;
    transform: rotate(var(--a)) translateX(calc(var(--r) * 1px)) scale(0.5);
  }
  100% {
    opacity: 0;
    transform: rotate(var(--a)) translateX(calc(var(--r) * 1px)) scale(0.5);
  }
}

@keyframes twinkle {
  0%,
  100% {
    opacity: 0;
    transform: scale(0.3) rotate(0deg);
  }
  50% {
    opacity: 0.95;
    transform: scale(1) rotate(45deg);
  }
}

/* Licences are small: keep the scene a quiet backdrop behind the foil. */
.scene--card {
  opacity: 0.75;
}

@media (prefers-reduced-motion: reduce) {
  .scene *,
  .scene i {
    animation: none !important;
  }

  .ember,
  .spray,
  .comet,
  .burst {
    display: none;
  }
}
</style>
