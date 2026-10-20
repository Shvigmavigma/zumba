import assert from 'node:assert/strict'
import test from 'node:test'
import { randomPlate, scatter, scrambleFrame } from '../src/ui/fx/floatingNumbers.js'

function sequence(...values) {
  let index = 0
  return () => values[index++ % values.length]
}

test('numbers are spread over distinct grid cells inside the box', () => {
  const points = scatter(12, { cols: 4, rows: 5 })
  assert.equal(points.length, 12)
  const cells = new Set(points.map(({ x, y }) => `${Math.floor(x / 25)}:${Math.floor(y / 20)}`))
  assert.equal(cells.size, 12)
  points.forEach(({ x, y }) => {
    assert.ok(x > 0 && x < 100)
    assert.ok(y > 0 && y < 100)
  })
})

test('never asks for more numbers than there are cells', () => {
  assert.equal(scatter(50, { cols: 2, rows: 2 }).length, 4)
})

test('plates always have three digits', () => {
  assert.equal(randomPlate(() => 0), '000')
  assert.equal(randomPlate(() => 0.077), '077')
  assert.equal(randomPlate(() => 0.9999), '999')
})

test('a flip locks digits from left to right and ends on the target', () => {
  const nine = sequence(0.95)
  assert.equal(scrambleFrame('#144', 0, nine), '#999')
  assert.equal(scrambleFrame('#144', 0.34, nine), '#199')
  assert.equal(scrambleFrame('#144', 1, nine), '#144')
})
