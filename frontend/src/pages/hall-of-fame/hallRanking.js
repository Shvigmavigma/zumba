// How the Hall of Fame orders pilots and teams. Two standings share one list:
// by RER (everybody, best rating first) and by medals (podium finishers only).
import { OVERALL_RATING_GAME, RATING_GAMES, ratingForGame } from '../../pilotDisplay'
import { isRerExcluded } from '../../ranks'

export const HALL_MODE_RATING = 'rating'
export const HALL_MODE_MEDALS = 'medals'

/**
 * One podium statistic of a pilot or a team for the selected simulator.
 * @param {object | null | undefined} item
 * @param {'points' | 'gold' | 'silver' | 'bronze' | 'podiums'} field
 * @param {string} game  a simulator, or OVERALL_RATING_GAME for all of them
 * @returns {number}
 */
export function hallStat(item, field, game) {
  const source = game === OVERALL_RATING_GAME ? item : item?.stats_by_game?.[game]
  return Number(source?.[field] || 0)
}

function isTeam(item) {
  return item?.member_count !== undefined
}

function teamRating(team, game) {
  if (game !== OVERALL_RATING_GAME) return team?.ratings_by_game?.[game] ?? team?.average_rating
  const ratings = RATING_GAMES
    .map((itemGame) => Number(team?.ratings_by_game?.[itemGame]))
    .filter((rating) => Number.isFinite(rating))
  return ratings.length ? Math.max(...ratings) : team?.average_rating
}

/**
 * The RER a pilot or a team is ranked by in the selected simulator; overall
 * it is their best one.
 * @param {object | null | undefined} item
 * @param {string} game
 * @returns {number | undefined}
 */
export function hallRating(item, game) {
  return isTeam(item) ? teamRating(item, game) : ratingForGame(item, game)
}

function compareMedals(left, right, game) {
  return hallStat(right, 'points', game) - hallStat(left, 'points', game)
    || hallStat(right, 'gold', game) - hallStat(left, 'gold', game)
    || hallStat(right, 'silver', game) - hallStat(left, 'silver', game)
    || hallStat(right, 'bronze', game) - hallStat(left, 'bronze', game)
}

function compareNames(left, right) {
  return String(left.nickname || left.name || '').localeCompare(String(right.nickname || right.name || ''), undefined, { sensitivity: 'base' })
}

/**
 * The standings, best first, as a new list. By rating everybody in the rating
 * is ranked (pilots taken out of RER have no place in it); by medals only
 * those with podium points. Ties fall to medals, then names.
 * @template T
 * @param {T[]} items
 * @param {{ mode: string, game: string }} options
 * @returns {T[]}
 */
export function rankHallItems(items, { mode, game }) {
  const byRating = mode === HALL_MODE_RATING
  return [...(items || [])]
    .filter((item) => (byRating ? !isRerExcluded(item) : hallStat(item, 'points', game) > 0))
    .sort((left, right) => (
      (byRating ? Number(hallRating(right, game) || 0) - Number(hallRating(left, game) || 0) : 0)
      || compareMedals(left, right, game)
      || compareNames(left, right)
    ))
}
