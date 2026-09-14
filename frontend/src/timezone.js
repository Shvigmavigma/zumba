import { state } from './store'

const preferredShortLabels = {
  UTC: 'UTC',
  'Europe/Kyiv': 'Kyiv',
  'Europe/Moscow': 'MSK',
  'Asia/Yekaterinburg': 'YEKT',
  'Asia/Almaty': 'ALM',
  'Asia/Tashkent': 'TAS',
  'Europe/London': 'LON',
  'Europe/Berlin': 'BER',
  'Africa/Cairo': 'CAI',
  'Africa/Johannesburg': 'JNB',
  'America/New_York': 'NYC',
  'America/Chicago': 'CHI',
  'America/Denver': 'DEN',
  'America/Los_Angeles': 'LAX',
  'America/Sao_Paulo': 'SAO',
  'Asia/Dubai': 'DXB',
  'Asia/Kolkata': 'DEL',
  'Asia/Shanghai': 'SHA',
  'Asia/Singapore': 'SIN',
  'Asia/Tokyo': 'TYO',
  'Asia/Seoul': 'SEL',
  'Australia/Sydney': 'SYD',
  'Pacific/Auckland': 'AKL'
}

const fallbackTimeZones = [
  { value: 'UTC', shortLabel: 'UTC' },
  { value: 'Europe/Kyiv', shortLabel: 'Kyiv' },
  { value: 'Europe/Moscow', shortLabel: 'MSK' },
  { value: 'Asia/Yekaterinburg', shortLabel: 'YEKT' },
  { value: 'Asia/Almaty', shortLabel: 'ALM' },
  { value: 'Asia/Tashkent', shortLabel: 'TAS' },
  { value: 'Europe/London', shortLabel: 'LON' },
  { value: 'Europe/Berlin', shortLabel: 'BER' },
  { value: 'Africa/Cairo', shortLabel: 'CAI' },
  { value: 'Africa/Johannesburg', shortLabel: 'JNB' },
  { value: 'America/New_York', shortLabel: 'NYC' },
  { value: 'America/Chicago', shortLabel: 'CHI' },
  { value: 'America/Denver', shortLabel: 'DEN' },
  { value: 'America/Los_Angeles', shortLabel: 'LAX' },
  { value: 'America/Sao_Paulo', shortLabel: 'SAO' },
  { value: 'Asia/Dubai', shortLabel: 'DXB' },
  { value: 'Asia/Kolkata', shortLabel: 'DEL' },
  { value: 'Asia/Shanghai', shortLabel: 'SHA' },
  { value: 'Asia/Singapore', shortLabel: 'SIN' },
  { value: 'Asia/Tokyo', shortLabel: 'TYO' },
  { value: 'Asia/Seoul', shortLabel: 'SEL' },
  { value: 'Australia/Sydney', shortLabel: 'SYD' },
  { value: 'Pacific/Auckland', shortLabel: 'AKL' }
]

function availableTimeZones() {
  let values = []
  try {
    values = typeof Intl.supportedValuesOf === 'function' ? Intl.supportedValuesOf('timeZone') : []
  } catch {
    values = []
  }
  const source = values.length ? [...values, ...Object.keys(preferredShortLabels)] : fallbackTimeZones.map((item) => item.value)
  // Keep a few non-canonical UTC aliases available for users who need them.
  return Array.from(new Set([...source, 'UTC', 'GMT', 'Etc/UTC', 'Etc/GMT'])).sort((left, right) => left.localeCompare(right))
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

export const timeZoneOptions = availableTimeZones().map((value) => {
  const shortLabel = preferredShortLabels[value]
  const offset = offsetLabel(value)
  return {
    value,
    shortLabel: shortLabel || value,
    label: shortLabel ? `${shortLabel} ${offset}` : `${value}${offset ? ` ${offset}` : ''}`
  }
})

export function localeCode() {
  return state.locale === 'ru' ? 'ru-RU' : 'en-US'
}

export function activeTimeZone() {
  return state.timeZone || 'Europe/Moscow'
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
