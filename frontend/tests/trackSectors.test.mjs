import assert from 'node:assert/strict'
import test from 'node:test'
import { formatGap, formatSectorTime, lapRecord, pilotColor, sectorRecords } from '../src/pages/pilots/trackSectors.js'

const ACC_MAX = 2147483647

function line(raceNumber, bestSplits, carId = raceNumber) {
  return { car: { carId, raceNumber }, timing: { bestSplits } }
}

function session(lines, laps = []) {
  return { raw: { sessionResult: { leaderBoardLines: lines }, laps } }
}

/** A finished race: rows link a car's number to a site pilot, registered_pilots carry the look. */
function race({ id = 1, date = '2026-09-01T17:00:00Z', rows, pilots = [], raceSession, qualification }) {
  return {
    id,
    name: `Round ${id}`,
    datetime_start: date,
    registered_pilots: pilots,
    results: { rows, ...(raceSession ? { race: raceSession } : {}), ...(qualification ? { qualification } : {}) }
  }
}

const rows = [
  { race_number: 7, user_id: 70, nickname: 'seven' },
  { race_number: 12, user_id: 120, nickname: 'twelve' },
  { race_number: 99, user_id: null, driver_name: 'Guest Driver' }
]
const pilots = [
  { user_id: 70, nickname: 'seven', first_name: 'Sam', last_name: 'Seven', pilot_number: 7, avatar_color: '#ff8800', avatar_url: '/api/uploads/avatars/users/70.png' },
  { user_id: 120, nickname: 'twelve', first_name: '', last_name: '', pilot_number: 12, avatar_color: 'not-a-colour', avatar_url: null }
]

test('each sector goes to the site pilot with the fastest time in it, whichever session it was set in', () => {
  const records = sectorRecords([
    race({
      rows,
      pilots,
      raceSession: session([line(7, [34800, 49500, 33900]), line(12, [34700, 49900, 33800])]),
      qualification: session([line(7, [34900, 49400, 33700]), line(12, [34750, 50100, 33950])])
    })
  ])

  assert.deepEqual(records.sectors.map((sector) => [sector.n, sector.ms, sector.pilot.userId, sector.session]), [
    [1, 34700, 120, 'race'],
    [2, 49400, 70, 'qualification'],
    [3, 33700, 70, 'qualification']
  ])
  assert.equal(records.idealMs, 34700 + 49400 + 33700)
  assert.equal(records.pilots, 2)
})

test('a holder comes with the name, number, colour and avatar of their profile', () => {
  const records = sectorRecords([race({ rows, pilots, raceSession: session([line(7, [34800, 49500, 33900]), line(12, [34700, 49900, 33800])]) })])
  const [first, second] = records.sectors

  assert.deepEqual(first.pilot, { userId: 120, name: 'twelve', nickname: 'twelve', number: 12, color: '#1652d8', avatar: '' })
  assert.deepEqual(second.pilot, { userId: 70, name: 'Sam Seven', nickname: 'seven', number: 7, color: '#ff8800', avatar: '/api/uploads/avatars/users/70.png' })
  assert.equal(first.raceId, 1)
  assert.equal(first.raceName, 'Round 1')
})

test('a car without a site account, or without a valid lap, holds nothing', () => {
  const records = sectorRecords([
    race({
      rows,
      pilots,
      raceSession: session([
        line(99, [30000, 40000, 30000]),
        line(7, [ACC_MAX, ACC_MAX, ACC_MAX]),
        line(12, [34700, 0, 33800]),
        line(55, [20000, 20000, 20000])
      ])
    })
  ])

  assert.deepEqual(records.sectors.map((sector) => sector && [sector.ms, sector.pilot.userId]), [[34700, 120], null, [33800, 120]])
  // No lap can be put together while a sector has no time.
  assert.equal(records.idealMs, null)
  assert.equal(records.pilots, 1)
})

test('an equal time stays with whoever set it first', () => {
  const later = race({ id: 2, date: '2026-09-20T17:00:00Z', rows, pilots, raceSession: session([line(7, [34700, 49000, 33000])]) })
  const earlier = race({ id: 1, date: '2026-09-01T17:00:00Z', rows, pilots, raceSession: session([line(12, [34700, 49900, 33800])]) })

  const records = sectorRecords([later, earlier])

  assert.deepEqual(records.sectors.map((sector) => [sector.pilot.userId, sector.raceId]), [[120, 1], [70, 2], [70, 2]])
})

test('valid laps of site pilots are counted, others are not', () => {
  const laps = [
    { carId: 7, isValidForBest: true, splits: [1, 2, 3] },
    { carId: 7, isValidForBest: false, splits: [1, 2, 3] },
    { carId: 12, isValidForBest: true, splits: [1, 2, 3] },
    { carId: 99, isValidForBest: true, splits: [1, 2, 3] }
  ]
  const records = sectorRecords([race({ rows, pilots, raceSession: session([line(7, [34800, 49500, 33900]), line(12, [34700, 49900, 33800]), line(99, [1, 1, 1])], laps) })])

  assert.equal(records.validLaps, 2)
  assert.equal(records.sessions, 1)
})

test('races without sector times give an empty result, not an error', () => {
  const manual = race({ rows: [{ race_number: 7, user_id: 70, best_lap_ms: 100000 }], pilots })
  for (const input of [[], null, undefined, [manual], [{ id: 3, results: null }], [{ id: 4, results: [{ user_id: 1 }] }]]) {
    const records = sectorRecords(input)
    assert.deepEqual(records.sectors, [null, null, null])
    assert.equal(records.idealMs, null)
    assert.equal(records.validLaps, 0)
  }
})

test('the result does not depend on the order the races come in and leaves them untouched', () => {
  const a = race({ id: 1, date: '2026-09-01T17:00:00Z', rows, pilots, raceSession: session([line(7, [34800, 49500, 33900])]) })
  const b = race({ id: 2, date: '2026-09-20T17:00:00Z', rows, pilots, raceSession: session([line(12, [34700, 49900, 33800])]) })
  const snapshot = JSON.stringify([a, b])

  assert.deepEqual(sectorRecords([a, b]), sectorRecords([b, a]))
  assert.equal(JSON.stringify([a, b]), snapshot)
})

test('a pilot colour is used only when it is a plain hex colour', () => {
  assert.equal(pilotColor('#FF8800'), '#ff8800')
  assert.equal(pilotColor('#abc'), '#abc')
  assert.equal(pilotColor('red'), '#1652d8')
  assert.equal(pilotColor('#12345'), '#1652d8')
  assert.equal(pilotColor('url(javascript:1)'), '#1652d8')
  assert.equal(pilotColor(null, '#000000'), '#000000')
})

test('sector times and gaps read like a timing screen', () => {
  assert.equal(formatSectorTime(34747), '34.747')
  assert.equal(formatSectorTime(9005), '9.005')
  assert.equal(formatSectorTime(62123), '1:02.123')
  assert.equal(formatSectorTime(null), '—')
  assert.equal(formatSectorTime(0), '—')
  assert.equal(formatGap(303), '+0.303')
  assert.equal(formatGap(-1250), '−1.250')
  assert.equal(formatGap(0), '0.000')
  assert.equal(formatGap(null), '')
})

test('the lap record comes with the look of the pilot who set it', () => {
  const races = [race({ id: 5, rows, pilots })]
  const top = { user_id: 70, pilotName: 'Sam Seven', pilotNumber: 7, bestLapMs: 118037, bestLapSession: 'qualification', raceId: 5, raceName: 'Round 5', raceDate: '2026-09-01T17:00:00Z', carModel: 'BMW M4 GT3' }

  assert.deepEqual(lapRecord(top, races), {
    ms: 118037,
    session: 'qualification',
    raceId: 5,
    raceName: 'Round 5',
    raceDate: '2026-09-01T17:00:00Z',
    car: 'BMW M4 GT3',
    pilot: { userId: 70, name: 'Sam Seven', nickname: 'seven', number: 7, color: '#ff8800', avatar: '/api/uploads/avatars/users/70.png' }
  })
})

test('a lap record of a driver without a site account keeps the name from the results', () => {
  const top = { user_id: null, pilotName: 'Guest Driver', pilotNumber: 99, bestLapMs: 117000, bestLapSession: 'race', raceId: 5, raceName: 'Round 5', raceDate: '', carModel: '' }

  assert.deepEqual(lapRecord(top, []).pilot, { userId: null, name: 'Guest Driver', nickname: '', number: 99, color: '#1652d8', avatar: '' })
  assert.equal(lapRecord(null, []), null)
  assert.equal(lapRecord({ user_id: 70, bestLapMs: null }, []), null)
})

// Results entered by hand (Assetto Corsa) have no simulator file: the sector times come with the rows.
const manualRows = [
  { race_number: 7, user_id: 70, nickname: 'seven', best_sectors_ms: [21400, 37700, 31800], valid_laps: 40, qualification_best_sectors_ms: [21300, 37900, 31500], qualification_valid_laps: 5 },
  { race_number: 12, user_id: 120, nickname: 'twelve', best_sectors_ms: [21350, 37650, 31900], valid_laps: 38 },
  { race_number: 99, user_id: null, driver_name: 'Guest Driver', best_sectors_ms: [20000, 30000, 30000], valid_laps: 12 }
]

test('sector times kept in the result rows count like the ones from a simulator file', () => {
  const records = sectorRecords([race({ rows: manualRows, pilots })])

  assert.deepEqual(records.sectors.map((sector) => [sector.n, sector.ms, sector.pilot.userId, sector.session]), [
    [1, 21300, 70, 'qualification'],
    [2, 37650, 120, 'race'],
    [3, 31500, 70, 'qualification']
  ])
  assert.equal(records.idealMs, 21300 + 37650 + 31500)
  assert.equal(records.pilots, 2)
  assert.equal(records.sessions, 2)
  assert.equal(records.validLaps, 40 + 38 + 5)
})

test('a row with broken sector times is passed over', () => {
  const records = sectorRecords([
    race({
      rows: [
        { race_number: 7, user_id: 70, best_sectors_ms: 'fast', valid_laps: 'many' },
        { race_number: 12, user_id: 120, best_sectors_ms: [21350, 0, null], valid_laps: 3 },
        { race_number: 13, user_id: 130, best_sectors_ms: [21900, 38000] }
      ],
      pilots
    })
  ])

  assert.deepEqual(records.sectors.map((sector) => sector && [sector.ms, sector.pilot.userId]), [[21350, 120], [38000, 130], null])
  assert.equal(records.idealMs, null)
  assert.equal(records.validLaps, 3)
})

test('a simulator file, when the race has one, is read instead of the rows', () => {
  const records = sectorRecords([
    race({
      rows: [{ race_number: 7, user_id: 70, best_sectors_ms: [1000, 1000, 1000] }],
      pilots,
      raceSession: session([line(7, [34800, 49500, 33900])])
    })
  ])

  assert.deepEqual(records.sectors.map((sector) => sector.ms), [34800, 49500, 33900])
})

test('a pilot whose laps the stewards annulled holds no sector and adds no laps', () => {
  const annulledRows = [
    { ...manualRows[0], laps_annulled: true },
    manualRows[1]
  ]
  const fromRows = sectorRecords([race({ rows: annulledRows, pilots })])
  const fromFile = sectorRecords([
    race({
      rows: [{ ...rows[0], laps_annulled: true }, rows[1]],
      pilots,
      raceSession: session([line(7, [30000, 40000, 30000]), line(12, [34700, 49900, 33800])])
    })
  ])

  assert.deepEqual(fromRows.sectors.map((sector) => sector.pilot.userId), [120, 120, 120])
  assert.equal(fromRows.validLaps, 38)
  assert.equal(fromRows.pilots, 1)
  assert.deepEqual(fromFile.sectors.map((sector) => [sector.ms, sector.pilot.userId]), [[34700, 120], [49900, 120], [33800, 120]])
})
