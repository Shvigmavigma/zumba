import assert from 'node:assert/strict'
import test from 'node:test'
import { accLineHasActivity, classifiedRows, isRowOutsideRating, qualificationOrder, lapsAnnulled, bestLapOf } from '../src/pages/race/raceClassification.js'

const row = (userId, position, gapMs, extra = {}) => ({ user_id: userId, position, gap_ms: gapMs, ...extra })

test('a pilot outside the rating is left out and the rest move up', () => {
  const rows = [row(1, 1, 0), row(2, 2, 1500, { exclude_from_rer: true }), row(3, 3, 4000)]
  const shown = classifiedRows(rows)
  assert.deepEqual(shown.map((item) => [item.user_id, item.position]), [[1, 1], [3, 2]])
  // The leader stayed, so the gaps still count from them.
  assert.deepEqual(shown.map((item) => item.gap_ms), [0, 4000])
})

test('the flag of the registered pilot counts when the row has none', () => {
  const participants = [{ user_id: 2, exclude_from_rer: true }, { user_id: 3, exclude_from_rer: false }]
  assert.equal(isRowOutsideRating(row(2, 2, 0), participants), true)
  assert.equal(isRowOutsideRating(row(3, 3, 0), participants), false)
  assert.deepEqual(classifiedRows([row(2, 1, 0), row(3, 2, 900)], participants).map((item) => item.user_id), [3])
})

test('gaps are counted from the new leader when the winner is left out', () => {
  const rows = [row(1, 1, 0, { exclude_from_rer: true }), row(2, 2, 1500), row(3, 3, 4000), row(4, 4, null)]
  const shown = classifiedRows(rows)
  assert.deepEqual(shown.map((item) => [item.position, item.gap_ms]), [[1, 0], [2, 2500], [3, null]])
})

test('a guest car without an account is never treated as excluded', () => {
  const rows = [{ user_id: null, position: 1, gap_ms: 0, driver_name: 'Guest' }, row(2, 2, 700)]
  assert.equal(isRowOutsideRating(rows[0], [{ user_id: 2 }]), false)
  assert.equal(classifiedRows(rows, [{ user_id: 2 }]).length, 2)
})

test('the classification is a new list: stored rows stay as they were', () => {
  const rows = [row(1, 1, 0, { exclude_from_rer: true }), row(2, 2, 1500)]
  classifiedRows(rows)
  assert.deepEqual(rows.map((item) => [item.position, item.gap_ms]), [[1, 0], [2, 1500]])
  assert.deepEqual(classifiedRows(null), [])
})

test('an ACC leaderboard line counts only when the car drove a lap', () => {
  assert.equal(accLineHasActivity({ timing: { lapCount: 3 } }), true)
  assert.equal(accLineHasActivity({ timing: { lapCount: 0 } }), false)
  assert.equal(accLineHasActivity({ timing: {} }), false)
  assert.equal(accLineHasActivity(null), false)
})

test('a hand-entered qualifying is listed in the stored grid order', () => {
  const rows = [
    { user_id: 1, qualification_position: 2, qualification_best_lap_ms: 90700 },
    { user_id: 2, qualification_position: 1, qualification_best_lap_ms: 90600 },
    { user_id: 3, qualification_position: 3, qualification_best_lap_ms: 90900 }
  ]

  assert.deepEqual(qualificationOrder(rows).map((row) => row.user_id), [2, 1, 3])
})

test('where the results keep lap times only, the fastest lap comes first', () => {
  const rows = [
    { user_id: 1, qualification_position: null, qualification_best_lap_ms: 91035 },
    { user_id: 2, qualification_position: null, qualification_best_lap_ms: 90609 },
    { user_id: 3, qualification_best_lap_ms: 90785 }
  ]

  assert.deepEqual(qualificationOrder(rows).map((row) => row.user_id), [2, 3, 1])
})

test('a pilot without a qualifying lap is not in the qualifying', () => {
  const rows = [
    { user_id: 1, qualification_best_lap_ms: null },
    { user_id: 2, qualification_best_lap_ms: 90609 },
    { user_id: 3 },
    { user_id: 4, qualification_best_lap_ms: 0 }
  ]

  assert.deepEqual(qualificationOrder(rows).map((row) => row.user_id), [2])
  assert.deepEqual(qualificationOrder([]), [])
})

test('laps annulled by the stewards are told by a flag on the result row', () => {
  assert.equal(lapsAnnulled({ user_id: 1, laps_annulled: true }), true)
  assert.equal(lapsAnnulled({ user_id: 1, laps_annulled: false }), false)
  assert.equal(lapsAnnulled({ user_id: 1, laps_annulled: 'yes' }), false)
  assert.equal(lapsAnnulled({ user_id: 1 }), false)
  assert.equal(lapsAnnulled(null), false)
})

test('the best lap of a race weekend is the fastest of race and qualifying laps, with the session it came from', () => {
  const rows = [
    { user_id: 1, best_lap_ms: 91146, qualification_best_lap_ms: 90747 },
    { user_id: 2, best_lap_ms: 91184, qualification_best_lap_ms: 90609 },
    { user_id: 3, best_lap_ms: 91000, laps_annulled: true, qualification_best_lap_ms: 90100 }
  ]

  const best = bestLapOf(rows)

  assert.equal(best.row.user_id, 2)
  assert.equal(best.ms, 90609)
  assert.equal(best.session, 'qualification')
})

test('without qualifying laps the best lap is the race one; with no lap at all there is none', () => {
  assert.deepEqual(bestLapOf([{ user_id: 1, best_lap_ms: 91146, qualification_best_lap_ms: null }, { user_id: 2, best_lap_ms: 0 }]), { row: { user_id: 1, best_lap_ms: 91146, qualification_best_lap_ms: null }, ms: 91146, session: 'race' })
  assert.equal(bestLapOf([{ user_id: 1, best_lap_ms: 0 }, { user_id: 2, best_lap_ms: 2147483647 }]), null)
  assert.equal(bestLapOf([]), null)
})
