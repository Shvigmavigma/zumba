import assert from 'node:assert/strict'
import test from 'node:test'
import { formatDuration, isAccMaxTime, timeLabel, validTimeMs } from '../src/pages/race/raceTime.js'

test('a time reads like a timing screen', () => {
  assert.equal(formatDuration(90609), '1:30.609')
  assert.equal(formatDuration('4557618'), '75:57.618')
  assert.equal(formatDuration(59999.6), '1:00.000')
  assert.equal(formatDuration(0), '0:00.000')
})

test('no time is not a time of zero', () => {
  for (const value of [null, undefined, '', 'fast', NaN, {}]) {
    assert.equal(formatDuration(value), '-', String(value))
  }
})

test('a time that was really set is a positive number of milliseconds', () => {
  assert.equal(validTimeMs(90609), 90609)
  assert.equal(validTimeMs('91146'), 91146)
  for (const value of [null, undefined, '', 0, '0', -5, NaN, 'fast', 2147483647, 4294967295]) {
    assert.equal(validTimeMs(value), null, String(value))
  }
})

test('the results show a dash where a pilot set no time: no qualifying lap, a race not started', () => {
  assert.equal(timeLabel(null), '-')
  assert.equal(timeLabel(0), '-')
  assert.equal(timeLabel(undefined), '-')
  assert.equal(timeLabel(2147483647), '-')
  assert.equal(timeLabel(90609), '1:30.609')
})

test('the simulator\'s own "no time" is told apart from a real one', () => {
  assert.equal(isAccMaxTime(2147483647), true)
  assert.equal(isAccMaxTime(4294967295), true)
  assert.equal(isAccMaxTime(90609), false)
  assert.equal(isAccMaxTime(null), false)
})
