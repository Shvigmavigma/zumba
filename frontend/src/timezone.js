import { state } from './store'

// The picker intentionally exposes one fixed UTC offset for every hour from
// -24 through +24.  JavaScript's IANA database does not contain all of those
// offsets (and some offsets change with DST), so the fixed options use a small
// `UTC+HH`/`UTC-HH` identifier and are formatted by the helpers below.
const fixedUtcOffsets = Array.from({ length: 49 }, (_, index) => index - 24)
  .filter((offset) => offset !== 3)

const fixedTimeZoneOptions = fixedUtcOffsets.map((offset) => {
  const sign = offset < 0 ? '-' : '+'
  const hours = String(Math.abs(offset)).padStart(2, '0')
  const value = `UTC${sign}${hours}`
  return { value, shortLabel: value, label: value }
})

// Keep the two real +03 zones as separate choices, since Kyiv observes DST
// while Moscow stays on UTC+03 year-round.
const cityTimeZoneOptions = [
  { value: 'Europe/Kyiv', shortLabel: 'Kyiv', label: 'Kyiv UTC+03' },
  { value: 'Europe/Moscow', shortLabel: 'MSK', label: 'MSK UTC+03' }
]

const supportedTimeZoneValues = new Set([
  ...fixedTimeZoneOptions.map((item) => item.value),
  ...cityTimeZoneOptions.map((item) => item.value)
])

function fixedOffsetMinutes(timeZone) {
  const match = /^UTC([+-])(\d{2})(?::?(\d{2}))?$/.exec(timeZone || '')
  if (!match) return null
  const hours = Number(match[2])
  const minutes = Number(match[3] || 0)
  if (hours > 24 || minutes > 59 || (hours === 24 && minutes !== 0)) return null
  const total = (hours * 60) + minutes
  return match[1] === '-' ? -total : total
}

function dateForTimeZone(value, timeZone) {
  const date = new Date(value)
  const offset = fixedOffsetMinutes(timeZone)
  return offset === null ? date : new Date(date.getTime() + (offset * 60 * 1000))
}

function formatterTimeZone(timeZone) {
  return fixedOffsetMinutes(timeZone) === null ? timeZone : 'UTC'
}

function offsetLabel(timeZone) {
  try {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone,
      timeZoneName: 'shortOffset',
      hour: '2-digit'
    }).formatToParts(new Date())
    const rawOffset = parts.find((part) => part.type === 'timeZoneName')?.value || 'GMT+0'
    const normalized = rawOffset.replace(/^GMT/, 'UTC')
    if (normalized === 'UTC' || normalized === 'UTC+0') return 'UTC+00'
    return normalized.replace(/UTC([+-])(\d{1,2})(?::(\d\d))?$/, (_, sign, hour, minutes = '') => `UTC${sign}${hour.padStart(2, '0')}${minutes ? `:${minutes}` : ''}`)
  } catch {
    return ''
  }
}

const beforeKyivAndMoscow = fixedTimeZoneOptions.filter((item) => fixedOffsetMinutes(item.value) < 180)
const afterKyivAndMoscow = fixedTimeZoneOptions.filter((item) => fixedOffsetMinutes(item.value) > 180)

// Keep the list in chronological offset order, with the two +03 choices next
// to each other instead of hiding them at the bottom of the select.
export const timeZoneOptions = [
  ...beforeKyivAndMoscow,
  ...cityTimeZoneOptions,
  ...afterKyivAndMoscow
]

export function isSupportedTimeZone(value) {
  return supportedTimeZoneValues.has(value)
}

export function localeCode() {
  return state.locale === 'ru' ? 'ru-RU' : 'en-US'
}

export function activeTimeZone() {
  return state.timeZone || 'Europe/Moscow'
}

export function formatInTimeZone(value, options = {}) {
  if (!value) return ''
  const timeZone = activeTimeZone()
  return new Intl.DateTimeFormat(localeCode(), {
    hourCycle: 'h23',
    ...options,
    timeZone: formatterTimeZone(timeZone)
  }).format(dateForTimeZone(value, timeZone))
}

export function formatDateTime(value, options = {}) {
  if (options.dateStyle || options.timeStyle) {
    return formatInTimeZone(value, {
      dateStyle: 'medium',
      timeStyle: 'short',
      ...options
    })
  }
  return formatInTimeZone(value, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    ...options
  })
}

export function formatShortDate(value, options = {}) {
  return formatInTimeZone(value, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    ...options
  })
}

export function formatDayPart(value) {
  return formatInTimeZone(value, { day: '2-digit' })
}

export function formatMonthPart(value) {
  return formatInTimeZone(value, { month: 'short' })
}

export function formatTimeOnly(value) {
  return formatInTimeZone(value, {
    hour: '2-digit',
    minute: '2-digit'
  })
}

export function dateKeyInTimeZone(value) {
  const timeZone = activeTimeZone()
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: formatterTimeZone(timeZone),
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).formatToParts(dateForTimeZone(value, timeZone))
  const data = Object.fromEntries(parts.filter((part) => part.type !== 'literal').map((part) => [part.type, part.value]))
  return `${data.year}-${data.month}-${data.day}`
}
