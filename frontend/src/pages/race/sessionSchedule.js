// The evening's sessions of a race, as staff scheduled them. Times come from
// the API as wall-clock strings ("19:30:00"); how they are shown in the
// viewer's time zone is up to timezone.js.

// Running order. The race itself is the one the schedule leads up to.
const SESSIONS = [
  { key: 'briefing' },
  { key: 'practice' },
  { key: 'qualification' },
  { key: 'race_session', main: true }
]

const MINUTES_IN_DAY = 24 * 60

function clockMinutes(value) {
  const match = /^(\d{1,2}):(\d{2})(?::\d{2})?$/.exec(String(value ?? '').trim())
  if (!match) return null
  const hours = Number(match[1])
  const minutes = Number(match[2])
  return hours > 23 || minutes > 59 ? null : hours * 60 + minutes
}

/**
 * How long a session lasts, in whole minutes. A session that ends after
 * midnight is counted into the next day.
 * @param {string | null | undefined} start  "HH:MM" or "HH:MM:SS"
 * @param {string | null | undefined} end
 * @returns {number | null} null when either time cannot be read
 */
export function sessionMinutes(start, end) {
  const from = clockMinutes(start)
  const to = clockMinutes(end)
  if (from === null || to === null) return null
  return to >= from ? to - from : to - from + MINUTES_IN_DAY
}

/**
 * The sessions that have both a start and an end, in running order.
 * @param {object | null | undefined} race
 * @returns {{ key: string, start: string, end: string, minutes: number | null, main: boolean }[]}
 */
export function raceSessions(race) {
  return SESSIONS
    .map(({ key, main }) => ({ key, start: race?.[`${key}_start_time`], end: race?.[`${key}_end_time`], main: Boolean(main) }))
    .filter((session) => session.start && session.end)
    .map(({ key, start, end, main }) => ({ key, start, end, minutes: sessionMinutes(start, end), main }))
}
