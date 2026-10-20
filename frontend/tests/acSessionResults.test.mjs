import assert from 'node:assert/strict'
import test from 'node:test'
import { acRowTiming, matchAcDrivers, parseAcSession } from '../src/pages/race/acSessionResults.js'

function lap(car, number, sectors, { cuts = 0, time = sectors.reduce((sum, value) => sum + value, 0) } = {}) {
  return { car, lap: number, sectors, time, cuts, tyre: 'M' }
}

/** A Content Manager session file: three cars, qualifying and a race. */
function sessionFile() {
  return {
    track: 'ks_red_bull_ring-layout_gp_lfm',
    number_of_sessions: 2,
    players: [
      { name: 'Sam Seven | 7', car: 'formula_4', skin: 'a' },
      { name: 'Ivan Petrov', car: 'formula_4', skin: 'b' },
      { name: 'Empty Slot', car: 'formula_4', skin: 'c' },
      { name: 'Guest', car: 'formula_4', skin: 'd' }
    ],
    sessions: [
      {
        name: 'Qualify',
        type: 2,
        laps: [
          lap(0, 0, [60000, 37900, 31900]),
          lap(0, 1, [21300, 37500, 31500]),
          lap(0, 2, [21000, 37000, 31000], { cuts: 2 }),
          lap(1, 0, [21500, 37400, 31700]),
          lap(1, 1, [21450, 37800, 31600], { time: -1 })
        ]
      },
      {
        name: 'Race',
        type: 3,
        raceResult: [1, 0, 3, 2],
        laps: [
          lap(0, 0, [26000, 38000, 32000]),
          lap(0, 1, [21400, 37700, 31800]),
          lap(0, 2, [21350, 37900, 31850]),
          lap(1, 0, [25000, 38100, 32100]),
          lap(1, 1, [21380, 37650, 31900]),
          lap(3, 0, [27000, 39000, 33000])
        ]
      }
    ],
    __raceIni: { SERVER: { PASSWORD: 'secret', SERVER_IP: '10.0.0.1' }, REMOTE: { GUID: '7656' } }
  }
}

test('a session file is read into one entry per car that drove, slots without laps are left out', () => {
  const result = parseAcSession(sessionFile())

  assert.equal(result.track, 'ks_red_bull_ring-layout_gp_lfm')
  assert.deepEqual(result.drivers.map((driver) => driver.car), [0, 1, 3])
  assert.deepEqual(result.drivers.map((driver) => driver.name), ['Sam Seven', 'Ivan Petrov', 'Guest'])
  assert.deepEqual(result.drivers.map((driver) => driver.number), [7, null, null])
})

test('the race gives laps, the total time, the best lap and the best time in each sector', () => {
  const [sam, ivan, guest] = parseAcSession(sessionFile()).drivers

  assert.deepEqual(sam.race, { laps: 3, totalMs: 96000 + 90900 + 91100, bestLapMs: 90900, bestSectorsMs: [21350, 37700, 31800], validLaps: 3 })
  assert.deepEqual(ivan.race, { laps: 2, totalMs: 95200 + 90930, bestLapMs: 90930, bestSectorsMs: [21380, 37650, 31900], validLaps: 2 })
  assert.equal(guest.race.laps, 1)
  assert.equal(guest.qualification, null)
})

test('laps with a cut or without a proper time give neither a best lap nor sector times', () => {
  const [sam, ivan] = parseAcSession(sessionFile()).drivers

  assert.deepEqual(sam.qualification, { laps: 3, totalMs: null, bestLapMs: 90300, bestSectorsMs: [21300, 37500, 31500], validLaps: 2 })
  assert.deepEqual(ivan.qualification, { laps: 2, totalMs: null, bestLapMs: 90600, bestSectorsMs: [21500, 37400, 31700], validLaps: 1 })
})

test('the server settings stored in the file are not carried over', () => {
  const text = JSON.stringify(parseAcSession(sessionFile()))

  assert.ok(!text.includes('secret') && !text.includes('10.0.0.1') && !text.includes('7656'))
  assert.ok(!text.includes('__raceIni'))
})

test('a file of another kind is refused with a reason', () => {
  assert.throws(() => parseAcSession(null), /Content Manager/)
  assert.throws(() => parseAcSession({ sessionResult: { leaderBoardLines: [] } }), /Content Manager/)
  assert.throws(() => parseAcSession({ players: [], sessions: [] }), /no laps/i)
  assert.throws(() => parseAcSession({ players: [{ name: 'A' }], sessions: [{ type: 3, laps: [{ car: 0, sectors: 'x', time: 1 }] }] }), /no laps/i)
})

const pilots = [
  { user_id: 70, first_name: 'Sam', last_name: 'Seven', nickname: 'seven', login: 'sam7', pilot_number: 7 },
  { user_id: 80, first_name: 'Иван', last_name: 'Петров', nickname: 'vanya', login: 'ivan', pilot_number: 80 },
  { user_id: 90, first_name: 'Sam', last_name: 'Other', nickname: 'guestless', login: 'sam2', pilot_number: 90 },
  { user_id: 95, first_name: 'Aleksei', last_name: 'Sokolov', nickname: 'sokol', login: 'sokol', pilot_number: 95 }
]

function driver(car, name, number = null) {
  return { car, name, number }
}

test('a driver is tied to the pilot with the same name, whichever alphabet and order it is written in', () => {
  const matches = matchAcDrivers([driver(0, 'Sam Seven'), driver(1, 'Ivan Petrov'), driver(2, 'Petrov Ivan'), driver(3, 'SOKOL')], pilots)

  assert.deepEqual(matches.get(0), { userId: 70, how: 'name' })
  assert.deepEqual(matches.get(1), { userId: 80, how: 'name' })
  assert.equal(matches.has(2), false, 'a pilot is given to one car only')
  assert.deepEqual(matches.get(3), { userId: 95, how: 'name' })
})

test('a number after the name ties the driver when the name does not', () => {
  const matches = matchAcDrivers([driver(0, 'S. Seven', 7), driver(1, 'Nobody', 404)], pilots)

  assert.deepEqual(matches.get(0), { userId: 70, how: 'number' })
  assert.equal(matches.has(1), false)
})

test('a single word that only one pilot and one driver share is offered as a guess', () => {
  const matches = matchAcDrivers([driver(0, 'A. Sokolov'), driver(1, 'Sam')], pilots)

  assert.deepEqual(matches.get(0), { userId: 95, how: 'guess' })
  assert.equal(matches.has(1), false, 'two pilots are called Sam')
})

test('nobody is tied when there is nothing to go by', () => {
  assert.equal(matchAcDrivers([driver(0, ''), driver(1, 'Zed Zulu')], pilots).size, 0)
  assert.equal(matchAcDrivers([driver(0, 'Sam Seven')], []).size, 0)
})

test('a tied driver gives the form row its race figures and the sector times of both sessions', () => {
  const [sam, , guest] = parseAcSession(sessionFile()).drivers

  assert.deepEqual(acRowTiming(sam), {
    finish_ms: 278000,
    lap_count: 3,
    best_lap_ms: 90900,
    best_sectors_ms: [21350, 37700, 31800],
    valid_laps: 3,
    qualification_best_lap_ms: 90300,
    qualification_best_sectors_ms: [21300, 37500, 31500],
    qualification_valid_laps: 2
  })
  assert.deepEqual(acRowTiming(guest), {
    finish_ms: 99000,
    lap_count: 1,
    best_lap_ms: 99000,
    best_sectors_ms: [27000, 39000, 33000],
    valid_laps: 1,
    qualification_best_lap_ms: null,
    qualification_best_sectors_ms: null,
    qualification_valid_laps: null
  })
})

test('a driver who only qualified, or set no valid lap, brings no race result and no sector times', () => {
  const file = sessionFile()
  const onlyQualified = { ...file, sessions: [file.sessions[0]] }
  const noValidLap = { ...file, sessions: [{ name: 'Race', type: 3, laps: [lap(0, 0, [21000, 37000, 31000], { cuts: 1 })] }] }

  assert.deepEqual(acRowTiming(parseAcSession(onlyQualified).drivers[0]), {
    finish_ms: null,
    lap_count: 0,
    best_lap_ms: null,
    best_sectors_ms: null,
    valid_laps: null,
    qualification_best_lap_ms: 90300,
    qualification_best_sectors_ms: [21300, 37500, 31500],
    qualification_valid_laps: 2
  })
  assert.deepEqual(acRowTiming(parseAcSession(noValidLap).drivers[0]), {
    finish_ms: 89000,
    lap_count: 1,
    best_lap_ms: null,
    best_sectors_ms: null,
    valid_laps: null,
    qualification_best_lap_ms: null,
    qualification_best_sectors_ms: null,
    qualification_valid_laps: null
  })
})
