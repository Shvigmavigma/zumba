<script setup>
// The GETPC pilot who talks a pilot out of the light theme, like a game's
// final boss. Switching from dark to light opens this scene instead
// (preferences.js): the screen dims and the ground rumbles, a framed dialog
// box rises at the bottom, the pilot climbs up behind it with a lime glow,
// gathers himself, raises both fists beside his helmet and brings them down
// on the box so hard that he and the box shake. Then he talks, one letter at
// a time, like a visual novel, nodding along, and takes a new pose after every
// answer: he unclenches his fists and holds his helmet, puts his hands on his hips, raises a fist to say
// goodbye, or pumps his fist for a pilot who backs out. Backing out leaves the
// theme alone; seeing it through switches to light, just this once (this tab)
// or for good (and then he never asks again). Esc backs out; a click on the
// box shows the whole line at once.
// He is the user's own pixel art (src/assets/pilot): torso, helmet and two
// whole arms, drawn with WebGL as one body that bends at the shoulders, elbows,
// wrists and neck without coming apart (pilotGL.js, pilotDeform.js); every
// joint follows its pose as a spring (pilotPoses.js), so he moves like a person.
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { prefersReducedMotion } from '../ui/motion/env'
import torsoUrl from '../assets/pilot/pilot-torso.webp'
import headUrl from '../assets/pilot/pilot-head.webp'
import armLUrl from '../assets/pilot/pilot-armL.webp'
import armRUrl from '../assets/pilot/pilot-armR.webp'
import armLEdgeUrl from '../assets/pilot/pilot-armL-edge.webp'
import armREdgeUrl from '../assets/pilot/pilot-armR-edge.webp'
import handLUrl from '../assets/pilot/pilot-handL.webp'
import handRUrl from '../assets/pilot/pilot-handR.webp'
import elbowUrl from '../assets/pilot/pilot-elbow.webp'
import { createPilotGL } from './pilotGL'
import { PILOT_RIG as RIG } from './pilotRig'
import { LINE_POSES, kick, liveTarget, restingAt, stepSprings, wordNod } from './pilotPoses'
import { DIALOGUE, FIRST_LINE, answer, browserStorage, stopPilotAsking, themePilot } from './themePilot'
import { switchTheme } from './preferences'

// The entrance, in ms from opening: up from below, gathering, fists up, the slam, then talk.
const CROUCH_AT_MS = 950
const WINDUP_AT_MS = 1180
const ARMS_FRONT_AT_MS = 1420
const SLAM_AT_MS = 1650
const IMPACT_AFTER_MS = 150
const TALK_AT_MS = 2050
const LETTER_MS = 28
const PUMP_MS = 1400
const GOODBYE_MS = 1300
const LIFT_MS = 300
const LEAVE_MS = 680
const MAX_SCALE = 0.9
// Room over his helmet (drawing pixels) for fists raised above it.
const HEADROOM = 150
// The jolt of the slam: the body drops and bounces, the head snaps, the forearms rebound.
const IMPACT_KICK = { y: 260, nod: 170, Le: -110, Re: 110 }

// Room either side of the drawing (its pixels) for elbows thrown wide.
const MARGIN_X = 90
// He comes up from below and goes back down: how far (drawing px) and how fast.
const RISE_AT_MS = 200
const RISE_MS = 800
const SINK_MS = 520

const SHOWN_H = RIG.edge + RIG.gloveDepth
const URLS = {
  torso: torsoUrl, head: headUrl, armL: armLUrl, armR: armRUrl,
  armLEdge: armLEdgeUrl, armREdge: armREdgeUrl, handL: handLUrl, handR: handRUrl, elbow: elbowUrl
}
const part = (name) => {
  const box = RIG.parts[name]
  return { left: `${box.x}px`, top: `${box.y}px`, width: `${box.w}px`, height: `${box.h}px` }
}
const FALLBACK = ['torso', 'head', 'armL', 'armR'].map((name) => ({ name, url: URLS[name], style: part(name) }))
const easeOut = (t) => 1 - (1 - t) ** 3
const easeIn = (t) => t * t * t

const { t } = useI18n()
const phase = ref('closed') // closed | enter | talk | leave
const line = ref(FIRST_LINE)
const typed = ref(0)
const busy = ref(false)
const scale = ref(0.6)
const reduced = ref(false)
const impact = ref(0)
const armsFront = ref(false)
const fallback = ref(false)
const canvas = ref(null)
const dialog = ref(null)
let renderer = null
let rise = { from: 0, to: 0, start: 0, ms: 1, ease: easeOut }
let outcome = null
let returnFocus = null
let timers = []
let typer = 0
let frame = 0
let openedAt = 0
let lastFrame = 0
let words = 0
let joints = restingAt('rise')
let poseName = 'rise'
let poseAt = 0
let quickness = 1

const letters = computed(() => Array.from(t(`ui.themePilot.lines.${line.value}`)))
const lineText = computed(() => letters.value.join(''))
const shownText = computed(() => letters.value.slice(0, typed.value).join(''))
const lineDone = computed(() => typed.value >= letters.value.length)
const choices = computed(() => (busy.value ? [] : DIALOGUE[line.value] || []))
const sceneStyle = computed(() => ({
  '--k': scale.value,
  '--fw': RIG.frame.w,
  '--fh': RIG.frame.h,
  '--shown': SHOWN_H,
  '--edge-y': RIG.edge,
  '--depth': `${RIG.gloveDepth * scale.value}px`,
  '--mx': MARGIN_X,
  '--headroom': HEADROOM
}))
// Lime bits knocked off the box's frame where the fists land: x in the drawing's pixels, and where each flies.
const dust = [
  [250, -60, -70], [300, -20, -95], [350, 30, -80], [215, -95, -15], [385, 70, -30],
  [690, 60, -70], [640, 20, -95], [590, -30, -80], [725, 95, -15], [555, -70, -30]
].map(([x, dx, dy], index) => ({ index, style: { '--x': x, '--dx': dx, '--dy': dy } }))

function later(ms, fn) {
  timers.push(window.setTimeout(fn, reduced.value ? 0 : ms))
}

function clearTimers() {
  timers.forEach((id) => window.clearTimeout(id))
  timers = []
  window.clearInterval(typer)
}

/** As big as the screen allows: most of its height, the box under him, room above for raised fists. */
function fitScale() {
  const tall = (window.innerHeight * 0.94 - 175) / (SHOWN_H + HEADROOM)
  const wide = (window.innerWidth - 24) / RIG.frame.w
  scale.value = Math.round(Math.max(0.25, Math.min(MAX_SCALE, tall, wide)) * 1000) / 1000
}

// ---------- Motion ----------

/** He heads for a pose; `quick` > 1 for a fast, hard move. */
function moveTo(name, quick = 1) {
  poseName = name
  poseAt = performance.now()
  quickness = quick
  if (reduced.value) joints = restingAt(name)
}

/** How far below his place he is: climbing up at the start, going down at the end. */
function riseAt(now) {
  const progress = Math.min(1, Math.max(0, (now - rise.start) / rise.ms))
  return rise.from + (rise.to - rise.from) * rise.ease(progress)
}

function draw(now) {
  if (!renderer) return
  const k = scale.value
  const pose = { rise: reduced.value ? 0 : riseAt(now) }
  for (const joint of Object.keys(joints)) pose[joint] = joints[joint].value
  renderer.draw({
    width: (RIG.frame.w + MARGIN_X * 2) * k,
    height: (HEADROOM + SHOWN_H) * k,
    dpr: Math.min(2, window.devicePixelRatio || 1),
    scale: k,
    shiftX: MARGIN_X * k,
    shiftY: HEADROOM * k,
    edge: (HEADROOM + RIG.edge) * k
  }, pose, armsFront.value)
}

function loop(now) {
  const dt = lastFrame ? Math.min(0.05, (now - lastFrame) / 1000) : 0
  lastFrame = now
  if (!reduced.value && dt > 0) joints = stepSprings(joints, liveTarget(poseName, now - openedAt, now - poseAt), dt, quickness)
  draw(now)
  frame = window.requestAnimationFrame(loop)
}

async function setUpDrawing() {
  try {
    renderer = canvas.value ? await createPilotGL(canvas.value, URLS) : null
  } catch {
    renderer = null
  }
  // Without WebGL he simply stands there, as drawn.
  if (!renderer && phase.value !== 'closed') fallback.value = true
}

// ---------- The talk ----------

function speak(next) {
  window.clearInterval(typer)
  line.value = next
  typed.value = 0
  if (reduced.value) {
    typed.value = letters.value.length
    afterLine()
    return
  }
  typer = window.setInterval(() => {
    typed.value += 1
    // A word said: he nods along.
    const letter = letters.value[typed.value - 1]
    if (typed.value === 1 || letter === ' ' || lineDone.value) {
      joints = kick(joints, wordNod(words))
      words += 1
    }
    if (lineDone.value) {
      window.clearInterval(typer)
      afterLine()
    }
  }, LETTER_MS)
}

function afterLine() {
  if (choices.value.length) {
    nextTick(() => dialog.value?.querySelector('.pilot-box__choices button')?.focus())
    return
  }
  // The goodbye has no answers: he goes, and the light theme comes.
  if (line.value === 'bye') later(GOODBYE_MS, () => leave(true))
}

/** A click on the box while he is talking shows the whole line. */
function finishLine() {
  if (phase.value !== 'talk' || lineDone.value) return
  window.clearInterval(typer)
  typed.value = letters.value.length
  afterLine()
}

function choose(choice) {
  const next = answer(line.value, choice.id)
  if (next.outcome) outcome = next.outcome
  if (!next.line) {
    // Backing out: "yes!" — a fist pump, then he goes.
    busy.value = true
    moveTo('pump', 1.25)
    later(PUMP_MS, () => leave(false))
    return
  }
  moveTo(LINE_POSES[next.line] || 'box')
  speak(next.line)
}

// ---------- Coming and going ----------

function start() {
  clearTimers()
  window.cancelAnimationFrame(frame)
  reduced.value = prefersReducedMotion()
  outcome = null
  busy.value = false
  line.value = FIRST_LINE
  typed.value = 0
  impact.value = 0
  words = 0
  returnFocus = document.activeElement
  fitScale()
  openedAt = performance.now()
  lastFrame = 0
  joints = restingAt('rise')
  armsFront.value = reduced.value
  fallback.value = false
  rise = { from: SHOWN_H + 40, to: 0, start: openedAt + RISE_AT_MS, ms: RISE_MS, ease: easeOut }
  moveTo(reduced.value ? 'box' : 'rise')
  phase.value = 'enter'
  nextTick(() => {
    setUpDrawing()
    frame = window.requestAnimationFrame(loop)
    dialog.value?.focus({ preventScroll: true })
  })
  if (!reduced.value) {
    later(CROUCH_AT_MS, () => moveTo('crouch', 1.3))
    later(WINDUP_AT_MS, () => moveTo('windup', 1.5))
    later(ARMS_FRONT_AT_MS, () => { armsFront.value = true })
    later(SLAM_AT_MS, () => moveTo('slam', 2.8))
    later(SLAM_AT_MS + IMPACT_AFTER_MS, () => {
      impact.value += 1
      joints = kick(joints, IMPACT_KICK)
      moveTo('box', 1.2)
    })
  }
  later(TALK_AT_MS, () => {
    phase.value = 'talk'
    speak(FIRST_LINE)
  })
}

function leave(apply) {
  if (phase.value === 'leave' || phase.value === 'closed') return
  clearTimers()
  busy.value = true
  // Fists off the box first, then down behind it.
  moveTo('hips', 1.3)
  later(LIFT_MS, () => {
    armsFront.value = false
    phase.value = 'leave'
    rise = { from: 0, to: SHOWN_H + 40, start: performance.now(), ms: SINK_MS, ease: easeIn }
  })
  later(LIFT_MS + LEAVE_MS, () => {
    window.cancelAnimationFrame(frame)
    renderer?.destroy()
    renderer = null
    phase.value = 'closed'
    const point = themePilot.origin
    themePilot.open = false
    returnFocus?.focus?.({ preventScroll: true })
    if (!apply) return
    if (outcome === 'forever') stopPilotAsking(browserStorage('localStorage'))
    switchTheme('light', point, { once: outcome !== 'forever' })
  })
}

// Esc backs out; Tab stays among his answers.
function onKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    leave(false)
    return
  }
  if (event.key !== 'Tab') return
  const buttons = [...(dialog.value?.querySelectorAll('button') || [])]
  event.preventDefault()
  if (!buttons.length) return
  const index = buttons.indexOf(document.activeElement)
  const step = event.shiftKey ? -1 : 1
  buttons[(index + step + buttons.length) % buttons.length].focus()
}

watch(() => themePilot.open, (open) => {
  if (open && phase.value === 'closed') start()
})

onBeforeUnmount(() => {
  clearTimers()
  window.cancelAnimationFrame(frame)
  renderer?.destroy()
})

</script>

<template>
  <Teleport to="body">
    <div v-if="phase !== 'closed'" class="pilot-scene" :class="[`is-${phase}`, { 'is-reduced': reduced }]" :style="sceneStyle" @keydown="onKeydown">
      <div class="pilot-scene__scrim" aria-hidden="true" @click="leave(false)"></div>
      <div class="pilot-scene__stage" :class="{ 'is-hit': impact > 0 }">
        <div class="pilot-scene__pilot" aria-hidden="true">
          <span class="pilot-scene__glow"></span>

          <!-- One body, drawn over the box: what stands behind it is cut at its edge. -->
          <canvas v-show="!fallback" ref="canvas" class="pilot-scene__canvas"></canvas>
          <div v-if="fallback" class="pilot-still">
            <img v-for="piece in FALLBACK" :key="piece.name" class="pilot-still__img" :src="piece.url" :style="piece.style" alt="" draggable="false" />
          </div>

          <template v-if="impact > 0">
            <span v-for="speck in dust" :key="speck.index" class="pilot-scene__dust" :style="speck.style"></span>
          </template>
        </div>

        <div class="pilot-box-wrap">
          <section
            ref="dialog"
            class="pilot-box"
            role="dialog"
            aria-modal="true"
            aria-labelledby="theme-pilot-name"
            tabindex="-1"
            @click="finishLine"
          >
            <span class="pilot-box__tick pilot-box__tick--top" aria-hidden="true"></span>
            <span class="pilot-box__tick pilot-box__tick--bottom" aria-hidden="true"></span>
            <span id="theme-pilot-name" class="pilot-box__name">{{ t('ui.themePilot.name') }}</span>
            <p class="pilot-box__line">
              <span aria-hidden="true">{{ shownText }}<i v-if="phase === 'talk' && !lineDone" class="pilot-box__caret"></i></span>
              <span v-if="phase === 'talk'" class="visually-hidden" aria-live="polite">{{ lineText }}</span>
            </p>
            <div v-if="phase === 'talk' && lineDone && choices.length" class="pilot-box__choices">
              <button
                v-for="choice in choices"
                :key="`${line}-${choice.id}`"
                class="pilot-box__choice"
                :class="{ 'is-safe': !choice.to }"
                type="button"
                @click.stop="choose(choice)"
              >
                {{ t(`ui.themePilot.choices.${choice.id}`) }}
              </button>
            </div>
            <span v-else-if="phase === 'talk' && lineDone && !busy" class="pilot-box__more" aria-hidden="true"></span>
          </section>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.pilot-scene {
  --lime: #c6f200;
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: grid;
  overflow: hidden;
}

.pilot-scene__scrim {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(70% 55% at 50% 100%, color-mix(in srgb, var(--lime) 16%, transparent), transparent 70%),
    radial-gradient(120% 90% at 50% 50%, transparent 40%, rgba(0, 0, 0, 0.5)),
    rgba(3, 5, 9, 0.84);
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
  animation: pilot-fade-in 280ms ease-out both;
}

/* Everything that shakes together: the pilot and the box. */
.pilot-scene__stage {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  align-self: end;
  justify-self: center;
  width: min(900px, 100% - 24px);
  padding-bottom: max(16px, env(safe-area-inset-bottom));
}

/* The ground rumbles while he climbs up. */
.pilot-scene.is-enter .pilot-scene__stage:not(.is-hit) {
  animation: pilot-rumble 90ms linear 200ms 9;
}

/* The slam: both of them shake. */
.pilot-scene__stage.is-hit {
  animation: pilot-hit 520ms cubic-bezier(0.2, 0.7, 0.3, 1);
}

/* ---------- The pilot ---------- */
.pilot-scene__pilot {
  position: relative;
  flex: none;
  width: calc(var(--fw) * var(--k) * 1px);
  height: calc(var(--shown) * var(--k) * 1px);
  pointer-events: none;
}

/* The canvas reaches past the pilot's box: above for raised fists, to the sides for wide elbows. */
.pilot-scene__canvas {
  position: absolute;
  z-index: 2;
  top: calc(var(--headroom) * var(--k) * -1px);
  left: calc(var(--mx) * var(--k) * -1px);
  width: calc((var(--fw) + var(--mx) * 2) * var(--k) * 1px);
  height: calc((var(--headroom) + var(--shown)) * var(--k) * 1px);
  filter: drop-shadow(0 0 calc(26px * var(--k)) color-mix(in srgb, var(--lime) 42%, transparent));
}

/* Without WebGL: the drawing as it is, standing behind the box. */
.pilot-still {
  position: absolute;
  top: 0;
  left: 0;
  width: calc(var(--fw) * 1px);
  height: calc(var(--edge-y) * 1px);
  overflow: hidden;
  transform: scale(var(--k));
  transform-origin: 0 0;
}

.pilot-still__img {
  position: absolute;
  display: block;
  max-width: none;
}

.pilot-scene__glow {
  position: absolute;
  bottom: 0;
  left: 50%;
  width: 120%;
  height: 85%;
  background: radial-gradient(closest-side, color-mix(in srgb, var(--lime) 34%, transparent), transparent);
  filter: blur(18px);
  translate: -50% 18%;
  animation:
    pilot-fade-in 800ms ease-out 250ms both,
    pilot-glow 2.4s ease-in-out 2000ms infinite;
}

.pilot-scene__dust {
  --bit: calc(10px * var(--k) + 2px);
  position: absolute;
  z-index: 3;
  top: calc(var(--edge-y) * var(--k) * 1px);
  left: calc(var(--x) * var(--k) * 1px);
  width: var(--bit);
  height: var(--bit);
  background: var(--lime);
  box-shadow: 0 0 calc(var(--bit) * 1.5) var(--lime);
  animation: pilot-dust 640ms cubic-bezier(0.2, 0.8, 0.3, 1) forwards;
}

/* ---------- The box: square, a thick frame, two corners cut ---------- */
.pilot-box-wrap {
  position: relative;
  z-index: 1;
  width: 100%;
  margin-top: calc(var(--depth) * -1);
  filter: drop-shadow(0 26px 40px rgba(0, 0, 0, 0.65)) drop-shadow(0 -6px 26px color-mix(in srgb, var(--lime) 16%, transparent));
  animation: pilot-box-in 420ms var(--ease-ios) 80ms both;
}

.pilot-box {
  --cut: 28px;
  --frame: 8px;
  position: relative;
  display: grid;
  gap: 10px;
  min-height: calc(var(--depth) + 170px);
  /* Room for the fists on the top edge. */
  padding:
    calc(var(--depth) + var(--frame) + 12px)
    calc(var(--frame) + clamp(16px, 3vw, 30px))
    calc(var(--frame) + 18px);
  background: linear-gradient(165deg, #46526a 0%, #1c2430 38%, #0c1017 100%);
  color: var(--c-text);
  outline: none;
  clip-path: polygon(var(--cut) 0, 100% 0, 100% calc(100% - var(--cut)), calc(100% - var(--cut)) 100%, 0 100%, 0 var(--cut));
}

/* A lime line along the inside of the frame... */
.pilot-box::before,
.pilot-box::after {
  position: absolute;
  z-index: 0;
  content: '';
  clip-path: polygon(var(--c) 0, 100% 0, 100% calc(100% - var(--c)), calc(100% - var(--c)) 100%, 0 100%, 0 var(--c));
}

.pilot-box::before {
  --inset: calc(var(--frame) - 2px);
  --c: calc(var(--cut) - var(--inset) * 0.586);
  inset: var(--inset);
  background: linear-gradient(90deg, var(--lime), color-mix(in srgb, var(--lime) 35%, transparent) 60%, var(--lime));
}

/* ...and the panel inside it. */
.pilot-box::after {
  --c: calc(var(--cut) - var(--frame) * 0.586);
  inset: var(--frame);
  background:
    radial-gradient(90% 120% at 0% 0%, color-mix(in srgb, var(--lime) 8%, transparent), transparent 55%),
    repeating-linear-gradient(180deg, rgba(255, 255, 255, 0.018) 0 1px, transparent 1px 3px),
    linear-gradient(180deg, #10151d, #080b10);
}

.pilot-box > * {
  position: relative;
  z-index: 1;
}

/* Marks on the frame, like a game's panel. */
.pilot-box__tick {
  position: absolute;
  z-index: 1;
  height: 3px;
  background: var(--lime);
}

.pilot-box__tick--top {
  top: 2px;
  right: 44px;
  width: 64px;
  box-shadow: -76px 0 0 color-mix(in srgb, var(--lime) 45%, transparent);
}

.pilot-box__tick--bottom {
  bottom: 2px;
  left: 44px;
  width: 64px;
  box-shadow: 76px 0 0 color-mix(in srgb, var(--lime) 45%, transparent);
}

.pilot-box__name {
  justify-self: start;
  padding: 6px 16px 6px 14px;
  background: var(--lime);
  color: #0b0d10;
  font-family: var(--font-display);
  font-size: 11.5px;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  clip-path: polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px);
}

.pilot-box__line {
  min-height: 2.9em;
  margin: 0;
  color: #f1f4f8;
  font-size: clamp(16px, 2.1vw, 20px);
  font-weight: 600;
  line-height: 1.45;
}

/* The block cursor of a line still being typed. */
.pilot-box__caret {
  display: inline-block;
  width: 0.5em;
  height: 1em;
  margin-left: 2px;
  vertical-align: -0.12em;
  background: var(--lime);
  animation: pilot-blink 700ms steps(1) infinite;
}

.pilot-box__choices {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
  animation: pilot-choices-in 260ms var(--ease-out) both;
}

/* Answers cut like the box. Backing out is the one he lights up, in the league's blue. */
.pilot-box__choice {
  min-height: 40px;
  padding: 0 20px;
  border: 0;
  background: #222a36;
  color: #e9edf3;
  cursor: pointer;
  font: inherit;
  font-size: 14px;
  font-weight: 700;
  clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
  box-shadow: inset 0 0 0 2px #3a4558;
  transition: background var(--dur-2) var(--ease-out), box-shadow var(--dur-2) var(--ease-out), transform var(--dur-2) var(--ease-out);
}

.pilot-box__choice:hover {
  background: #2c3646;
  box-shadow: inset 0 0 0 2px color-mix(in srgb, var(--lime) 60%, #3a4558);
}

.pilot-box__choice.is-safe {
  background: var(--bm-blue);
  box-shadow: inset 0 0 0 2px color-mix(in srgb, #fff 22%, var(--bm-blue));
  color: #fff;
}

.pilot-box__choice.is-safe:hover {
  background: color-mix(in srgb, #fff 10%, var(--bm-blue));
}

.pilot-box__choice:active {
  transform: translateY(1px);
}

.pilot-box__choice:focus-visible {
  outline: none;
  box-shadow: inset 0 0 0 2px var(--lime);
}

/* The goodbye has no answers: a small blinking arrow says he is done. */
.pilot-box__more {
  justify-self: end;
  width: 0;
  height: 0;
  border-top: 9px solid var(--lime);
  border-right: 7px solid transparent;
  border-left: 7px solid transparent;
  animation: pilot-blink 700ms steps(1) infinite;
}

/* ---------- Leaving ---------- */
.pilot-scene.is-leave .pilot-scene__glow {
  animation: pilot-fade-out 400ms ease-in forwards;
}

.pilot-scene.is-leave .pilot-box-wrap {
  animation: pilot-box-out 380ms ease-in 200ms forwards;
}

.pilot-scene.is-leave .pilot-scene__scrim {
  animation: pilot-fade-out 380ms ease-in 300ms forwards;
}

.pilot-scene.is-reduced,
.pilot-scene.is-reduced * {
  animation: none !important;
}

.pilot-scene.is-reduced .pilot-scene__dust {
  display: none;
}

/* ---------- Motion ---------- */
@keyframes pilot-rumble {
  0%,
  100% {
    transform: none;
  }
  25% {
    transform: translate(-1px, 1px);
  }
  75% {
    transform: translate(1px, -1px);
  }
}

@keyframes pilot-hit {
  0% {
    transform: translateY(0);
  }
  12% {
    transform: translate(-7px, 9px) rotate(-0.6deg);
  }
  28% {
    transform: translate(6px, -4px) rotate(0.5deg);
  }
  44% {
    transform: translate(-4px, 3px) rotate(-0.3deg);
  }
  62% {
    transform: translate(3px, -1px);
  }
  80% {
    transform: translate(-1px, 1px);
  }
  100% {
    transform: none;
  }
}

@keyframes pilot-box-in {
  from {
    opacity: 0;
    transform: translateY(50px);
  }
}

@keyframes pilot-box-out {
  to {
    opacity: 0;
    transform: translateY(60px);
  }
}

@keyframes pilot-dust {
  0% {
    opacity: 1;
    transform: translate(0, 0);
  }
  100% {
    opacity: 0;
    transform: translate(calc(var(--dx) * var(--k) * 1px), calc(var(--dy) * var(--k) * 1px));
  }
}

@keyframes pilot-glow {
  50% {
    opacity: 0.7;
  }
}

@keyframes pilot-fade-in {
  from {
    opacity: 0;
  }
}

@keyframes pilot-fade-out {
  to {
    opacity: 0;
  }
}

@keyframes pilot-blink {
  50% {
    opacity: 0;
  }
}

@keyframes pilot-choices-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
}
</style>
