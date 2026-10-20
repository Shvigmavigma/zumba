// Pure helpers for the championships page. No Vue, no store: easy to test and
// shared by the page and its sub-components.
import { formatPilotNumber } from '../../pilotDisplay.js'

export const STANDINGS_PAGE_SIZE = 18

export const SCORING_OPTIONS = [
  { value: 'fia', label: 'FIA 25-18-15' },
  { value: 'endurance', label: 'Endurance 38-27-23' },
  { value: 'linear', label: 'Linear N+1' }
]

const ASSET_GAMES = ['ACC', 'AC', 'iRacing', 'LMU']
const EMPTY_ASSETS = { tracks: [], classes: [] }

const STATUS_KEYS = {
  draft: 'statuses.draft',
  registration_open: 'statuses.registration_open',
  active: 'statuses.ongoing',
  upcoming: 'statuses.upcoming',
  not_started: 'statuses.not_started',
  ongoing: 'statuses.ongoing',
  finished: 'statuses.finished'
}

const STATUS_TONES = {
  registration_open: 'green',
  active: 'blue',
  ongoing: 'red',
  upcoming: 'amber',
  not_started: 'blue',
  draft: 'amber'
}

export function defaultStage() {
  return {
    name: '',
    datetime_start: '',
    track: '',
    car_class: '',
    server_link: '',
    lmu_results_at: '',
    has_qualification: true,
    scoring_system: 'fia',
    pole_bonus_enabled: false,
    is_team_event: null
  }
}

export function defaultChampionshipForm() {
  return {
    name: '',
    description: '',
    classes: [],
    registration_start: '',
    registration_end: '',
    championship_start: '',
    championship_end: '',
    video_url: '',
    game: 'ACC',
    car_change_allowed: false,
    scoring_system: 'fia',
    pole_bonus_enabled: false,
    is_team_event: false,
    is_published: false,
    stages: []
  }
}

/** Track/class lists of /race-assets for one game (ACC lives at the root for older data). */
export function assetConfigForGame(raceAssets, game) {
  if (!ASSET_GAMES.includes(game)) return EMPTY_ASSETS
  if (game === 'ACC') return raceAssets?.games?.ACC || raceAssets || EMPTY_ASSETS
  return raceAssets?.games?.[game] || EMPTY_ASSETS
}

/** Unique cars (case-insensitive) of the given classes, in asset order. */
export function carsForClasses(config, classes) {
  const seen = new Set()
  return (config?.classes || [])
    .filter((item) => classes.has(item.name))
    .flatMap((item) => item.cars || [])
    .filter((car) => {
      const key = car.toLowerCase()
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
}

/** A new list with `name` added, or removed when it is already there. */
export function toggleInList(list, name) {
  return list.includes(name) ? list.filter((item) => item !== name) : [...list, name]
}

/** Switching the game clears classes and per-stage track/class (they belong to the old game). */
export function resetForGame(form) {
  return {
    ...form,
    classes: [],
    stages: (form.stages || []).map((stage) => ({
      ...stage,
      track: '',
      car_class: '',
      lmu_results_at: form.game === 'LMU' ? (stage.lmu_results_at || stage.datetime_start) : ''
    }))
  }
}

export function toIso(value) {
  return new Date(value).toISOString()
}

export function optionalIso(value) {
  return value ? toIso(value) : null
}

/** ISO date → value for <input type="datetime-local"> in the browser's zone. */
export function toLocalInput(value) {
  if (!value) return ''
  const date = new Date(value)
  const offset = date.getTimezoneOffset() * 60000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

export function pilotNumberDraft(value) {
  const number = Number(value)
  return Number.isInteger(number) && number >= 0 ? formatPilotNumber(number) : ''
}

/** @throws {Error} with `message` unless the value is exactly three digits. */
export function parsePilotNumber(value, message) {
  const raw = String(value ?? '').trim()
  if (!/^\d{3}$/.test(raw)) throw new Error(message)
  return Number(raw)
}

/** @throws {Error} with `message` when no car is given. */
export function parseCar(value, message) {
  const car = String(value || '').trim()
  if (!car) throw new Error(message)
  return car
}

/** Drops descriptions broken by a wrong encoding (replacement chars or ??? runs). */
export function cleanText(value) {
  const text = String(value || '').trim()
  if (!text || text.includes('�') || /\?{3,}/.test(text)) return ''
  return text
}

export function scoringLabel(value) {
  return SCORING_OPTIONS.find((option) => option.value === value)?.label || String(value || '').toUpperCase()
}

/** i18n key for a championship or stage status (a running season reads as "ongoing"). */
export function statusKey(status) {
  return STATUS_KEYS[status] || ''
}

export function statusTone(status) {
  return STATUS_TONES[status] || ''
}

/** Russian-style plural bucket: 'One' | 'Few' | 'Many' (English uses One/Many). */
export function pluralBucket(count, locale) {
  if (locale !== 'ru') return count === 1 ? 'One' : 'Many'
  const mod10 = count % 10
  const mod100 = count % 100
  if (mod10 === 1 && mod100 !== 11) return 'One'
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return 'Few'
  return 'Many'
}

export function stageRound(stage, index) {
  return stage?.championship_round ?? index + 1
}

/**
 * Season overview: stages in round order, how many are finished, the current
 * stage (live, otherwise the first unfinished one) and each stage's phase.
 */
export function seasonProgress(stages = []) {
  const list = [...stages].sort((a, b) => (
    (a.championship_round ?? 0) - (b.championship_round ?? 0)
    || new Date(a.datetime_start).getTime() - new Date(b.datetime_start).getTime()
  ))
  const finished = list.filter((stage) => stage.status === 'finished').length
  const current = list.find((stage) => stage.status === 'ongoing') || list.find((stage) => stage.status !== 'finished') || null
  const phaseOf = (stage) => {
    if (stage.status === 'finished') return 'done'
    if (stage.status === 'ongoing') return 'live'
    if (current && stage.id === current.id) return 'next'
    return 'future'
  }
  return {
    stages: list.map((stage, index) => ({ stage, round: stageRound(stage, index), phase: phaseOf(stage) })),
    total: list.length,
    finished,
    current,
    percent: list.length ? Math.round((finished / list.length) * 100) : 0
  }
}

/**
 * How far the season has come along the line between its stages: one value
 * from 0 to 1 for every stretch between two neighbouring stages. A stretch is
 * full once the stage it leads to has been raced (or is running); the stretch
 * out of the last stage raced fills with the time passed on the way to the
 * next one; the stretches beyond are empty.
 * @param {{ stage: { datetime_start: string }, phase: string }[]} items  seasonProgress(...).stages
 * @param {number} [now]
 * @returns {number[]}
 */
export function seasonRailFill(items = [], now = Date.now()) {
  const reached = (item) => item.phase === 'done' || item.phase === 'live'
  return items.slice(1).map((to, index) => {
    const from = items[index]
    if (reached(to)) return 1
    if (!reached(from)) return 0
    const start = new Date(from.stage.datetime_start).getTime()
    const end = new Date(to.stage.datetime_start).getTime()
    if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return 0
    return Math.min(1, Math.max(0, (now - start) / (end - start)))
  })
}

/**
 * Where registration stands: 'draft' (unpublished), 'open', 'soon' (opens
 * later) or 'closed'.
 */
export function registrationPhase(championship, now = Date.now()) {
  if (!championship) return 'closed'
  if (championship.status === 'draft' || championship.is_published === false) return 'draft'
  if (championship.status === 'registration_open') return 'open'
  const opensAt = new Date(championship.registration_start).getTime()
  return Number.isFinite(opensAt) && opensAt > now ? 'soon' : 'closed'
}

/** Standings rows with overall rank and the gap to the leader. */
export function rankStandings(standings = []) {
  const leaderPoints = Number(standings[0]?.points) || 0
  return standings.map((row, index) => ({
    ...row,
    rank: index + 1,
    gap: index === 0 ? 0 : leaderPoints - (Number(row.points) || 0)
  }))
}
