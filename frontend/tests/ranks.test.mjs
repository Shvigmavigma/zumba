import assert from 'node:assert/strict'
import { register } from 'node:module'
import test from 'node:test'

// ranks.js imports './pilotDisplay' without an extension, as Vite allows.
register('./helpers/resolveJs.mjs', import.meta.url)
const { SEASON_FINISH, finishOf, finishOfRating, isRerExcluded, overallRank, rankFor, rankLadder } = await import('../src/ranks.js')

test('ratings map onto the seven ranks of the default tiers', () => {
  assert.equal(rankFor(1000).key, 'rookie')
  assert.equal(rankFor(1500).key, 'bronze')
  assert.equal(rankFor(3100).key, 'silver')
  assert.equal(rankFor(4600).key, 'gold')
  assert.equal(rankFor(6200).key, 'platinum')
  assert.equal(rankFor(7600).key, 'diamond')
  assert.equal(rankFor(9300).key, 'champ')
})

test('out-of-range and missing ratings fall back to the ends', () => {
  assert.equal(rankFor(-20).key, 'rookie')
  assert.equal(rankFor(null).key, 'rookie')
  assert.equal(rankFor(12000).key, 'champ')
})

test('progress and distance point at the next tier', () => {
  const bronze = rankFor(2000)
  assert.equal(bronze.next.name, 'Silver')
  assert.equal(bronze.toNext, 500)
  assert.equal(bronze.progress, 0.5)
  const champ = rankFor(9000)
  assert.equal(champ.next, null)
  assert.equal(champ.progress, 1)
})

test('renamed or fewer tiers keep their look by position', () => {
  const tiers = [
    { name: 'Новичок', min_rating: 0, max_rating: 999 },
    { name: 'Профи', min_rating: 1000, max_rating: 1999 },
    { name: 'Легенда', min_rating: 2000, max_rating: 9999 }
  ]
  assert.deepEqual([0, 1500, 5000].map((value) => rankFor(value, tiers).key), ['rookie', 'gold', 'champ'])
})

test('the overall rank uses the best simulator', () => {
  const pilot = { rating: 1000, game_ratings: { ACC: { rating: 1400 }, AC: { rating: 4100 } } }
  assert.equal(overallRank(pilot).key, 'gold')
  assert.equal(rankLadder().length, 7)
})

test('a pilot outside the rating has no rank to show', () => {
  const excluded = { rating: 9300, game_ratings: { ACC: { rating: 9300 } }, exclude_from_rer: true }
  assert.equal(isRerExcluded(excluded), true)
  assert.equal(overallRank(excluded).key, 'rookie')
  assert.equal(finishOf(excluded), 'rookie')
  // Only an explicit flag counts: a missing one must not hide a real rank.
  assert.equal(isRerExcluded({ rating: 9300 }), false)
  assert.equal(isRerExcluded(null), false)
  assert.equal(overallRank({ rating: 9300, game_ratings: { ACC: { rating: 9300 } }, exclude_from_rer: false }).key, 'champ')
})

test('the season champion gets a finish of their own, whatever their rating', () => {
  const title = { id: 10, name: 'Победитель BMRL CHAMPIONSHIP 1' }
  const champion = { rating: 1000, game_ratings: { ACC: { rating: 2930 } }, pilot_roles: [title] }
  assert.equal(finishOf(champion), SEASON_FINISH)
  // The title is not a rank: the RER tier stays what the rating says.
  assert.equal(overallRank(champion).key, 'silver')
  assert.equal(finishOf({ ...champion, pilot_roles: [] }), 'silver')
  assert.equal(finishOf(null), 'rookie')
})

test('a result row is finished by its roles first, then by its rating', () => {
  assert.equal(finishOfRating(4600, [{ id: 10, name: 'Победитель BMRL CHAMPIONSHIP 1' }]), SEASON_FINISH)
  assert.equal(finishOfRating(4600, [{ id: 2, name: 'Победитель Nascar' }]), 'gold')
  assert.equal(finishOfRating(4600, undefined), 'gold')
})
