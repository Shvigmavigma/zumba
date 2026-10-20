import assert from 'node:assert/strict'
import test from 'node:test'
import { DEFAULT_LICENSE_TIERS, licenseProgress, ratedGames } from '../src/pilotDisplay.js'

test('progress is measured from the tier floor to the next tier', () => {
  const result = licenseProgress(2000, DEFAULT_LICENSE_TIERS)
  assert.equal(result.tier.name, 'Bronze')
  assert.equal(result.next.name, 'Silver')
  assert.equal(result.progress, 0.5)
  assert.equal(result.toNext, 500)
})

test('the top tier is complete and has no next tier', () => {
  const result = licenseProgress(9000, DEFAULT_LICENSE_TIERS)
  assert.equal(result.tier.name, 'Champ')
  assert.equal(result.next, null)
  assert.equal(result.progress, 1)
})

test('invalid ratings fall back to the first tier without progress', () => {
  const result = licenseProgress('abc', DEFAULT_LICENSE_TIERS)
  assert.equal(result.tier.name, 'Rookie')
  assert.equal(result.progress, 0)
  assert.equal(result.toNext, 0)
})

test('profiles show ticked games and any game the pilot has raced in', () => {
  const pilot = { games: ['ACC'], game_ratings: { iRacing: { race_count: 3 }, LMU: { race_count: 0 } } }
  assert.deepEqual(ratedGames(pilot), ['ACC', 'iRacing'])
  assert.deepEqual(ratedGames({ games: [] }), ['ACC'])
})
