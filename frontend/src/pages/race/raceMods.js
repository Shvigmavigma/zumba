// Mods a race needs. A pilot without them cannot join the server, so the race
// page keeps pointing at the list until the pilot has opened it once
// (useRaceMods.js holds that state; these are its pure parts).

/**
 * The mods the race asks for, cleaned up; empty when none are needed.
 * @param {{ mods_pack?: Array<string | null> } | null | undefined} race
 * @returns {string[]}
 */
export function requiredMods(race) {
  return (race?.mods_pack || []).map((mod) => String(mod || '').trim()).filter(Boolean)
}

// A scheme, or a host with a dot in it, and no spaces anywhere.
const ADDRESS = /^(?:(?:https?:)?\/\/\S+|[\w-]+(?:\.[\w-]+)+(?:[/?#]\S*)?)$/i

/**
 * True when the mod is an address to open; staff sometimes type a pack's
 * name instead, and that must not become a dead link.
 * @param {string | null | undefined} mod
 * @returns {boolean}
 */
export function isModLink(mod) {
  return ADDRESS.test(String(mod || '').trim())
}

/**
 * What "the pilot has seen the mods" is remembered under: this race with this
 * exact list. When staff change the list the key changes and the reminder
 * comes back. Empty when the race needs no mods.
 * @param {{ id?: number | string, mods_pack?: Array<string | null> } | null | undefined} race
 * @returns {string}
 */
export function modsNoticeKey(race) {
  const mods = requiredMods(race)
  return mods.length ? `${race?.id ?? ''}:${mods.join('|')}` : ''
}
