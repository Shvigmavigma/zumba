import { animate, utils } from 'animejs'
import { canHover, frameThrottle, prefersReducedMotion } from './env'

const handlers = new WeakMap()

function bind(el, events) {
  for (const [name, fn] of Object.entries(events)) el.addEventListener(name, fn, { passive: true })
  handlers.set(el, events)
}

function unbind(el) {
  const events = handlers.get(el)
  if (!events) return
  for (const [name, fn] of Object.entries(events)) el.removeEventListener(name, fn)
  handlers.delete(el)
}

/**
 * v-spotlight — a soft light (and a lit border) follows the cursor across a card.
 * Styling lives in design/fx.css under [data-spotlight].
 */
export const vSpotlight = {
  mounted(el) {
    el.dataset.spotlight = ''
    if (!canHover) return
    const move = frameThrottle((event) => {
      const rect = el.getBoundingClientRect()
      el.style.setProperty('--mx', `${event.clientX - rect.left}px`)
      el.style.setProperty('--my', `${event.clientY - rect.top}px`)
    })
    bind(el, {
      pointermove: move,
      pointerenter: () => el.style.setProperty('--spot', '1'),
      pointerleave: () => el.style.setProperty('--spot', '0')
    })
  },
  unmounted: unbind
}

/**
 * v-tilt — perspective tilt with a moving glare, inspired by React Bits' TiltedCard.
 * Value: max tilt in degrees (default 8).
 */
export const vTilt = {
  mounted(el, binding) {
    if (!canHover || prefersReducedMotion()) return
    const max = Number(binding.value) || 8
    el.dataset.tilt = ''
    const move = frameThrottle((event) => {
      const rect = el.getBoundingClientRect()
      const px = (event.clientX - rect.left) / rect.width
      const py = (event.clientY - rect.top) / rect.height
      el.style.transition = 'transform 120ms ease-out'
      el.style.transform = `perspective(1000px) rotateX(${((0.5 - py) * max).toFixed(2)}deg) rotateY(${((px - 0.5) * max).toFixed(2)}deg) translateZ(0)`
      el.style.setProperty('--gx', `${(px * 100).toFixed(1)}%`)
      el.style.setProperty('--gy', `${(py * 100).toFixed(1)}%`)
    })
    bind(el, {
      pointermove: move,
      pointerenter: () => el.style.setProperty('--glare', '1'),
      pointerleave: () => {
        el.style.transition = 'transform 700ms cubic-bezier(0.32, 0.72, 0, 1)'
        el.style.transform = ''
        el.style.setProperty('--glare', '0')
      }
    })
  },
  unmounted: unbind
}

/**
 * v-magnet — the element leans toward the cursor while hovered (React Bits' Magnet).
 * Value: strength in px (default 6).
 */
export const vMagnet = {
  mounted(el, binding) {
    if (!canHover || prefersReducedMotion()) return
    const strength = Number(binding.value) || 6
    const move = frameThrottle((event) => {
      const rect = el.getBoundingClientRect()
      const dx = (event.clientX - (rect.left + rect.width / 2)) / (rect.width / 2)
      const dy = (event.clientY - (rect.top + rect.height / 2)) / (rect.height / 2)
      el.style.translate = `${(dx * strength).toFixed(2)}px ${(dy * strength).toFixed(2)}px`
    })
    el.style.transition = `${el.style.transition ? `${el.style.transition}, ` : ''}translate 380ms cubic-bezier(0.32, 0.72, 0, 1)`
    bind(el, {
      pointermove: move,
      pointerleave: () => {
        el.style.translate = ''
      }
    })
  },
  unmounted: unbind
}

const SPARK_COUNT = 9

/**
 * v-spark — a burst of sparks on click, like React Bits' ClickSpark, drawn with anime.js.
 */
export const vSpark = {
  mounted(el, binding) {
    const color = binding.value || '#8db1ff'
    bind(el, {
      click: (event) => {
        if (prefersReducedMotion()) return
        const layer = document.createElement('span')
        layer.className = 'ui-spark-layer'
        layer.style.left = `${event.clientX}px`
        layer.style.top = `${event.clientY}px`
        const sparks = Array.from({ length: SPARK_COUNT }, (_, index) => {
          const spark = document.createElement('i')
          spark.style.background = color
          spark.style.rotate = `${(360 / SPARK_COUNT) * index}deg`
          layer.appendChild(spark)
          return spark
        })
        document.body.appendChild(layer)
        animate(sparks, {
          translateY: [0, () => -utils.random(22, 38)],
          scaleY: [1, 0.2],
          opacity: [1, 0],
          duration: 560,
          ease: 'outExpo',
          onComplete: () => layer.remove()
        })
      }
    })
  },
  unmounted: unbind
}
