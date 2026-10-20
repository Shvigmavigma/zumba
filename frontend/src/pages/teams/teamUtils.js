// Shared helpers for the Teams page: abbreviation rules, team colours and
// seat (roster capacity) maths.

export const DEFAULT_TEAM_COLOR = '#dc2626'

/** Quick livery picks offered next to the native colour picker. */
export const TEAM_COLOR_PRESETS = [
  '#1652d8',
  '#0891b2',
  '#0d9488',
  '#16a34a',
  '#f59e0b',
  '#f97316',
  '#dc2626',
  '#db2777',
  '#7c3aed',
  '#0f172a'
]

/** Above this many seats the roster meter becomes a continuous bar. */
export const MAX_SEAT_SEGMENTS = 24

const HEX_RE = /^#[0-9a-f]{6}$/i

/** Three latin letters, upper case — the same rule the backend enforces. */
export function normalizeTeamAbbreviation(value) {
  return String(value || '').replace(/[^a-z]/gi, '').slice(0, 3).toUpperCase()
}

export function teamColor(value) {
  return HEX_RE.test(String(value || '')) ? value : DEFAULT_TEAM_COLOR
}

function luminance(hex) {
  const channels = [1, 3, 5].map((start) => parseInt(hex.slice(start, start + 2), 16) / 255)
  const [r, g, b] = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

/** Above this luminance a team colour is bright enough to need dark ink. */
const BRIGHT_LUMINANCE = 0.42

/** True when the team colour is bright, so the ink on it is the dark one. */
export function isBrightTeamColor(value) {
  return luminance(teamColor(value)) > BRIGHT_LUMINANCE
}

/** Readable text colour on top of a team colour. */
export function teamInk(value) {
  return isBrightTeamColor(value) ? '#05070c' : '#ffffff'
}

/** CSS custom properties that paint a component in the team's livery. */
export function teamStyle(value) {
  const color = teamColor(value)
  return { '--team': color, '--team-ink': teamInk(color) }
}

export function teamFillPercent(team) {
  if (!team?.member_limit) return 0
  return Math.min(100, Math.round((team.member_count / team.member_limit) * 100))
}

export function isTeamFull(team) {
  return Boolean(team?.member_limit) && team.member_count >= team.member_limit
}

export function freeSeats(team) {
  return Math.max(0, (Number(team?.member_limit) || 0) - (Number(team?.member_count) || 0))
}

export function formatSr(value) {
  const number = Number(value)
  return Number.isFinite(number) ? number.toFixed(1) : '-'
}

/** Mean of a numeric field over a list, or null when nothing is numeric. */
export function averageOf(items, pick) {
  const values = (items || []).map(pick).map(Number).filter(Number.isFinite)
  if (!values.length) return null
  return values.reduce((sum, value) => sum + value, 0) / values.length
}
