import test from 'node:test'
import assert from 'node:assert/strict'
import { INTRO_END_MS, INTRO_TIMING, accentParts, pixelOrder, wallRows, wallScale } from '../src/pages/race/winnerIntro.js'
import { pilotFirstName } from '../src/pilotDisplay.js'

test('the intro runs WINNER, then the name, then clears before the header comes in', () => {
  assert.ok(INTRO_TIMING.nameAt < INTRO_TIMING.clearAt)
  assert.ok(INTRO_TIMING.clearAt <= INTRO_TIMING.revealAt)
  assert.ok(INTRO_TIMING.revealAt < INTRO_END_MS)
  assert.ok(INTRO_TIMING.clearAt >= 2000 && INTRO_TIMING.clearAt <= 2500, 'the words stay for 2–2.5 s')
})

test('the screen goes black before the name comes up', () => {
  assert.ok(INTRO_TIMING.pixelsAt + INTRO_TIMING.pixelsMs <= INTRO_TIMING.nameAt)
})

test('the black spreads from the middle: middle blocks first, corners last', () => {
  const cols = 41
  const rows = 21
  const order = pixelOrder(cols, rows)
  assert.equal(order.length, cols * rows)
  const at = (col, row) => order[row * cols + col]
  const middle = at(20, 10)
  for (const corner of [at(0, 0), at(40, 0), at(0, 20), at(40, 20)]) {
    assert.ok(corner > 0.75, `corner ${corner}`)
    assert.ok(middle < corner)
  }
  assert.ok(middle < 0.25)
  assert.ok(order.every((value) => value >= 0 && value < 1))
})

test('the edge is ragged, and the same on every visit', () => {
  const order = pixelOrder(30, 16)
  assert.deepEqual(order, pixelOrder(30, 16))
  // Blocks 5 and 24 of row 8 are as far from the middle (col 14.5) but need not turn together.
  assert.notEqual(order[8 * 30 + 5], order[8 * 30 + 24])
  assert.equal(pixelOrder(0, 0).length, 0)
  assert.equal(pixelOrder(1, 1).length, 1)
})

test('the wall has one accent, in the middle of the middle row', () => {
  const rows = wallRows({ rows: 9, perRow: 5 })
  assert.equal(rows.length, 9)
  const accents = rows.flatMap((row) => row.words.filter((word) => word.look === 'accent').map((word) => [row.id, word.id]))
  assert.deepEqual(accents, [[4, 2]])
  assert.equal(rows[4].far, 0)
  assert.equal(rows[0].far, 4)
})

test('neighbouring rows slide in opposite directions and the middle row barely moves', () => {
  const rows = wallRows()
  for (const row of rows.filter((item) => item.far > 0)) {
    assert.equal(Math.abs(row.dir), 1)
  }
  for (let index = 0; index < rows.length - 1; index += 1) {
    assert.notEqual(rows[index].dir, rows[index + 1].dir, `rows ${index} and ${index + 1}`)
  }
  assert.ok(Math.abs(rows[4].dir) < 1)
})

test('the wall is the same on every visit', () => {
  assert.deepEqual(wallRows(), wallRows())
})

test('long names are drawn smaller so the accent fits, WINNER at full size', () => {
  assert.equal(wallScale('Winner'), 1)
  assert.equal(wallScale('Max'), 1)
  assert.equal(wallScale('Vladislav'), 6 / 9)
  assert.equal(wallScale('Aleksandr-Konstantin'), 0.5)
  assert.equal(wallScale(''), 1)
})

test('the accent splits off whole letters', () => {
  assert.deepEqual(accentParts('Max'), { first: 'M', rest: 'ax' })
  assert.deepEqual(accentParts(' Виктор '), { first: 'В', rest: 'иктор' })
  assert.deepEqual(accentParts('😀go'), { first: '😀', rest: 'go' })
  assert.deepEqual(accentParts(''), { first: '', rest: '' })
})

test('the first name comes from the first record that knows it, else the name they go by', () => {
  assert.equal(pilotFirstName('Victor Rezov', { first_name: 'Victor', last_name: 'Rezov' }), 'Victor')
  assert.equal(pilotFirstName('Victor Rezov', null, { first_name: ' Victor ' }), 'Victor')
  assert.equal(pilotFirstName('Senna_88', { first_name: '' }), 'Senna_88')
  assert.equal(pilotFirstName(undefined), '')
})
