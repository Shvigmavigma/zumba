// Who holds each timing sector of a track. ACC's result files (kept with every
// finished race, for the race and for qualifying) list every car's best time
// in each of the lap's three sectors, taken from its valid laps. A car is tied
// to a site pilot by its race number through the race's result rows; cars
// without a site account hold nothing. Results entered by hand (Assetto Corsa)
// have no such file: there the sector times come with the result rows, put in
// from the game's own session file when the results are entered. A pilot whose
// laps the stewards annulled holds nothing.
import { lapsAnnulled } from '../race/raceClassification.js'

export const SECTOR_COUNT = 3
/** ACC writes this where a car has no time. */
const ACC_NO_TIME_MS = 2147483647
const BRAND_BLUE = '#1652d8'
const HEX_COLOR = /^#(?:[0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})$/i
// Qualifying is run before the race, so on the same day it set its times first.
const SESSIONS = ['qualification', 'race']
/** Where a result row keeps a session's sector times and the number of valid laps they were taken from. */
const ROW_FIELDS = {
  qualification: { sectors: 'qualification_best_sectors_ms', laps: 'qualification_valid_laps' },
  race: { sectors: 'best_sectors_ms', laps: 'valid_laps' }
}

/**
 * @typedef {{ userId: number, name: string, nickname: string, number: number | null, color: string, avatar: string }} SectorPilot
 * @typedef {{ n: number, ms: number, pilot: SectorPilot, session: 'race' | 'qualification', raceId: number, raceName: string, raceDate: string }} SectorRecord
 * @typedef {object} SectorRecords
 * @property {(SectorRecord | null)[]} sectors  One per sector, null while nobody has a time in it.
 * @property {number | null} idealMs  The three best sectors put together; null until every sector has a time.
 * @property {number} validLaps  Valid laps of site pilots the times were taken from.
 * @property {number} pilots  Site pilots with a time in at least one sector.
 * @property {number} sessions  Sessions that had such times.
 */

/**
 * A pilot's profile colour, safe to put into a style: a plain hex colour, or the fallback.
 * @param {string | null | undefined} value
 * @param {string} [fallback]
 * @returns {string}
 */
export function pilotColor(value, fallback = BRAND_BLUE) {
  const color = String(value ?? '').trim()
  return HEX_COLOR.test(color) ? color.toLowerCase() : fallback
}

function resultRows(race) {
  if (Array.isArray(race?.results)) return race.results
  return Array.isArray(race?.results?.rows) ? race.results.rows : []
}

function validTime(value) {
  const ms = Number(value)
  return Number.isFinite(ms) && ms > 0 && ms < ACC_NO_TIME_MS ? ms : null
}

/**
 * How a site pilot is shown next to a record: the profile from the race's
 * entry list, or what the result row says when they have left it since.
 * @param {object} race
 * @param {object} row  result row with a user_id
 * @returns {SectorPilot}
 */
export function sectorPilot(race, row) {
  const userId = Number(row.user_id)
  const profile = (race.registered_pilots || []).find((pilot) => Number(pilot.user_id) === userId) || {}
  const nickname = profile.nickname || row.nickname || profile.login || row.login || ''
  const fullName = [profile.first_name ?? row.first_name, profile.last_name ?? row.last_name].filter(Boolean).join(' ').trim()
  const number = Number(profile.pilot_number ?? row.race_number ?? row.pilot_number)
  return {
    userId,
    name: fullName || nickname || row.driver_name || '',
    nickname,
    number: Number.isFinite(number) ? number : null,
    color: pilotColor(profile.avatar_color),
    avatar: profile.avatar_url || ''
  }
}

/**
 * One session of a race as the simulator's file tells it: each site pilot's best
 * sector times and how many valid laps of theirs stand behind them. Null without a file.
 */
function fileEntries(race, session, rowByNumber) {
  const raw = race.results?.[session]?.raw
  const lines = raw?.sessionResult?.leaderBoardLines
  if (!Array.isArray(lines)) return null
  const siteCars = new Set()
  const entries = []
  for (const line of lines) {
    const row = rowByNumber.get(Number(line?.car?.raceNumber))
    if (!row) continue
    siteCars.add(line.car.carId)
    entries.push({ row, splits: Array.isArray(line.timing?.bestSplits) ? line.timing.bestSplits : [] })
  }
  const validLaps = (Array.isArray(raw.laps) ? raw.laps : []).filter((lap) => lap?.isValidForBest && siteCars.has(lap.carId)).length
  return { entries, validLaps }
}

/** The same from the result rows themselves, for results entered by hand. */
function rowEntries(rows, session) {
  const fields = ROW_FIELDS[session]
  const entries = rows.filter((row) => Array.isArray(row[fields.sectors])).map((row) => ({ row, splits: row[fields.sectors], laps: row[fields.laps] }))
  const timed = entries.filter((entry) => entry.splits.some((value) => validTime(value) !== null))
  const validLaps = timed.reduce((sum, entry) => sum + (Number.isInteger(entry.laps) && entry.laps > 0 ? entry.laps : 0), 0)
  return { entries, validLaps }
}

function raceTime(race) {
  const time = new Date(race?.datetime_start).getTime()
  return Number.isFinite(time) ? time : Infinity
}

/**
 * The best time in each sector among site pilots, over every session of the
 * given races. An equal time stays with whoever set it first.
 * @param {object[] | null | undefined} races  finished races of one track, as the races API returns them
 * @returns {SectorRecords}
 */
export function sectorRecords(races) {
  const ordered = [...(races || [])].sort((a, b) => raceTime(a) - raceTime(b) || Number(a?.id) - Number(b?.id))
  const sectors = Array.from({ length: SECTOR_COUNT }, () => null)
  const timedPilots = new Set()
  let validLaps = 0
  let sessions = 0

  for (const race of ordered) {
    const siteRows = resultRows(race).filter((row) => row?.user_id && !lapsAnnulled(row))
    if (!siteRows.length) continue
    const rowByNumber = new Map(siteRows.map((row) => [Number(row.race_number), row]))
    for (const session of SESSIONS) {
      const { entries, validLaps: sessionLaps } = fileEntries(race, session, rowByNumber) ?? rowEntries(siteRows, session)
      let timed = false
      for (const { row, splits } of entries) {
        for (let index = 0; index < SECTOR_COUNT; index += 1) {
          const ms = validTime(splits[index])
          if (ms === null) continue
          timed = true
          timedPilots.add(Number(row.user_id))
          if (sectors[index] && sectors[index].ms <= ms) continue
          sectors[index] = { n: index + 1, ms, pilot: sectorPilot(race, row), session, raceId: race.id, raceName: race.name || '', raceDate: race.datetime_start || '' }
        }
      }
      if (!timed) continue
      sessions += 1
      validLaps += sessionLaps
    }
  }

  return {
    sectors,
    idealMs: sectors.every(Boolean) ? sectors.reduce((sum, sector) => sum + sector.ms, 0) : null,
    validLaps,
    pilots: timedPilots.size,
    sessions
  }
}

/**
 * The track's lap record as the header shows it, from the first row of the
 * records table: the time with the look of the pilot who set it.
 * @param {object | null | undefined} row  top row of the track's records
 * @param {object[]} races  the track's races, to find the pilot's profile in
 * @returns {{ ms: number, session: string | null, raceId: number, raceName: string, raceDate: string, car: string, pilot: SectorPilot | { userId: null } } | null}
 */
export function lapRecord(row, races) {
  const ms = validTime(row?.bestLapMs)
  if (ms === null) return null
  const race = (races || []).find((item) => item.id === row.raceId) || {}
  const number = Number(row.pilotNumber)
  const pilot = row.user_id
    ? { ...sectorPilot(race, { user_id: row.user_id, race_number: row.pilotNumber, driver_name: row.pilotName }) }
    : { userId: null, name: row.pilotName || '', nickname: '', number: Number.isFinite(number) ? number : null, color: BRAND_BLUE, avatar: '' }
  return {
    ms,
    session: row.bestLapSession || null,
    raceId: row.raceId,
    raceName: row.raceName || '',
    raceDate: row.raceDate || '',
    car: row.carModel || '',
    pilot: { ...pilot, name: pilot.name || row.pilotName || '' }
  }
}

function pad(value, length) {
  return String(value).padStart(length, '0')
}

/**
 * A sector or lap time: "34.747", or "1:02.123" from a minute up.
 * @param {number | null | undefined} ms
 * @returns {string}
 */
export function formatSectorTime(ms) {
  const total = Math.round(Number(ms))
  if (!Number.isFinite(total) || total <= 0) return '—'
  const minutes = Math.floor(total / 60000)
  const seconds = Math.floor((total % 60000) / 1000)
  const millis = pad(total % 1000, 3)
  return minutes ? `${minutes}:${pad(seconds, 2)}.${millis}` : `${seconds}.${millis}`
}

/**
 * A difference between two times with its sign: "+0.303", "−1.250".
 * @param {number | null | undefined} ms
 * @returns {string}
 */
export function formatGap(ms) {
  if (ms === null || ms === undefined || !Number.isFinite(Number(ms))) return ''
  const total = Math.round(Number(ms))
  const sign = total > 0 ? '+' : total < 0 ? '−' : ''
  return `${sign}${(Math.abs(total) / 1000).toFixed(3)}`
}
