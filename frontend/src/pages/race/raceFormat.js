// Pure formatting and parsing helpers for the race page. No component state
// lives here, so every function can be shared by the page and its sections.
import { Cloud, CloudDrizzle, CloudLightning, CloudRain, CloudSun, Sun } from 'lucide-vue-next'
import { formatPilotNumber } from '../../pilotDisplay'

/** Lucide icon per weather condition key used by the API. */
export const WEATHER_ICONS = {
  clear: Sun,
  partly_cloudy: CloudSun,
  overcast: Cloud,
  light_rain: CloudDrizzle,
  heavy_rain: CloudRain,
  storm: CloudLightning
}

// Times are told from "no time" in one place (raceTime.js); they are passed on here for the sections that import this module.
export { ACC_MAX_TIME_MS, formatDuration, isAccMaxTime, timeLabel, validTimeMs } from './raceTime'

export function normalizeAccPlayerId(value) {
  const raw = String(value || '').trim()
  return raw.toUpperCase().startsWith('S') ? raw.slice(1) : raw
}

export function accPlayerId(value) {
  const raw = String(value || '').trim()
  if (!raw) return ''
  return raw.toUpperCase().startsWith('S') ? raw : `S${raw}`
}

export function accLineDriver(line) {
  if (line.currentDriver && Object.keys(line.currentDriver).length) return line.currentDriver
  return Array.isArray(line.car?.drivers) ? line.car.drivers[0] || {} : {}
}

export function accDriverName(driver) {
  const name = [driver.firstName, driver.lastName].filter(Boolean).join(' ').trim()
  return name || driver.shortName || ''
}

/**
 * Parses "ss.mmm", "mm:ss.mmm" or "hh:mm:ss.mmm" into milliseconds.
 * @param {string} value
 * @param {boolean} required
 * @param {string} invalidMessage error text thrown for bad input
 */
export function parseDurationMs(value, required, invalidMessage) {
  const raw = String(value || '').trim()
  if (!raw) {
    if (required) throw new Error(invalidMessage)
    return null
  }
  const parts = raw.split(':').map((part) => Number(part.replace(',', '.')))
  if (parts.some((part) => !Number.isFinite(part))) throw new Error(invalidMessage)
  let seconds = 0
  if (parts.length === 1) seconds = parts[0]
  else if (parts.length === 2) seconds = parts[0] * 60 + parts[1]
  else if (parts.length === 3) seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
  else throw new Error(invalidMessage)
  return Math.round(seconds * 1000)
}

export function pilotNumberDraft(value) {
  const number = Number(value)
  return Number.isInteger(number) && number > 0 ? formatPilotNumber(number) : ''
}

/** Race numbers are three digits, 001–999; 000 is rejected by the API. */
export function parsePilotNumberValue(value, invalidMessage) {
  const raw = String(value ?? '').trim()
  if (!/^[0-9]{3}$/.test(raw) || raw === '000') throw new Error(invalidMessage)
  return Number(raw)
}

/**
 * Live check for the number field: '' (fine or still typing), 'format' or 'zero'.
 * Only reports a problem once the value cannot become valid by typing more.
 */
export function pilotNumberIssue(value) {
  const raw = String(value ?? '').trim()
  if (!raw) return ''
  if (!/^[0-9]*$/.test(raw) || raw.length > 3) return 'format'
  if (raw.length === 3 && raw === '000') return 'zero'
  return ''
}

export function modHref(value) {
  const raw = String(value || '').trim()
  if (!raw) return '#'
  if (/^https?:\/\//i.test(raw)) return raw
  if (/^\/\//.test(raw)) return `https:${raw}`
  return `https://${raw}`
}

/** True when the server field holds a link rather than an in-game server name. */
export function isLinkLike(value) {
  return /^(https?:)?\/\//i.test(String(value || '').trim()) || /^www\./i.test(String(value || '').trim())
}

/** Full name, then nickname, then login, then the given fallback. */
export function personName(item, fallback = '') {
  const fullName = [item?.first_name, item?.last_name].filter(Boolean).join(' ')
  return fullName || item?.nickname || item?.login || fallback
}

export function numberLabel(item) {
  return item?.pilot_number !== null && item?.pilot_number !== undefined ? `#${formatPilotNumber(item.pilot_number)}` : `ID ${item?.user_id}`
}

export function resultBestLapMs(row) {
  return row?.best_lap_ms ?? row?.bestLap ?? row?.timing?.bestLap ?? null
}

export function resultFinishMs(row) {
  return row?.adjusted_finish_ms ?? row?.finish_ms ?? row?.totalTime ?? row?.timing?.totalTime ?? null
}

export function resultQualificationBestLapMs(row) {
  return row?.qualification_best_lap_ms ?? row?.qualificationBestLapMs ?? null
}

/** Mirrors `v-model.number`: numeric input becomes a number, anything else stays as typed. */
export function looseNumber(value) {
  const number = Number.parseFloat(value)
  return Number.isNaN(number) ? value : number
}
