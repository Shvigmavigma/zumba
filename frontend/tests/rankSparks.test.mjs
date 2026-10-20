import assert from 'node:assert/strict'
import test from 'node:test'
import { HOP_COUNT, hopVars, seededRandom } from '../src/ui/rank/sparks.js'

const positions = (vars) => Array.from({ length: HOP_COUNT }, (_, hop) => Number(vars[`--x${hop}`]))

test('the seeded generator repeats its sequence and stays inside [0, 1)', () => {
  const first = seededRandom(42)
  const second = seededRandom(42)
  const values = Array.from({ length: 200 }, () => first())
  assert.deepEqual(values, Array.from({ length: 200 }, () => second()))
  values.forEach((value) => assert.ok(value >= 0 && value < 1))
  assert.notDeepEqual(values.slice(0, 5), Array.from({ length: 5 }, seededRandom(43)))
})

test('an emitter gets a place and a strength for every hop, inside the range', () => {
  const vars = hopVars(seededRandom(7), 10, 70)
  assert.equal(Object.keys(vars).length, HOP_COUNT * 2)
  positions(vars).forEach((x) => assert.ok(x >= 10 && x <= 70))
  for (let hop = 0; hop < HOP_COUNT; hop += 1) {
    const strength = Number(vars[`--k${hop}`])
    assert.ok(strength >= 0.65 && strength <= 1.15)
  }
})

test('an emitter never lands in the same or a neighbouring zone twice in a row', () => {
  for (let seed = 1; seed <= 60; seed += 1) {
    const zones = positions(hopVars(seededRandom(seed), 0, 100)).map((x) => Math.min(HOP_COUNT - 1, Math.floor(x / (100 / HOP_COUNT))))
    assert.equal(new Set(zones).size, HOP_COUNT)
    zones.forEach((zone, hop) => {
      // The last hop leads back to the first; on a closed rim the first and last zones touch too.
      const next = zones[(hop + 1) % HOP_COUNT]
      const apart = Math.abs(zone - next)
      assert.ok(Math.min(apart, HOP_COUNT - apart) >= 2, `seed ${seed}: zones ${zone} -> ${next}`)
    })
  }
})
