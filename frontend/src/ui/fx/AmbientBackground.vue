<script setup>
// Site-wide animated backdrop: a slow brand-blue aurora crossed by faint
// "light trails" (in the spirit of React Bits' Aurora / Hyperspeed), rendered
// with OGL at reduced resolution. Scrolling briefly speeds the trails up.
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Mesh, Program, Renderer, Triangle } from 'ogl'
import { state } from '../../store'
import { reducedMotion } from '../motion/env'

const host = ref(null)
const failed = ref(false)

const vertex = /* glsl */ `
attribute vec2 position;
void main() {
  gl_Position = vec4(position, 0.0, 1.0);
}
`

const fragment = /* glsl */ `
precision highp float;
uniform float uTime;
uniform float uDistance;
uniform vec2 uRes;
uniform vec2 uPointer;
uniform vec3 uBg;
uniform vec3 uBlue;
uniform vec3 uDeep;
uniform vec3 uCyan;
uniform float uLight;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
  float v = 0.0;
  float a = 0.5;
  for (int i = 0; i < 4; i++) { v += a * noise(p); p *= 2.03; a *= 0.5; }
  return v;
}

void main() {
  vec2 p = (gl_FragCoord.xy - 0.5 * uRes) / uRes.y;
  float t = uTime;
  vec3 col = uBg;
  float tint = mix(1.0, 0.55, uLight);

  // Aurora: two drifting pools of blue shaped by domain-warped noise.
  vec2 q = p * 1.15 + vec2(0.0, t * 0.015);
  float n = fbm(q + vec2(fbm(q + t * 0.03), fbm(q - t * 0.022)));
  vec2 c1 = vec2(0.62 + 0.08 * sin(t * 0.06), 0.42 + 0.05 * cos(t * 0.08)) + uPointer * 0.04;
  vec2 c2 = vec2(-0.75 + 0.07 * cos(t * 0.045), -0.5 + 0.04 * sin(t * 0.07)) - uPointer * 0.03;
  float b1 = smoothstep(1.0, 0.0, length((p - c1) * vec2(0.8, 1.1)));
  float b2 = smoothstep(1.15, 0.0, length((p - c2) * vec2(0.9, 1.0)));
  col = mix(col, uDeep, b2 * 0.6 * n * tint);
  col = mix(col, uBlue, b1 * 0.42 * (0.55 + 0.45 * n) * tint);
  col += uCyan * 0.035 * pow(b1, 3.0) * (1.0 - uLight);

  // Light trails running diagonally across the page, like cars on a straight.
  float ang = -0.42;
  vec2 s = mat2(cos(ang), -sin(ang), sin(ang), cos(ang)) * p;
  float laneY = s.y * 20.0;
  float lane = floor(laneY);
  float r = hash(vec2(lane, 3.17));
  float active = step(0.8, r);
  float width = 0.05 + 0.06 * hash(vec2(lane, 9.1));
  float line = smoothstep(width, 0.0, abs(fract(laneY) - 0.5));
  float seg = fract(s.x * (0.9 + r * 1.6) - uDistance * (0.25 + r * 0.8) + r * 13.0);
  float trail = pow(seg, 7.0) * smoothstep(1.0, 0.965, seg) * line * active;
  vec3 trailColor = mix(uBlue, uCyan, step(0.94, r));
  col = mix(col, trailColor, clamp(trail * mix(0.62, 0.35, uLight), 0.0, 1.0));

  // Vignette (dark theme only) and fine grain to avoid gradient banding.
  float vig = smoothstep(1.45, 0.15, length(p * vec2(0.85, 1.2)));
  col *= mix(mix(0.7, 1.0, vig), 1.0, uLight);
  col += (hash(gl_FragCoord.xy + fract(t * 7.0)) - 0.5) * 0.016;
  gl_FragColor = vec4(col, 1.0);
}
`

const PALETTES = {
  dark: { bg: [0.016, 0.024, 0.043], blue: [0.086, 0.322, 0.847], deep: [0.051, 0.184, 0.561], cyan: [0.31, 0.847, 0.918], light: 0 },
  light: { bg: [0.933, 0.945, 0.969], blue: [0.55, 0.68, 0.98], deep: [0.78, 0.84, 0.97], cyan: [0.31, 0.75, 0.86], light: 1 }
}
const RESOLUTION_SCALE = 0.7
const FRAME_INTERVAL = 1000 / 30

let renderer = null
let program = null
let mesh = null
let frame = 0
let lastFrame = 0
let lastTick = 0
let distance = 0
let speed = 1
let scrollVelocity = 0
let lastScrollY = 0
let pointerX = 0
let pointerY = 0
let resizeObserver = null

function applyPalette(theme, instant = false) {
  if (!program) return
  const palette = PALETTES[theme === 'light' ? 'light' : 'dark']
  const u = program.uniforms
  const from = { bg: [...u.uBg.value], blue: [...u.uBlue.value], deep: [...u.uDeep.value], cyan: [...u.uCyan.value], light: u.uLight.value }
  const start = performance.now()
  const duration = instant ? 0 : 700
  const mixArr = (a, b, k) => a.map((value, index) => value + (b[index] - value) * k)
  const step = (now) => {
    const k = duration ? Math.min(1, (now - start) / duration) : 1
    const e = 1 - Math.pow(1 - k, 3)
    u.uBg.value = mixArr(from.bg, palette.bg, e)
    u.uBlue.value = mixArr(from.blue, palette.blue, e)
    u.uDeep.value = mixArr(from.deep, palette.deep, e)
    u.uCyan.value = mixArr(from.cyan, palette.cyan, e)
    u.uLight.value = from.light + (palette.light - from.light) * e
    if (reducedMotion.value || !frame) render(performance.now())
    if (k < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

function resize() {
  if (!renderer || !host.value) return
  const { clientWidth, clientHeight } = host.value
  renderer.dpr = Math.min(window.devicePixelRatio || 1, 1.5) * RESOLUTION_SCALE
  renderer.setSize(clientWidth, clientHeight)
  program.uniforms.uRes.value = [renderer.gl.canvas.width, renderer.gl.canvas.height]
  render(performance.now())
}

function render(now) {
  if (!renderer) return
  program.uniforms.uTime.value = now / 1000
  program.uniforms.uDistance.value = distance
  program.uniforms.uPointer.value = [pointerX, pointerY]
  renderer.render({ scene: mesh })
}

function loop(now) {
  frame = requestAnimationFrame(loop)
  if (now - lastFrame < FRAME_INTERVAL) return
  const dt = Math.min(0.1, (now - (lastTick || now)) / 1000)
  lastTick = now
  lastFrame = now
  scrollVelocity *= 0.9
  const target = 1 + Math.min(7, Math.abs(scrollVelocity) * 0.012)
  speed += (target - speed) * 0.08
  distance += dt * speed * 0.32
  render(now)
}

function start() {
  if (frame || reducedMotion.value || !renderer) return
  lastTick = 0
  frame = requestAnimationFrame(loop)
}

function stop() {
  cancelAnimationFrame(frame)
  frame = 0
}

function handleVisibility() {
  if (document.hidden) stop()
  else start()
}

function handleScroll() {
  const y = window.scrollY
  scrollVelocity += y - lastScrollY
  lastScrollY = y
}

function handlePointer(event) {
  pointerX = event.clientX / window.innerWidth - 0.5
  pointerY = 0.5 - event.clientY / window.innerHeight
}

onMounted(() => {
  try {
    renderer = new Renderer({ dpr: RESOLUTION_SCALE, alpha: false, antialias: false, powerPreference: 'low-power', webgl: 1 })
    const gl = renderer.gl
    if (!gl) throw new Error('WebGL unavailable')
    host.value.appendChild(gl.canvas)
    const palette = PALETTES[state.theme === 'light' ? 'light' : 'dark']
    program = new Program(gl, {
      vertex,
      fragment,
      uniforms: {
        uTime: { value: 0 },
        uDistance: { value: 0 },
        uRes: { value: [1, 1] },
        uPointer: { value: [0, 0] },
        uBg: { value: palette.bg },
        uBlue: { value: palette.blue },
        uDeep: { value: palette.deep },
        uCyan: { value: palette.cyan },
        uLight: { value: palette.light }
      }
    })
    mesh = new Mesh(gl, { geometry: new Triangle(gl), program })
    resizeObserver = new ResizeObserver(resize)
    resizeObserver.observe(host.value)
    resize()
    lastScrollY = window.scrollY
    window.addEventListener('scroll', handleScroll, { passive: true })
    window.addEventListener('pointermove', handlePointer, { passive: true })
    document.addEventListener('visibilitychange', handleVisibility)
    start()
  } catch {
    failed.value = true
    renderer = null
  }
})

watch(() => state.theme, (theme) => applyPalette(theme))
watch(reducedMotion, (reduce) => {
  if (reduce) {
    stop()
    render(performance.now())
  } else {
    start()
  }
})

onBeforeUnmount(() => {
  stop()
  resizeObserver?.disconnect()
  window.removeEventListener('scroll', handleScroll)
  window.removeEventListener('pointermove', handlePointer)
  document.removeEventListener('visibilitychange', handleVisibility)
  renderer?.gl.getExtension('WEBGL_lose_context')?.loseContext()
  renderer = null
})
</script>

<template>
  <div ref="host" class="ambient" :class="{ 'is-fallback': failed }" aria-hidden="true"></div>
</template>

<style scoped>
.ambient {
  position: fixed;
  inset: 0;
  z-index: -1;
  overflow: hidden;
  pointer-events: none;
  background:
    radial-gradient(60% 50% at 80% 10%, color-mix(in srgb, var(--bm-blue) 26%, transparent), transparent 70%),
    radial-gradient(50% 50% at 0% 100%, color-mix(in srgb, var(--bm-blue-deep) 30%, transparent), transparent 70%),
    var(--c-bg);
}

.ambient :deep(canvas) {
  display: block;
  width: 100% !important;
  height: 100% !important;
}
</style>
