import test from 'node:test'
import assert from 'node:assert/strict'
import { seasonProgress, seasonRailFill } from '../src/pages/championships/helpers.js'

const stage = (id, round, status, start) => ({ id, championship_round: round, status, datetime_start: start })
const day = (date) => `2026-10-${String(date).padStart(2, '0')}T19:30:00Z`
const at = (date, hours = 19.5) => new Date(`2026-10-${String(date).padStart(2, '0')}T00:00:00Z`).getTime() + hours * 3600000

test('the stretch out of the last stage raced fills with the time passed on the way to the next one', () => {
  const season = seasonProgress([stage(1, 1, 'finished', day(11)), stage(2, 2, 'registration_open', day(17))])
  assert.deepEqual(seasonRailFill(season.stages, at(14)), [0.5])
})

test('a stretch is full once the stage it leads to has been raced or is running', () => {
  const season = seasonProgress([
    stage(1, 1, 'finished', day(1)),
    stage(2, 2, 'finished', day(8)),
    stage(3, 3, 'ongoing', day(15)),
    stage(4, 4, 'registration_open', day(22))
  ])
  assert.deepEqual(seasonRailFill(season.stages, at(15)), [1, 1, 0])
})

test('before the first stage and beyond the next one the line stays empty', () => {
  const season = seasonProgress([stage(1, 1, 'registration_open', day(11)), stage(2, 2, 'draft', day(17)), stage(3, 3, 'draft', day(24))])
  assert.deepEqual(seasonRailFill(season.stages, at(10)), [0, 0])
})

test('the fill never runs past the next stage, even when its start is overdue', () => {
  const season = seasonProgress([stage(1, 1, 'finished', day(11)), stage(2, 2, 'registration_open', day(17))])
  assert.deepEqual(seasonRailFill(season.stages, at(20)), [1])
})

test('dates that make no stretch give an empty one, and a single stage has no line at all', () => {
  const broken = seasonProgress([stage(1, 1, 'finished', day(17)), stage(2, 2, 'registration_open', 'not a date')])
  assert.deepEqual(seasonRailFill(broken.stages, at(18)), [0])
  assert.deepEqual(seasonRailFill(seasonProgress([stage(1, 1, 'finished', day(11))]).stages, at(12)), [])
  assert.deepEqual(seasonRailFill([], at(12)), [])
})
