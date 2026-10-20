import assert from 'node:assert/strict'
import test from 'node:test'
import { isExtraColumn, resultColumns } from '../src/pages/race/resultColumns.js'

test('the race table at a glance: place, pilot, best lap, the time that counts, rating change and gap', () => {
  assert.deepEqual(resultColumns('race', { detailed: false, hasQuali: true }), ['pos', 'pilot', 'bestLap', 'adjusted', 'delta', 'gap'])
})

test('the whole race table adds the car, laps, qualifying lap, the raw time and both penalties', () => {
  assert.deepEqual(resultColumns('race', { detailed: true, hasQuali: true }), [
    'pos', 'pilot', 'car', 'laps', 'bestLap', 'qualiLap', 'finish', 'timePenalty', 'srPenalty', 'adjusted', 'delta', 'gap'
  ])
})

test('a race without qualifying laps has no qualifying column, however much is shown', () => {
  assert.equal(resultColumns('race', { detailed: true, hasQuali: false }).includes('qualiLap'), false)
  assert.equal(resultColumns('race', { detailed: false, hasQuali: false }).includes('qualiLap'), false)
})

test('qualifying at a glance is place, pilot, lap and gap; the car comes with the whole table', () => {
  assert.deepEqual(resultColumns('qualification', { detailed: false }), ['pos', 'pilot', 'bestLap', 'gap'])
  assert.deepEqual(resultColumns('qualification', { detailed: true }), ['pos', 'pilot', 'car', 'bestLap', 'gap'])
})

test('a column of the whole table only is told from one that is always there', () => {
  assert.equal(isExtraColumn('race', 'laps'), true)
  assert.equal(isExtraColumn('race', 'finish'), true)
  assert.equal(isExtraColumn('race', 'adjusted'), false)
  assert.equal(isExtraColumn('race', 'pilot'), false)
  assert.equal(isExtraColumn('qualification', 'car'), true)
  assert.equal(isExtraColumn('qualification', 'gap'), false)
})
