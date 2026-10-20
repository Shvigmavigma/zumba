// Which stored result rows make the classification the race page shows.
// Pilots staff took out of the rating (exclude_from_rer) drive the race but
// are not classified: their rows are left out and everybody behind moves up.
import { validTimeMs } from './raceTime.js'

/**
 * True when the row's pilot is outside the rating: by the row's own flag, or
 * by the flag of the registered pilot. A car without an account never is.
 * @param {{ user_id?: number | string | null, exclude_from_rer?: boolean } | null | undefined} row
 * @param {Array<{ user_id?: number | string, exclude_from_rer?: boolean }>} [participants]
 * @returns {boolean}
 */
export function isRowOutsideRating(row, participants = []) {
  if (row?.exclude_from_rer === true) return true
  const userId = Number(row?.user_id)
  if (!Number.isInteger(userId) || userId <= 0) return false
  return participants.find((item) => Number(item.user_id) === userId)?.exclude_from_rer === true
}

function finiteOrNull(value) {
  return value !== null && value !== undefined && Number.isFinite(Number(value)) ? Number(value) : null
}

/**
 * The classification, as a new list: rows of pilots outside the rating are
 * dropped, places are renumbered and gaps are counted from the new leader.
 * @template {{ position?: number, gap_ms?: number | null }} T
 * @param {T[] | null | undefined} rows  stored rows, best first
 * @param {object[]} [participants]
 * @returns {T[]}
 */
export function classifiedRows(rows, participants = []) {
  const shown = (rows || []).filter((row) => !isRowOutsideRating(row, participants))
  const leaderGap = finiteOrNull(shown[0]?.gap_ms) ?? 0
  return shown.map((row, index) => {
    const gap = finiteOrNull(row.gap_ms)
    return { ...row, position: index + 1, gap_ms: gap === null ? row.gap_ms ?? null : Math.max(0, gap - leaderGap) }
  })
}

/**
 * An ACC leaderboard line of a car that actually drove: entries that never
 * left the pits are not part of the session's result.
 * @param {{ timing?: { lapCount?: number } } | null | undefined} line
 * @returns {boolean}
 */
export function accLineHasActivity(line) {
  return Number(line?.timing?.lapCount || 0) > 0
}

/**
 * The rows of a hand-entered qualifying in grid order: by the stored position and,
 * where the results keep lap times only (a simulator without a result file), by the
 * lap time. A pilot without a qualifying lap is not in it.
 * @param {object[]} rows  result rows
 * @returns {object[]}
 */
export function qualificationOrder(rows) {
  const place = (row) => Number(row.qualification_position) || Infinity
  const lap = (row) => Number(row.qualification_best_lap_ms)
  return rows
    .filter((row) => lap(row) > 0)
    .sort((left, right) => (place(left) - place(right)) || (lap(left) - lap(right)))
}

/**
 * The stewards annulled this pilot's laps: their best laps and sector times do not count
 * for the fastest lap, the track records or the sector holders. The result itself stands.
 * @param {object | null | undefined} row  result row
 * @returns {boolean}
 */
export function lapsAnnulled(row) {
  return row?.laps_annulled === true
}

/**
 * The best lap of a race weekend: the fastest of the race and qualifying laps,
 * with the session it was set in. Laps the stewards annulled do not count.
 * @param {object[]} rows  result rows
 * @returns {{ row: object, ms: number, session: 'race' | 'qualification' } | null}
 */
export function bestLapOf(rows) {
  let best = null
  for (const row of rows || []) {
    if (lapsAnnulled(row)) continue
    for (const [session, value] of [['race', row.best_lap_ms], ['qualification', row.qualification_best_lap_ms]]) {
      const ms = validTimeMs(value)
      if (ms !== null && (best === null || ms < best.ms)) best = { row, ms, session }
    }
  }
  return best
}
