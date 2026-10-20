<script setup>
// 3D layout of a circuit, drawn as SVG from the track's centre line: the road in
// perspective, numbered corners that name themselves, DRS zones and a light
// running the lap. It can be dragged round; left alone it turns slowly.
// Given `sectors`, each timing sector of the lap is painted in its own colour
// (say, of the pilot who holds it) and gets a mark, filled through the
// `sector` slot; `activeSector` lights one of them up. A `start` slot puts a
// mark by the start line (say, for the holder of the lap record).
// No dependencies but Vue. Colours come from the design tokens (--bm-*, --c-*)
// and fall back to the dark theme's values where the tokens are not defined.
import { computed, onBeforeUnmount, onMounted, ref, useId, useSlots, watch } from 'vue'
import { buildTrack, declutter, distanceAt, fitTable, sceneAt } from './trackLayout3d.js'

const VIEW = { width: 960, height: 540, padding: 44 }
const DEG = Math.PI / 180
const FOCAL = 1500
const PITCH_LIMITS = [30, 84]
const TURN_PER_SECOND = 7 // degrees, when it turns by itself
const DRAW_SECONDS = 2.6
const LAP_SECONDS = 16
const RESUME_AFTER = 2500 // ms after the last drag before it turns by itself again
const DRAG_YAW = 0.35 // degrees per px
const DRAG_PITCH = 0.25
const KEY_STEP = 6
const LONGEST_FRAME = 0.1 // seconds: after a stall the animation carries on, it does not jump
const COMPACT_BELOW = 520 // px of the component's own width: phones and narrow columns
const MARK_SIZE = { regular: 30, compact: 23 } // px a corner mark needs, with a little air round it
const SECTOR_MARK_ROOM = 1.25

const props = defineProps({
  /** Track data: { name, points, corners?, zones?, yaw? } — see tracks/silverstone.js. */
  track: { type: Object, required: true },
  /** Turn slowly while nobody is dragging or reading a corner. */
  autoRotate: { type: Boolean, default: true },
  /** Let the visitor drag it round (and use the arrow keys when it has focus). */
  interactive: { type: Boolean, default: true },
  /** A light running the lap. */
  lapLight: { type: Boolean, default: true },
  /** Draw the lap in when it first comes into view; off, the layout is simply there. */
  drawIn: { type: Boolean, default: true },
  showZones: { type: Boolean, default: true },
  showGrid: { type: Boolean, default: true },
  /** Angle of the camera below the horizon at rest, degrees: 90 is a plan view. */
  pitch: { type: Number, default: 58 },
  /** Accessible name of the whole figure; by default it is made from the track's name. */
  label: { type: String, default: '' },
  /** Word before a corner's number in its accessible name. */
  cornerWord: { type: String, default: 'Поворот' },
  /** Hint shown until the first drag. */
  hint: { type: String, default: 'Потяните, чтобы повернуть' },
  /**
   * How to paint the lap's timing sectors, in order: [{ color }] or null for a sector left as it is.
   * Needs `sectorLines` in the track data; an empty list draws the plain layout.
   */
  sectors: { type: Array, default: () => [] },
  /** Number of the sector that is lit up (v-model:active-sector), or null. */
  activeSector: { type: Number, default: null },
  /** Colour of the light running the lap; by default the theme's own. */
  lightColor: { type: String, default: '' }
})
const emit = defineEmits(['select', 'update:activeSector'])
const slots = useSlots()

const stage = ref(null)
const fadeId = useId()
const maskId = useId()
const yaw = ref(props.track.yaw ?? 90)
const pitch = ref(props.pitch)
const reducedMotion = typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches
const drawn = ref(props.drawIn && !reducedMotion ? 0 : 1)
const lightAt = ref(0)
const active = ref(null)
const dragging = ref(false)
const touched = ref(false)
const width = ref(VIEW.width)

let frame = 0
let lastTick = 0
let idleSince = 0
let visible = false
let observer = null
let resizer = null
let drag = null

const model = computed(() => buildTrack(props.track))
/** Fit tables by whole degree of tilt, worked out the first time the track is seen at that tilt. */
const fits = computed(() => ({ track: model.value, byPitch: new Map() }))

function distanceFor(yawDegrees, pitchDegrees) {
  const key = Math.round(pitchDegrees)
  const cache = fits.value.byPitch
  if (!cache.has(key)) cache.set(key, fitTable(model.value, VIEW, key * DEG, FOCAL))
  return distanceAt(cache.get(key), yawDegrees * DEG)
}

function easeInOut(k) {
  return k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2
}

const scene = computed(() =>
  sceneAt(
    model.value,
    VIEW,
    { yaw: yaw.value * DEG, pitch: pitch.value * DEG, distance: distanceFor(yaw.value, pitch.value), focal: FOCAL },
    { progress: easeInOut(drawn.value), lightAt: props.lapLight ? lightAt.value : null, grid: props.showGrid, zones: props.showZones, sectors: props.sectors.length > 0, startMark: Boolean(slots.start) }
  )
)

const compact = computed(() => width.value < COMPACT_BELOW)
/** How far apart two marks must be, in the drawing's own px: the marks do not shrink with the drawing. */
const markSpacing = computed(() => ((compact.value ? MARK_SIZE.compact : MARK_SIZE.regular) * VIEW.width) / width.value)

/** Sectors with their colours; a sector nobody holds keeps the plain road. */
const paintedSectors = computed(() => scene.value.sectors.map((sector) => ({ ...sector, color: props.sectors[sector.n - 1]?.color || '' })))
/** Every sector has a colour: the plain road and its edge are not needed under them. */
const fullyPainted = computed(() => paintedSectors.value.length > 0 && paintedSectors.value.every((sector) => sector.color))

/**
 * Corner and sector marks, moved apart together so that neither covers the other,
 * far ones first so near ones sit on top.
 */
const placedMarks = computed(() => {
  const corners = scene.value.corners.map((corner) => ({ ...corner, kind: 'corner' }))
  const sectors = paintedSectors.value
    .filter((sector) => sector.mark && sector.color)
    .map((sector) => ({ ...sector.mark, n: sector.n, color: sector.color, kind: 'sector' }))
  const start = scene.value.startMark ? [{ ...scene.value.startMark, n: 0, kind: 'start' }] : []
  // A sector mark carries a picture: with them on the drawing everything needs a little more room.
  const spacing = markSpacing.value * (sectors.length || start.length ? SECTOR_MARK_ROOM : 1)
  return declutter([...corners, ...sectors, ...start], spacing)
    .sort((a, b) => b.depth - a.depth)
    .map((mark) => ({
      ...mark,
      left: `${(mark.markX / VIEW.width) * 100}%`,
      top: `${(mark.markY / VIEW.height) * 100}%`,
      leader: `M${mark.x} ${mark.y}L${mark.markX} ${mark.markY}`
    }))
})
const marks = computed(() => placedMarks.value.filter((mark) => mark.kind === 'corner'))
const sectorMarks = computed(() => placedMarks.value.filter((mark) => mark.kind === 'sector'))
const startMark = computed(() => placedMarks.value.find((mark) => mark.kind === 'start') || null)
const leaders = computed(() => placedMarks.value.map((mark) => mark.leader).join(''))
const figureLabel = computed(() => props.label || `Схема трассы ${props.track.name ?? ''}`.trim())

function clamp(value, low, high) {
  return Math.min(high, Math.max(low, value))
}

function moves() {
  return visible && !reducedMotion && (drawn.value < 1 || props.lapLight || props.autoRotate)
}

function tick(now) {
  const seconds = Math.min(LONGEST_FRAME, (now - lastTick) / 1000)
  lastTick = now
  if (drawn.value < 1) {
    drawn.value = Math.min(1, drawn.value + seconds / DRAW_SECONDS)
  } else if (props.lapLight) {
    lightAt.value = (lightAt.value + (model.value.length / LAP_SECONDS) * seconds) % model.value.length
  }
  const resting = !dragging.value && active.value === null && props.activeSector === null && now - idleSince > RESUME_AFTER
  if (props.autoRotate && resting && drawn.value >= 1) yaw.value = (yaw.value + TURN_PER_SECOND * seconds) % 360
  frame = moves() ? requestAnimationFrame(tick) : 0
}

function wake() {
  if (frame || !moves()) return
  lastTick = performance.now()
  frame = requestAnimationFrame(tick)
}

function onPointerDown(event) {
  if (!props.interactive || event.button > 0 || event.target.closest('button')) return
  drag = { x: event.clientX, y: event.clientY, yaw: yaw.value, pitch: pitch.value, touch: event.pointerType === 'touch' }
  dragging.value = true
  touched.value = true
  stage.value.setPointerCapture(event.pointerId)
}

function onPointerMove(event) {
  if (!drag) return
  yaw.value = drag.yaw + (event.clientX - drag.x) * DRAG_YAW
  // On a touch screen a vertical swipe scrolls the page, so there only the turn follows the finger.
  if (!drag.touch) pitch.value = clamp(drag.pitch + (event.clientY - drag.y) * DRAG_PITCH, PITCH_LIMITS[0], PITCH_LIMITS[1])
}

function onPointerUp(event) {
  if (!drag) return
  drag = null
  dragging.value = false
  idleSince = performance.now()
  if (stage.value.hasPointerCapture(event.pointerId)) stage.value.releasePointerCapture(event.pointerId)
}

function onKeydown(event) {
  if (!props.interactive || event.target !== stage.value) return
  const turns = { ArrowLeft: [-KEY_STEP, 0], ArrowRight: [KEY_STEP, 0], ArrowUp: [0, KEY_STEP], ArrowDown: [0, -KEY_STEP] }[event.key]
  if (!turns) return
  event.preventDefault()
  yaw.value += turns[0]
  pitch.value = clamp(pitch.value + turns[1], PITCH_LIMITS[0], PITCH_LIMITS[1])
  idleSince = performance.now()
  touched.value = true
}

function choose(corner) {
  active.value = corner.n
  emit('select', { n: corner.n, name: corner.name })
}

function release(corner) {
  if (active.value === corner.n) active.value = null
  idleSince = performance.now()
}

function lightSector(n) {
  if (props.activeSector !== n) emit('update:activeSector', n)
}

function dimSector(n) {
  if (props.activeSector === n) emit('update:activeSector', null)
  idleSince = performance.now()
}

watch(model, () => {
  yaw.value = props.track.yaw ?? 90
  drawn.value = props.drawIn && !reducedMotion ? 0 : 1
  lightAt.value = 0
  active.value = null
  wake()
})
watch(() => [props.autoRotate, props.lapLight], wake)
// A sector let go from outside (the page's own list) starts the idle clock too.
watch(() => props.activeSector, (n) => {
  if (n === null) idleSince = performance.now()
})

onMounted(() => {
  observer = new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting
    wake()
  }, { threshold: 0.15 })
  observer.observe(stage.value)
  // Measured at once so the first paint already has its marks spaced for this width.
  if (stage.value.clientWidth > 0) width.value = stage.value.clientWidth
  resizer = new ResizeObserver(([entry]) => {
    if (entry.contentRect.width > 0) width.value = entry.contentRect.width
  })
  resizer.observe(stage.value)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  resizer?.disconnect()
  if (frame) cancelAnimationFrame(frame)
  frame = 0
})
</script>

<template>
  <div
    ref="stage"
    class="track3d"
    :class="{ 'is-dragging': dragging, 'is-interactive': interactive, 'is-compact': compact, 'has-active-sector': activeSector !== null }"
    role="group"
    :aria-label="figureLabel"
    :tabindex="interactive ? 0 : undefined"
    :style="{ aspectRatio: `${VIEW.width} / ${VIEW.height}`, '--t3-light': lightColor || undefined }"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointercancel="onPointerUp"
    @keydown="onKeydown"
  >
    <svg class="track3d__svg" :viewBox="`0 0 ${VIEW.width} ${VIEW.height}`" aria-hidden="true">
      <defs>
        <radialGradient :id="fadeId" cx="50%" cy="50%" r="60%">
          <stop offset="0.45" stop-color="#fff" />
          <stop offset="1" stop-color="#fff" stop-opacity="0" />
        </radialGradient>
        <mask :id="maskId">
          <rect :width="VIEW.width" :height="VIEW.height" :fill="`url(#${fadeId})`" />
        </mask>
      </defs>
      <path class="track3d__grid" :d="scene.grid" :mask="`url(#${maskId})`" />
      <template v-if="!fullyPainted">
        <path class="track3d__glow" :d="scene.glow" />
        <path class="track3d__edge" :d="scene.edge" />
        <path class="track3d__road" :d="scene.road" />
      </template>
      <template v-for="sector in paintedSectors" :key="`glow-${sector.n}`">
        <path v-if="sector.color" class="track3d__sector-glow" :class="{ 'is-active': activeSector === sector.n }" :style="{ '--sector': sector.color }" :d="sector.glow" />
      </template>
      <template v-for="sector in paintedSectors" :key="`road-${sector.n}`">
        <path
          v-if="sector.color"
          class="track3d__sector-road"
          :class="{ 'is-active': activeSector === sector.n }"
          :style="{ '--sector': sector.color }"
          :d="sector.road"
          @pointerenter="lightSector(sector.n)"
          @pointerleave="dimSector(sector.n)"
        />
      </template>
      <path class="track3d__dashes" :d="scene.dashes" />
      <path class="track3d__zones" :d="scene.zones" />
      <path class="track3d__start" :d="scene.start" />
      <path v-for="sector in paintedSectors" :key="`line-${sector.n}`" class="track3d__sector-line" :d="sector.line" />
      <path class="track3d__tail" :d="scene.lightTail" />
      <circle v-if="scene.light" class="track3d__light" :cx="scene.light.x" :cy="scene.light.y" r="6" />
      <path class="track3d__leaders" :d="leaders" />
    </svg>

    <button
      v-for="mark in marks"
      :key="mark.n"
      type="button"
      class="track3d__corner"
      :class="{ 'is-active': active === mark.n }"
      :style="{ left: mark.left, top: mark.top }"
      :aria-label="mark.name ? `${cornerWord} ${mark.n}, ${mark.name}` : `${cornerWord} ${mark.n}`"
      @pointerenter="active = mark.n"
      @pointerleave="release(mark)"
      @focus="active = mark.n"
      @blur="release(mark)"
      @click="choose(mark)"
    >
      <span class="track3d__number">{{ mark.n }}</span>
      <!-- A turn the circuit gives no name to still answers, with its plain number. -->
      <span v-if="active === mark.n" class="track3d__name" :class="{ 'is-plain': !mark.name }">{{ mark.name || `${cornerWord} ${mark.n}` }}</span>
    </button>

    <!-- Who holds a sector: the page fills the mark (an avatar, a time); the same facts are in the page's own list. -->
    <div
      v-for="mark in sectorMarks"
      :key="`sector-${mark.n}`"
      class="track3d__sector-mark"
      :class="{ 'is-active': activeSector === mark.n }"
      :style="{ left: mark.left, top: mark.top, '--sector': mark.color }"
      aria-hidden="true"
      @pointerenter="lightSector(mark.n)"
      @pointerleave="dimSector(mark.n)"
    >
      <slot name="sector" :n="mark.n" :active="activeSector === mark.n" :compact="compact">
        <span class="track3d__sector-tag">S{{ mark.n }}</span>
      </slot>
    </div>

    <div v-if="startMark" class="track3d__start-mark" :style="{ left: startMark.left, top: startMark.top }" aria-hidden="true">
      <slot name="start" :compact="compact" />
    </div>

    <p v-if="interactive && hint && !touched" class="track3d__hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.track3d {
  --t3-edge: var(--bm-blue-bright, #3c74f6);
  --t3-glow: var(--bm-blue, #1652d8);
  --t3-road: var(--c-surface-solid, #0a1224);
  --t3-ink: var(--c-text, #f3f6fc);
  --t3-muted: var(--c-text-2, #a8b3c7);
  --t3-grid: var(--c-line-strong, rgba(150, 178, 255, 0.2));
  --t3-zone: var(--bm-green, #22c55e);
  --t3-light: var(--bm-cyan, #4fd8ea);
  --t3-plate: var(--c-elevated, #101827);
  position: relative;
  width: 100%;
  border-radius: var(--r-lg, 22px);
  user-select: none;
  -webkit-user-select: none;
}

.track3d.is-interactive {
  cursor: grab;
  /* Horizontal drags turn the track; vertical swipes still scroll the page. */
  touch-action: pan-y;
}

.track3d.is-dragging {
  cursor: grabbing;
}

.track3d:focus-visible {
  outline: 2px solid var(--t3-edge);
  outline-offset: 4px;
}

.track3d__svg {
  display: block;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: inherit;
}

.track3d__grid {
  fill: none;
  stroke: var(--t3-grid);
  stroke-width: 1;
  opacity: 0.45;
}

.track3d__glow {
  fill: var(--t3-glow);
  opacity: 0.17;
}

.track3d__edge {
  fill: var(--t3-edge);
}

.track3d__road {
  fill: var(--t3-road);
}

.track3d__dashes {
  fill: var(--t3-ink);
  opacity: 0.34;
}

.track3d__zones {
  fill: var(--t3-zone);
  opacity: 0.55;
}

.track3d__start {
  fill: var(--t3-ink);
}

.track3d__tail {
  fill: var(--t3-light);
  opacity: 0.6;
}

.track3d__light {
  fill: #fff;
  stroke: var(--t3-light);
  stroke-width: 3;
  filter: drop-shadow(0 0 6px var(--t3-light));
}

/* ---------- Timing sectors, each in its own colour ---------- */
.track3d__sector-glow {
  fill: var(--sector);
  opacity: 0.2;
  pointer-events: none;
  transition: opacity var(--dur-2, 280ms) var(--ease-out, ease-out);
}

/* The road itself takes the colour; a lighter rim of the same colour keeps a dark one readable. */
.track3d__sector-road {
  fill: var(--sector);
  stroke: color-mix(in srgb, var(--sector) 55%, #fff);
  stroke-linejoin: round;
  stroke-width: 1.6;
  transition: opacity var(--dur-2, 280ms) var(--ease-out, ease-out);
}

/* On a light surface a pale colour needs a darker rim, not a lighter one. */
:root[data-theme='light'] .track3d__sector-road {
  stroke: color-mix(in srgb, var(--sector) 60%, #0b1220);
}

.track3d.has-active-sector .track3d__sector-road:not(.is-active) {
  opacity: 0.38;
}

.track3d.has-active-sector .track3d__sector-glow:not(.is-active) {
  opacity: 0.06;
}

.track3d__sector-glow.is-active {
  opacity: 0.42;
}

/* Where one sector hands over to the next. */
.track3d__sector-line {
  fill: var(--t3-ink);
  pointer-events: none;
}

.track3d__sector-mark,
.track3d__start-mark {
  position: absolute;
  z-index: 1;
  display: grid;
  place-items: center;
  transform: translate(-50%, -50%);
}

.track3d__sector-mark.is-active,
.track3d__start-mark:hover {
  z-index: 3;
}

.track3d__sector-tag {
  display: grid;
  min-width: 30px;
  height: 22px;
  padding: 0 7px;
  place-items: center;
  border-radius: var(--r-pill, 999px);
  background: var(--sector);
  color: #fff;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 11px;
  font-weight: 700;
}

.track3d__leaders {
  fill: none;
  stroke: var(--t3-muted);
  stroke-width: 1;
  opacity: 0.6;
}

.track3d__corner {
  position: absolute;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 26px;
  min-width: 26px;
  margin: 0;
  padding: 0;
  border: 1px solid color-mix(in srgb, var(--t3-edge) 55%, transparent);
  border-radius: var(--r-pill, 999px);
  background: var(--t3-plate);
  color: var(--t3-ink);
  font: inherit;
  white-space: nowrap;
  cursor: pointer;
  /* The number stays on the corner's mark; the name grows out to the right of it. */
  transform: translate(-13px, -50%);
  transition: border-color var(--dur-1, 160ms) linear, box-shadow var(--dur-2, 280ms) var(--ease-out, ease-out);
}

/* A finger needs more than 26px. */
.track3d__corner::before {
  position: absolute;
  inset: -9px;
  content: '';
}

.track3d__corner.is-active {
  z-index: 2;
  border-color: var(--t3-edge);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}

/* Room for the name (or, where the circuit has none, the plain "Turn 5"). */
.track3d__corner.is-active {
  padding-right: 12px;
}

.track3d__corner:focus-visible {
  outline: 2px solid var(--t3-edge);
  outline-offset: 2px;
}

.track3d__number {
  display: grid;
  width: 24px;
  height: 24px;
  place-items: center;
  border-radius: 50%;
  background: var(--t3-glow);
  color: #fff;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
}

.track3d__name {
  font-family: var(--font-display, system-ui, sans-serif);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.track3d__name.is-plain {
  color: var(--t3-muted);
}

.track3d__hint {
  position: absolute;
  right: 16px;
  bottom: 12px;
  margin: 0;
  color: var(--t3-muted);
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  pointer-events: none;
}

.track3d.is-compact .track3d__corner {
  height: 20px;
  min-width: 20px;
  transform: translate(-10px, -50%);
}

.track3d.is-compact .track3d__number {
  width: 18px;
  height: 18px;
  font-size: 9px;
}

.track3d.is-compact .track3d__hint {
  display: none;
}

@media (prefers-reduced-motion: reduce) {
  .track3d__sector-glow,
  .track3d__sector-road {
    transition: none;
  }
}
</style>
