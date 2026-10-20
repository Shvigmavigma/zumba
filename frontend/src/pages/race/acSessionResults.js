// An Assetto Corsa session as Content Manager saves it (Progress/Sessions/*.json):
// every lap of every car with its three sector times and the number of cuts.
// From it the staff results form takes, per driver: laps, total time, best lap
// and the best time in each sector. Only laps and driver names are read: the
// file also holds the server's settings, which never leave this module.

const SECTOR_COUNT = 3
/** Sector times add up to the lap time; the game rounds each of them, hence the slack. */
const SUM_SLACK_MS = 2
const SESSION_BY_TYPE = { 2: 'qualification', 3: 'race' }
const MIN_GUESS_WORD = 4
/** "Name | 77": the league's drivers put their number after the name. */
const NUMBER_SUFFIX = /\|\s*#?(\d{1,3})\s*$/
const TRANSLIT = {
  а: 'a', б: 'b', в: 'v', г: 'g', д: 'd', е: 'e', ё: 'e', ж: 'zh', з: 'z', и: 'i', й: 'y', к: 'k', л: 'l', м: 'm', н: 'n', о: 'o', п: 'p',
  р: 'r', с: 's', т: 't', у: 'u', ф: 'f', х: 'kh', ц: 'ts', ч: 'ch', ш: 'sh', щ: 'shch', ъ: '', ы: 'y', ь: '', э: 'e', ю: 'yu', я: 'ya'
}
/** Spellings that transliteration mixes up, folded to one. */
const SPELLING_FOLDS = [['kh', 'h'], ['ks', 'x'], ['yu', 'u'], ['ya', 'a'], ['iy', 'i'], ['ii', 'i'], ['y', 'i'], ['j', 'i'], ['ie', 'e']]

/**
 * @typedef {{ laps: number, totalMs: number | null, bestLapMs: number | null, bestSectorsMs: (number | null)[], validLaps: number }} AcSessionSummary
 *   totalMs: the sum of the lap times, for the race only.
 * @typedef {{ car: number, name: string, number: number | null, race: AcSessionSummary | null, qualification: AcSessionSummary | null }} AcDriver
 * @typedef {{ userId: number, how: 'name' | 'number' | 'guess' }} AcMatch
 */

function sessionKind(session) {
  const byType = SESSION_BY_TYPE[Number(session?.type)]
  if (byType) return byType
  const name = String(session?.name ?? '').toLowerCase()
  if (name.startsWith('qual')) return 'qualification'
  return name.startsWith('race') ? 'race' : null
}

function properLap(lap) {
  return Number.isInteger(lap?.car) && lap.car >= 0 && Array.isArray(lap.sectors) && lap.sectors.length === SECTOR_COUNT && Number.isFinite(Number(lap.time))
}

/** A lap that counts for a best time: no cuts, a real lap time, sector times that add up to it. */
function validLap(lap) {
  const time = Number(lap.time)
  const sectors = lap.sectors.map(Number)
  if (Number(lap.cuts) !== 0 || !(time > 0) || sectors.some((value) => !(value > 0))) return false
  return Math.abs(sectors.reduce((sum, value) => sum + value, 0) - time) <= SUM_SLACK_MS
}

function summarize(laps, kind) {
  const valid = laps.filter(validLap)
  const timed = laps.filter((lap) => Number(lap.time) > 0)
  return {
    laps: laps.length,
    totalMs: kind === 'race' ? timed.reduce((sum, lap) => sum + Number(lap.time), 0) : null,
    bestLapMs: valid.length ? Math.min(...valid.map((lap) => Number(lap.time))) : null,
    bestSectorsMs: Array.from({ length: SECTOR_COUNT }, (_, index) => (valid.length ? Math.min(...valid.map((lap) => Number(lap.sectors[index]))) : null)),
    validLaps: valid.length
  }
}

function driverName(player) {
  const text = String(player?.name ?? '').trim()
  const number = text.match(NUMBER_SUFFIX)
  return { name: text.replace(NUMBER_SUFFIX, '').trim(), number: number ? Number(number[1]) : null }
}

/**
 * Reads a Content Manager session file.
 * @param {unknown} file  the parsed JSON
 * @returns {{ track: string, drivers: AcDriver[] }}  cars that drove at least one lap, in the file's order
 */
export function parseAcSession(file) {
  if (!file || typeof file !== 'object' || !Array.isArray(file.players) || !Array.isArray(file.sessions)) {
    throw new Error('Not a Content Manager session file')
  }
  const byCar = new Map()
  for (const session of file.sessions) {
    const kind = sessionKind(session)
    if (!kind || !Array.isArray(session.laps)) continue
    for (const lap of session.laps.filter(properLap)) {
      if (!file.players[lap.car]) continue
      const entry = byCar.get(lap.car) ?? { race: [], qualification: [] }
      byCar.set(lap.car, { ...entry, [kind]: [...entry[kind], lap] })
    }
  }
  if (!byCar.size) throw new Error('The session file has no laps')
  const drivers = [...byCar.entries()].sort((a, b) => a[0] - b[0]).map(([car, laps]) => ({
    car,
    ...driverName(file.players[car]),
    race: laps.race.length ? summarize(laps.race, 'race') : null,
    qualification: laps.qualification.length ? summarize(laps.qualification, 'qualification') : null
  }))
  return { track: String(file.track ?? ''), drivers }
}

function sectorTimes(session) {
  return session && session.validLaps > 0 ? { sectors: session.bestSectorsMs, laps: session.validLaps } : { sectors: null, laps: null }
}

/**
 * What a row of the manual results form takes from a driver: the race result
 * (laps, total time, best lap), the best lap of qualifying, and the best sector
 * times of each session with the number of valid laps behind them. A session
 * without a valid lap gives none.
 * @param {AcDriver} driver
 */
export function acRowTiming(driver) {
  const race = sectorTimes(driver.race)
  const qualification = sectorTimes(driver.qualification)
  return {
    finish_ms: driver.race?.totalMs || null,
    lap_count: driver.race?.laps ?? 0,
    best_lap_ms: driver.race?.bestLapMs ?? null,
    best_sectors_ms: race.sectors,
    valid_laps: race.laps,
    qualification_best_lap_ms: driver.qualification?.bestLapMs ?? null,
    qualification_best_sectors_ms: qualification.sectors,
    qualification_valid_laps: qualification.laps
  }
}

function plain(value) {
  const lower = String(value ?? '').normalize('NFC').toLowerCase()
  const latin = [...lower].map((char) => TRANSLIT[char] ?? char).join('')
  return latin.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, ' ').trim()
}

/** A name as it is compared: one alphabet, no accents or punctuation, spelling variants folded. */
function nameKey(value) {
  const folded = SPELLING_FOLDS.reduce((text, [from, to]) => text.replaceAll(from, to), plain(value))
  return folded.replace(/([a-z])\1+/g, '$1')
}

function pilotKeys(pilot) {
  const first = pilot.first_name ?? ''
  const last = pilot.last_name ?? ''
  return [`${first} ${last}`, `${last} ${first}`, pilot.nickname, pilot.login].map(nameKey).filter(Boolean)
}

/** Key → the one item that has it; keys shared by several items are dropped. */
function uniqueIndex(items, keysOf) {
  const owners = new Map()
  for (const item of items) {
    for (const key of new Set(keysOf(item))) owners.set(key, owners.has(key) ? null : item)
  }
  return new Map([...owners].filter(([, owner]) => owner !== null))
}

function guessWords(text) {
  return nameKey(text).split(' ').filter((word) => word.length >= MIN_GUESS_WORD)
}

/**
 * Ties the file's drivers to the race's pilots: by the whole name (first and last
 * name in either order, nickname or login), then by the number after the name,
 * and last by a single word that one driver and one pilot alone share — a guess
 * for a person to confirm. A pilot is given to one car only.
 * @param {{ car: number, name: string, number: number | null }[]} drivers
 * @param {object[]} pilots  the race's entry list: user_id, first_name, last_name, nickname, login, pilot_number
 * @returns {Map<number, AcMatch>}  by car
 */
export function matchAcDrivers(drivers, pilots) {
  const matches = new Map()
  const taken = new Set()
  const free = () => pilots.filter((pilot) => !taken.has(pilot.user_id))
  const open = () => drivers.filter((driver) => !matches.has(driver.car))
  const tie = (driver, pilot, how) => {
    if (!pilot || taken.has(pilot.user_id)) return
    matches.set(driver.car, { userId: pilot.user_id, how })
    taken.add(pilot.user_id)
  }

  const byName = uniqueIndex(pilots, pilotKeys)
  for (const driver of drivers) tie(driver, byName.get(nameKey(driver.name)), 'name')

  const byNumber = uniqueIndex(free(), (pilot) => [Number(pilot.race_number ?? pilot.pilot_number)].filter(Number.isFinite))
  for (const driver of open()) {
    if (driver.number !== null) tie(driver, byNumber.get(driver.number), 'number')
  }

  const pilotWord = uniqueIndex(free(), (pilot) => [...guessWords(pilot.first_name), ...guessWords(pilot.last_name), ...guessWords(pilot.nickname)])
  const driverWord = uniqueIndex(open(), (driver) => guessWords(driver.name))
  for (const [word, driver] of driverWord) {
    if (!matches.has(driver.car)) tie(driver, pilotWord.get(word), 'guess')
  }
  return matches
}
