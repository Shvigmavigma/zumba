// Lap and race times as the race page reads and shows them. A missing time
// (null, an empty field) is never a time of zero: results entered by hand
// carry no qualifying lap for most pilots, and a pilot who did not start has
// a finish time of 0.

export const ACC_MAX_TIME_MS = 2147483647
const ACC_MAX_TIME_ALIASES = new Set([ACC_MAX_TIME_MS, 4294967295])

function isBlank(value) {
  return value === null || value === undefined || value === ''
}

/** 2:05.123 style lap/race time; "-" when there is no time or the value is not a number. */
export function formatDuration(ms) {
  if (isBlank(ms) || !Number.isFinite(Number(ms))) return '-'
  const totalMs = Math.max(0, Math.round(Number(ms)))
  const minutes = Math.floor(totalMs / 60000)
  const seconds = Math.floor((totalMs % 60000) / 1000)
  const millis = totalMs % 1000
  return `${minutes}:${String(seconds).padStart(2, '0')}.${String(millis).padStart(3, '0')}`
}

/** ACC writes INT32_MAX (or UINT32_MAX) as the time of a car that did not finish. */
export function isAccMaxTime(value) {
  if (isBlank(value)) return false
  const number = Number(value)
  return Number.isFinite(number) && (ACC_MAX_TIME_ALIASES.has(number) || number >= ACC_MAX_TIME_MS)
}

/**
 * A time that was really set: a positive number of milliseconds, not the simulator's "no time".
 * @param {unknown} value
 * @returns {number | null}
 */
export function validTimeMs(value) {
  if (isBlank(value)) return null
  const number = Number(value)
  return Number.isFinite(number) && number > 0 && !isAccMaxTime(number) ? number : null
}

/** A time as the results show it: "-" where none was set. */
export function timeLabel(value) {
  const ms = validTimeMs(value)
  return ms === null ? '-' : formatDuration(ms)
}
