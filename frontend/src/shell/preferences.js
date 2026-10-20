import { nextTick, watch } from 'vue'
import { state } from '../store'
import { timeZoneOptions } from '../timezone'
import { prefersReducedMotion } from '../ui/motion/env'
import { browserStorage, pilotStillAsks, readTheme, saveTheme, themePilot } from './themePilot'

// A light theme taken "just this once" (ThemePilot.vue) is kept for this tab only.
let themeOnce = readTheme(browserStorage('localStorage'), browserStorage('sessionStorage')).once

/**
 * Switches theme. Light goes through the GETPC pilot first (ThemePilot.vue),
 * unless he was told not to ask again.
 * @param {MouseEvent} [event]
 */
export function toggleTheme(event) {
  const next = state.theme === 'light' ? 'dark' : 'light'
  const origin = Number.isFinite(event?.clientX) ? { x: event.clientX, y: event.clientY } : null
  if (next === 'light' && pilotStillAsks(browserStorage('localStorage'))) {
    if (!themePilot.open) Object.assign(themePilot, { open: true, origin })
    return
  }
  switchTheme(next, origin)
}

/**
 * Applies a theme. Where the View Transitions API exists, the new theme grows
 * out of the pressed control as a circle.
 * @param {'light' | 'dark'} next
 * @param {{ x: number, y: number } | null} [origin]  where the theme control was pressed
 * @param {{ once?: boolean }} [options]  once: a light theme for this tab only, the saved choice stays
 */
export function switchTheme(next, origin = null, { once = false } = {}) {
  themeOnce = next === 'light' && once
  const apply = () => { state.theme = next }
  if (!document.startViewTransition || prefersReducedMotion()) {
    apply()
    return
  }
  const x = origin?.x ?? window.innerWidth - 40
  const y = origin?.y ?? 40
  const radius = Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y))
  const transition = document.startViewTransition(async () => {
    apply()
    await nextTick()
  })
  transition.ready.then(() => {
    document.documentElement.animate(
      { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${radius}px at ${x}px ${y}px)`] },
      { duration: 620, easing: 'cubic-bezier(0.32, 0.72, 0, 1)', pseudoElement: '::view-transition-new(root)' }
    )
  }).catch(() => {})
}

/** @param {'ru' | 'en'} value */
export function setLocale(value) {
  state.locale = value === 'en' ? 'en' : 'ru'
}

/** @param {string} value */
export function setTimeZone(value) {
  state.timeZone = timeZoneOptions.some((item) => item.value === value) ? value : 'Europe/Moscow'
}

/**
 * Persists theme, locale and time zone, keeping the document in sync.
 * @param {{ value: string }} locale vue-i18n locale ref
 */
export function syncPreferences(locale) {
  watch(() => state.theme, (value) => {
    const theme = value === 'light' ? 'light' : 'dark'
    document.documentElement.dataset.theme = theme
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'light' ? '#eef1f7' : '#04060b')
    saveTheme(theme, themeOnce, browserStorage('localStorage'), browserStorage('sessionStorage'))
  }, { immediate: true })

  watch(() => state.locale, (value) => {
    const next = value === 'en' ? 'en' : 'ru'
    if (next !== value) {
      state.locale = next
      return
    }
    locale.value = next
    document.documentElement.lang = next
    localStorage.setItem('locale', next)
  }, { immediate: true })

  watch(() => state.timeZone, (value) => {
    const next = timeZoneOptions.some((item) => item.value === value) ? value : 'Europe/Moscow'
    if (next !== value) {
      state.timeZone = next
      return
    }
    localStorage.setItem('timeZone', next)
    localStorage.setItem('timeZonePreferenceVersion', '2')
  }, { immediate: true })
}
