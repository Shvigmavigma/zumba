import test from 'node:test'
import assert from 'node:assert/strict'
import { mapIsPortrait, mapPoint } from '../src/pages/race/liveMapGeometry.js'

test('portrait maps and driver positions rotate together', () => {
  const geometry = { WIDTH: 100, HEIGHT: 200, X_OFFSET: 10, Z_OFFSET: 20, SCALE_FACTOR: 2, PADDING: 5 }
  assert.equal(mapIsPortrait(geometry), true)
  assert.deepEqual(mapPoint({ x: 30, z: 70 }, geometry), { left: 75, top: 25 })
})

test('landscape maps preserve their original orientation and positions', () => {
  const geometry = { WIDTH: 200, HEIGHT: 100, X_OFFSET: 10, Z_OFFSET: 20, SCALE_FACTOR: 2, PADDING: 5 }
  assert.equal(mapIsPortrait(geometry), false)
  assert.deepEqual(mapPoint({ x: 30, z: 70 }, geometry), { left: 12.5, top: 50 })
})

test('an additional half-turn moves the driver with the map', () => {
  const geometry = { WIDTH: 100, HEIGHT: 200, X_OFFSET: 10, Z_OFFSET: 20, SCALE_FACTOR: 2, PADDING: 5 }
  assert.deepEqual(mapPoint({ x: 30, z: 70 }, geometry, true), { left: 25, top: 75 })
})
