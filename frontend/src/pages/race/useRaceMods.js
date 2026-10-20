import { computed, reactive, toValue } from 'vue'
import { modsNoticeKey, requiredMods } from './raceMods'

const STORAGE_KEY = 'bmrl-mods-seen'
// How long the mods block stays lit after the page scrolls to it.
const FLASH_MS = 1800
/** The id the briefing gives its mods block; the hero and the form scroll to it. */
export const MODS_ANCHOR_ID = 'race-mods'

function readSeen() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
    return Array.isArray(saved) ? saved.filter((key) => typeof key === 'string') : []
  } catch {
    return []
  }
}

// Shared by every part of the race page: opening the list in the briefing
// calms the warning in the hero and in the registration form too.
const shared = reactive({ seen: new Set(readSeen()), flashKey: '' })
let flashTimer = 0

function persist() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...shared.seen]))
  } catch {
    // Private mode or blocked storage: the reminder simply comes back next visit.
  }
}

/**
 * The race's mods and whether this pilot has opened them yet.
 * @param {import('vue').MaybeRefOrGetter<object | null>} race
 */
export function useRaceMods(race) {
  const mods = computed(() => requiredMods(toValue(race)))
  const key = computed(() => modsNoticeKey(toValue(race)))
  const seen = computed(() => !key.value || shared.seen.has(key.value))
  const flashing = computed(() => Boolean(key.value) && shared.flashKey === key.value)

  function markSeen() {
    if (!key.value || shared.seen.has(key.value)) return
    shared.seen = new Set([...shared.seen, key.value])
    persist()
  }

  /** Scrolls to the mods block and lights it up for a moment. */
  function showMods() {
    document.getElementById(MODS_ANCHOR_ID)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    shared.flashKey = key.value
    window.clearTimeout(flashTimer)
    flashTimer = window.setTimeout(() => {
      shared.flashKey = ''
    }, FLASH_MS)
  }

  return { mods, seen, flashing, markSeen, showMods }
}
