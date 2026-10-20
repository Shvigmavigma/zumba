import { ref } from 'vue'

const QUERY = '(prefers-reduced-motion: reduce)'
const media = typeof window !== 'undefined' && window.matchMedia ? window.matchMedia(QUERY) : null

/** Reactive flag shared by every animated component. */
export const reducedMotion = ref(Boolean(media?.matches))
media?.addEventListener?.('change', (event) => {
  reducedMotion.value = event.matches
})

export function prefersReducedMotion() {
  return reducedMotion.value
}

const callbacks = new WeakMap()
// Strong set of pending elements for the position fallback below.
const pending = new Set()
let observer = null
let fallbackBound = false
let fallbackTimer = 0
const REVEAL_LINE = 0.92
const FALLBACK_DELAY_MS = 1200

function fire(el) {
  const callback = callbacks.get(el)
  if (!callback) return
  callbacks.delete(el)
  pending.delete(el)
  observer?.unobserve(el)
  callback(el)
}

/**
 * Safety net next to IntersectionObserver: reveal anything whose top has
 * passed the reveal line, so content can never stay hidden if the observer
 * is throttled or unavailable.
 */
function checkPending() {
  const line = window.innerHeight * REVEAL_LINE
  for (const el of [...pending]) {
    if (!el.isConnected) {
      pending.delete(el)
      continue
    }
    if (el.getBoundingClientRect().top < line) fire(el)
  }
}

function bindFallback() {
  if (fallbackBound || typeof window === 'undefined') return
  fallbackBound = true
  const onScroll = frameThrottle(checkPending)
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('resize', onScroll, { passive: true })
}

function sharedObserver() {
  if (observer || typeof IntersectionObserver === 'undefined') return observer
  observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) fire(entry.target)
    }
  }, {
    // Fire as soon as any part of the element passes the lower 8% of the
    // viewport. A ratio threshold would never be met by blocks taller than
    // the screen (long result tables on phones), leaving them hidden.
    rootMargin: '0px 0px -8% 0px',
    threshold: 0
  })
  return observer
}

/** Runs `callback` once, the first time `el` scrolls into view. */
export function onceInView(el, callback) {
  const io = sharedObserver()
  if (!io) {
    callback(el)
    return () => {}
  }
  callbacks.set(el, callback)
  pending.add(el)
  io.observe(el)
  bindFallback()
  // One shared timer per burst of mounts, not one per element.
  if (!fallbackTimer) {
    fallbackTimer = window.setTimeout(() => {
      fallbackTimer = 0
      checkPending()
    }, FALLBACK_DELAY_MS)
  }
  return () => {
    callbacks.delete(el)
    pending.delete(el)
    io.unobserve(el)
  }
}

/** Throttles pointer-driven style updates to one per animation frame. */
export function frameThrottle(fn) {
  let frame = 0
  let lastArgs = null
  return (...args) => {
    lastArgs = args
    if (frame) return
    frame = requestAnimationFrame(() => {
      frame = 0
      fn(...lastArgs)
    })
  }
}

export const canHover = typeof window !== 'undefined' && window.matchMedia
  ? window.matchMedia('(hover: hover) and (pointer: fine)').matches
  : false
