// The season title. The winner of a BMRL Championship gets a pilot role from
// the administrators (for example "Победитель BMRL CHAMPIONSHIP 1"); whoever
// holds it is the league's season champion and gets a banner and licences of
// their own. It is a title won over a season, not a rating: do not confuse it
// with the top RER licence tier, which is also called "Champ".

import { roleList } from './pilotRoles.js'

// The name plus its edition, if any: a number or a roman numeral as a whole word.
const EVENT = /bmrl\s+championship(?:\s+(?:\p{N}+|[ivx]+)(?![\p{L}\p{N}]))?/iu
const WINNER_WORDS = new Set(['победитель', 'чемпион', 'winner', 'champion'])

function isSeasonTitle(role) {
  const name = String(role?.name || '')
  if (!EVENT.test(name)) return false
  // Whole words only: "championship" alone must not count as "champion".
  return name.toLowerCase().split(/[^\p{L}\p{N}]+/u).some((word) => WINNER_WORDS.has(word))
}

/**
 * The role that makes this pilot a season champion, or null. Pilots who hide
 * their roles arrive without any, so they show no title either.
 * @param {{ pilot_roles?: Array<{ id: number, name: string } | null> } | null | undefined} pilot
 * @returns {{ id: number, name: string } | null}
 */
export function seasonTitleRole(pilot) {
  return roleList(pilot?.pilot_roles).find(isSeasonTitle) || null
}

/**
 * The championship named in the role, e.g. "BMRL CHAMPIONSHIP 1".
 * @param {{ name?: string } | null | undefined} role
 * @returns {string}
 */
export function seasonTitleEvent(role) {
  const match = String(role?.name || '').match(EVENT)
  return match ? match[0].replace(/\s+/g, ' ') : ''
}
