import { animate, splitText, stagger } from 'animejs'
import { onceInView, prefersReducedMotion } from './env'

const DEFAULTS = { y: 22, blur: 8, scale: 1, delay: 0, duration: 900 }
const cleanups = new WeakMap()

function clearInlineMotion(el) {
  el.style.removeProperty('opacity')
  el.style.removeProperty('transform')
  el.style.removeProperty('filter')
  el.style.removeProperty('will-change')
}

/**
 * v-reveal — fades an element up out of a soft blur the first time it enters
 * the viewport. Accepts a number (delay in ms) or { y, blur, scale, delay, duration }.
 */
export const vReveal = {
  mounted(el, binding) {
    if (prefersReducedMotion()) return
    const options = { ...DEFAULTS, ...(typeof binding.value === 'number' ? { delay: binding.value } : binding.value || {}) }
    el.style.opacity = '0'
    el.style.transform = `translate3d(0, ${options.y}px, 0) scale(${options.scale})`
    el.style.filter = options.blur ? `blur(${options.blur}px)` : ''
    el.style.willChange = 'opacity, transform, filter'
    const stop = onceInView(el, () => {
      const params = {
        opacity: [0, 1],
        translateY: [options.y, 0],
        scale: [options.scale, 1],
        duration: options.duration,
        delay: options.delay,
        ease: 'outExpo',
        onComplete: () => clearInlineMotion(el)
      }
      if (options.blur) params.filter = [`blur(${options.blur}px)`, 'blur(0px)']
      animate(el, params)
    })
    cleanups.set(el, stop)
  },
  unmounted(el) {
    cleanups.get(el)?.()
    cleanups.delete(el)
  }
}

/**
 * v-split — splits a heading into characters and lets them rise into place,
 * like a timing board flipping. Text that later changes reactively simply
 * replaces the split markup, so the heading always shows the right words.
 */
export const vSplit = {
  mounted(el, binding) {
    if (prefersReducedMotion() || !el.textContent.trim()) return
    const options = { delay: 0, stagger: 22, ...(typeof binding.value === 'number' ? { delay: binding.value } : binding.value || {}) }
    const splitter = splitText(el, { words: { wrap: 'clip' }, chars: true, accessible: true })
    el.style.visibility = 'hidden'
    const stop = onceInView(el, () => {
      el.style.visibility = ''
      animate(splitter.chars, {
        translateY: ['110%', '0%'],
        rotate: [8, 0],
        opacity: [0, 1],
        duration: 900,
        delay: stagger(options.stagger, { start: options.delay }),
        ease: 'outExpo',
        // Only restore the plain text if Vue has not already replaced it.
        onComplete: () => { if (el.contains(splitter.chars[0])) splitter.revert() }
      })
    })
    cleanups.set(el, () => {
      stop()
      el.style.visibility = ''
    })
  },
  unmounted(el) {
    cleanups.get(el)?.()
    cleanups.delete(el)
  }
}
