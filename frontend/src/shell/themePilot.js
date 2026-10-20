// The GETPC pilot who stands between a pilot and the light theme: the dialogue
// he plays, whether he still asks, and how a "just this once" light theme is
// kept apart from a saved one. The scene itself is ThemePilot.vue.
import { reactive } from 'vue'

/** Saying "yes, and don't ask again" leaves this mark; then he never shows up again. */
export const PILOT_ASK_KEY = 'lightThemePilot'
const NEVER = 'never'
/** A light theme taken "just this once" lives here, for this tab only. */
export const THEME_ONCE_KEY = 'themeOnce'

/**
 * The lines in order and the answers to each, in the order the buttons show.
 * `to: null` ends the talk with the theme left alone; `outcome` is how the
 * light theme is taken once the pilot says goodbye.
 */
export const DIALOGUE = Object.freeze({
  warn: [{ id: 'refuse', to: null }, { id: 'want', to: 'sure' }],
  sure: [{ id: 'yes', to: 'howLong' }, { id: 'refuse', to: null }],
  howLong: [{ id: 'once', to: 'bye', outcome: 'once' }, { id: 'forever', to: 'bye', outcome: 'forever' }],
  bye: []
})
export const FIRST_LINE = 'warn'

/**
 * Where an answer leads.
 * @param {string} line  the line being answered
 * @param {string} choice  the answer's id
 * @returns {{ line: string | null, outcome: 'once' | 'forever' | null }}
 */
export function answer(line, choice) {
  const picked = DIALOGUE[line]?.find((item) => item.id === choice)
  if (!picked) return { line: null, outcome: null }
  return { line: picked.to, outcome: picked.outcome || null }
}

/** @param {Storage | null | undefined} storage */
export function pilotStillAsks(storage) {
  try {
    return storage?.getItem(PILOT_ASK_KEY) !== NEVER
  } catch {
    return true
  }
}

/** @param {Storage | null | undefined} storage */
export function stopPilotAsking(storage) {
  try {
    storage?.setItem(PILOT_ASK_KEY, NEVER)
  } catch {
    // Without storage he simply asks again next time.
  }
}

/**
 * The theme to open with: a saved light theme, else a light theme taken just
 * this once in this tab, else dark.
 * @param {Storage | null | undefined} local
 * @param {Storage | null | undefined} session
 * @returns {{ theme: 'light' | 'dark', once: boolean }}
 */
export function readTheme(local, session) {
  try {
    if (local?.getItem('theme') === 'light') return { theme: 'light', once: false }
    if (session?.getItem(THEME_ONCE_KEY) === 'light') return { theme: 'light', once: true }
  } catch {
    // Blocked storage: the default look.
  }
  return { theme: 'dark', once: false }
}

/**
 * Keeps the theme. A light theme taken once stays in this tab only and the
 * saved choice stays dark; any other theme is saved as before.
 * @param {'light' | 'dark'} theme
 * @param {boolean} once
 * @param {Storage | null | undefined} local
 * @param {Storage | null | undefined} session
 */
export function saveTheme(theme, once, local, session) {
  try {
    if (theme === 'light' && once) {
      session?.setItem(THEME_ONCE_KEY, 'light')
      local?.setItem('theme', 'dark')
      return
    }
    local?.setItem('theme', theme)
    session?.removeItem(THEME_ONCE_KEY)
  } catch {
    // Nothing to keep it in.
  }
}

/**
 * The browser's storage, or null where touching it throws (blocked site data).
 * @param {'localStorage' | 'sessionStorage'} name
 * @returns {Storage | null}
 */
export function browserStorage(name) {
  try {
    return window[name] || null
  } catch {
    return null
  }
}

/** The scene's state: open or not, and where the theme control was pressed (for the circle the theme grows from). */
export const themePilot = reactive({ open: false, origin: null })
