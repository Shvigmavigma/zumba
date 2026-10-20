import { ref } from 'vue'

/** Shared open state for the ⌘K command palette. */
export const paletteOpen = ref(false)

export function openPalette() {
  paletteOpen.value = true
}

export function closePalette() {
  paletteOpen.value = false
}
