import assert from 'node:assert/strict'
import test from 'node:test'
import { raceSessions, sessionMinutes } from '../src/pages/race/sessionSchedule.js'

test('a session lasts from its start to its end, in minutes', () => {
  assert.equal(sessionMinutes('19:30:00', '19:35:00'), 5)
  assert.equal(sessionMinutes('20:00', '21:10'), 70)
  assert.equal(sessionMinutes('19:35:00', '20:00:30'), 25)
})

test('a session that runs past midnight is not negative', () => {
  assert.equal(sessionMinutes('23:50:00', '00:20:00'), 30)
})

test('a time that cannot be read gives no duration', () => {
  assert.equal(sessionMinutes('', '20:00'), null)
  assert.equal(sessionMinutes('19:30', null), null)
  assert.equal(sessionMinutes('soon', '20:00'), null)
  assert.equal(sessionMinutes('25:00', '26:00'), null)
})

test('only the sessions staff gave both times to are listed, in running order', () => {
  const race = {
    briefing_start_time: null,
    briefing_end_time: null,
    practice_start_time: '19:30:00',
    practice_end_time: '19:35:00',
    qualification_start_time: '19:35:00',
    qualification_end_time: null,
    race_session_start_time: '20:00:00',
    race_session_end_time: '21:10:00'
  }
  assert.deepEqual(raceSessions(race), [
    { key: 'practice', start: '19:30:00', end: '19:35:00', minutes: 5, main: false },
    { key: 'race_session', start: '20:00:00', end: '21:10:00', minutes: 70, main: true }
  ])
  assert.deepEqual(raceSessions({}), [])
  assert.deepEqual(raceSessions(null), [])
})
