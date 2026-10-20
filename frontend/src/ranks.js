import { DEFAULT_LICENSE_TIERS, OVERALL_RATING_GAME, ratingForGame } from './pilotDisplay'
import { seasonTitleRole } from './seasonChampion'

// Visual ranks follow the licence tiers by position, not by name, so tiers that
// are renamed or re-priced in the admin keep their look: the first tier is
// matte, the last one legendary. Styles live in design/ranks.css.
export const RANK_KEYS = ['rookie', 'bronze', 'silver', 'gold', 'platinum', 'diamond', 'champ']

/**
 * The rank a rating reaches, with what is left to the next one.
 * @param {number | string | null | undefined} rating
 * @param {{ name: string, min_rating: number, max_rating: number, color?: string }[]} [tiers]
 */
export function rankFor(rating, tiers = DEFAULT_LICENSE_TIERS) {
  const list = Array.isArray(tiers) && tiers.length ? tiers : DEFAULT_LICENSE_TIERS
  const value = Number.isFinite(Number(rating)) && rating !== null && rating !== '' ? Number(rating) : 0
  let index = list.findIndex((tier) => value >= Number(tier.min_rating) && value <= Number(tier.max_rating))
  if (index < 0) index = value > Number(list[list.length - 1].max_rating) ? list.length - 1 : 0
  const level = list.length > 1 ? Math.round((index * (RANK_KEYS.length - 1)) / (list.length - 1)) : 0
  const tier = list[index]
  const next = list[index + 1] || null
  const span = next ? Number(next.min_rating) - Number(tier.min_rating) : 0
  return {
    key: RANK_KEYS[level],
    level,
    index,
    tier,
    next,
    rating: Math.round(value),
    toNext: next ? Math.max(0, Math.ceil(Number(next.min_rating) - value)) : 0,
    progress: next && span > 0 ? Math.min(1, Math.max(0, (value - Number(tier.min_rating)) / span)) : 1
  }
}

/**
 * True for a pilot staff took out of the rating: they race, but RER neither
 * counts them nor ranks them.
 * @param {object | null | undefined} user
 * @returns {boolean}
 */
export function isRerExcluded(user) {
  return user?.exclude_from_rer === true
}

/**
 * A pilot's overall rank: their best RER across the simulators. A pilot
 * outside the rating has no rank to show and stays in the entry tier.
 * @param {object | null | undefined} user
 * @param {object[]} [tiers]
 */
export function overallRank(user, tiers) {
  return rankFor(isRerExcluded(user) ? null : ratingForGame(user, OVERALL_RATING_GAME), tiers)
}

/** The finish lists give the season champion instead of an RER rank's (see seasonChampion.js). */
export const SEASON_FINISH = 'season'

/**
 * How a pilot is finished in lists: the season champion's own finish, or else
 * the key of their overall rank. A finish is a look, not a rank: for the RER
 * tier itself use overallRank.
 * @param {object | null | undefined} user
 * @param {object[]} [tiers]
 * @returns {string}
 */
export function finishOf(user, tiers) {
  return seasonTitleRole(user) ? SEASON_FINISH : overallRank(user, tiers).key
}

/**
 * The same for a result row, which carries a rating and roles, not a pilot.
 * @param {number | string | null | undefined} rating
 * @param {Array<{ name: string } | null> | null | undefined} roles
 * @param {object[]} [tiers]
 * @returns {string}
 */
export function finishOfRating(rating, roles, tiers) {
  return seasonTitleRole({ pilot_roles: roles }) ? SEASON_FINISH : rankFor(rating, tiers).key
}

/**
 * Every tier as a rank, for ladders that show the whole way up.
 * @param {object[]} [tiers]
 */
export function rankLadder(tiers = DEFAULT_LICENSE_TIERS) {
  const list = Array.isArray(tiers) && tiers.length ? tiers : DEFAULT_LICENSE_TIERS
  return list.map((tier) => ({ ...rankFor(tier.min_rating, list), name: tier.name }))
}
