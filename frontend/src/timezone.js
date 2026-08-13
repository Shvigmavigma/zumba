import { state } from './store'

const baseTimeZoneOptions = [
  { value: 'UTC', shortLabel: 'UTC' },
  { value: 'Europe/Kyiv', shortLabel: 'Kyiv' },
  { value: 'Europe/Moscow', shortLabel: 'MSK' },
  { value: 'Europe/London', shortLabel: 'LON' },
  { value: 'Europe/Berlin', shortLabel: 'BER' },
  { value: 'America/New_York', shortLabel: 'NYC' },
  { value: 'Asia/Dubai', shortLabel: 'DXB' },
  { value: 'Asia/Tokyo', shortLabel: 'TYO' }
]

function offsetLabel(timeZone) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone,
    timeZoneName: 'shortOffset',
    hour: '2-digit'
  }).formatToParts(new Date())
  const rawOffset = parts.find((part) => part.type === 'timeZoneName')?.value || 'GMT'
  const normalized = rawOffset.replace('GMT', 'UTC')
  if (normalized === 'UTC') return 'UTC+00'
  return normalized.replace(/UTC([+-])(\d)$/, 'UTC$10$2')
}

export const timeZoneOptions = baseTimeZoneOptions.map((option) => ({
  ...option,
  label: `${option.shortLabel} ${offsetLabel(option.value)}`
}))

export function localeCode() {
  return state.locale === 'ru' ? 'ru-RU' : 'en-US'
}

export function activeTimeZone() {
  return state.timeZone || 'UTC'
}

export function formatInTimeZone(value, options = {}) {
  if (!value) return ''
  return new Intl.DateTimeFormat(localeCode(), {
    timeZone: activeTimeZone(),
    hourCycle: 'h23',
    ...options
  }).format(new Date(value))
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
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: activeTimeZone(),
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).formatToParts(new Date(value))
  const data = Object.fromEntries(parts.filter((part) => part.type !== 'literal').map((part) => [part.type, part.value]))
  return `${data.year}-${data.month}-${data.day}`
}
