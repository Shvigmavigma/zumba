import assert from 'node:assert/strict'
import { register } from 'node:module'
import test from 'node:test'

// hallRanking.js imports '../../pilotDisplay' without an extension, as Vite allows.
register('./helpers/resolveJs.mjs', import.meta.url)
const { hallRating, hallStat, rankHallItems } = await import('../src/pages/hall-of-fame/hallRanking.js')

const pilot = (id, rating, points = 0, extra = {}) => ({
  id,
  nickname: `p${id}`,
  rating,
  game_ratings: { ACC: { rating } },
  points,
  gold: 0,
  silver: 0,
  bronze: 0,
  ...extra
})

test('by rating: every pilot is ranked, best RER first', () => {
  const ranked = rankHallItems([pilot(1, 1500, 9), pilot(2, 3100), pilot(3, 2200, 3)], { mode: 'rating', game: 'all' })
  // Pilot 2 has no podium yet and still leads on rating.
  assert.deepEqual(ranked.map((item) => item.id), [2, 3, 1])
})

test('by medals: only podium finishers, points first', () => {
  const ranked = rankHallItems([pilot(1, 1500, 9), pilot(2, 3100), pilot(3, 2200, 3)], { mode: 'medals', game: 'all' })
  assert.deepEqual(ranked.map((item) => item.id), [1, 3])
})

test('equal ratings fall back to medals, then to the name', () => {
  const ranked = rankHallItems([
    pilot(1, 2000, 0, { nickname: 'bravo' }),
    pilot(2, 2000, 4, { gold: 1 }),
    pilot(3, 2000, 0, { nickname: 'Alpha' })
  ], { mode: 'rating', game: 'all' })
  assert.deepEqual(ranked.map((item) => item.id), [2, 3, 1])
})

test('equal points are split by gold, silver and bronze', () => {
  const ranked = rankHallItems([
    pilot(1, 1000, 6, { silver: 2 }),
    pilot(2, 1000, 6, { gold: 1, bronze: 1 }),
    pilot(3, 1000, 6, { gold: 1, silver: 1 })
  ], { mode: 'medals', game: 'all' })
  assert.deepEqual(ranked.map((item) => item.id), [3, 2, 1])
})

test('a simulator has its own statistics and rating', () => {
  const both = { ...pilot(1, 1200, 9), game_ratings: { ACC: { rating: 1200 }, AC: { rating: 4000 } }, stats_by_game: { AC: { points: 2 } } }
  const accOnly = { ...pilot(2, 3000, 5), stats_by_game: { ACC: { points: 5 } } }
  assert.equal(hallStat(both, 'points', 'AC'), 2)
  assert.equal(hallStat(both, 'points', 'all'), 9)
  assert.equal(hallStat(accOnly, 'points', 'AC'), 0)
  assert.equal(hallRating(both, 'AC'), 4000)
  assert.deepEqual(rankHallItems([both, accOnly], { mode: 'medals', game: 'AC' }).map((item) => item.id), [1])
  assert.deepEqual(rankHallItems([both, accOnly], { mode: 'rating', game: 'ACC' }).map((item) => item.id), [2, 1])
})

test('a team is rated by the selected simulator, overall by its best one', () => {
  const team = { id: 7, name: 'Team', member_count: 3, average_rating: 1800, ratings_by_game: { ACC: 2100, AC: 2600 } }
  assert.equal(hallRating(team, 'ACC'), 2100)
  assert.equal(hallRating(team, 'all'), 2600)
  // No rating in that simulator yet: fall back to the team average.
  assert.equal(hallRating(team, 'LMU'), 1800)
  assert.equal(hallRating({ id: 8, name: 'New', member_count: 1, average_rating: 1000 }, 'all'), 1000)
})

test('a pilot outside the rating is not ranked by RER, but keeps their medals', () => {
  const items = [pilot(1, 1500, 3), pilot(2, 1000, 9, { exclude_from_rer: true })]
  assert.deepEqual(rankHallItems(items, { mode: 'rating', game: 'all' }).map((item) => item.id), [1])
  assert.deepEqual(rankHallItems(items, { mode: 'medals', game: 'all' }).map((item) => item.id), [2, 1])
})

test('ranking never reorders the list it was given', () => {
  const items = [pilot(1, 1000), pilot(2, 3000)]
  rankHallItems(items, { mode: 'rating', game: 'all' })
  assert.deepEqual(items.map((item) => item.id), [1, 2])
})
