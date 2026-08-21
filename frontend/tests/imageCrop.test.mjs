import assert from 'node:assert/strict'
import test from 'node:test'
import { calculateCropGeometry, clampCropOffset, cropSourceRect } from '../src/imageCrop.js'

test('crop geometry covers the logo frame and clamps dragging', () => {
  const geometry = calculateCropGeometry(1600, 400, 780, 200, 1, 0, 0)
  assert.equal(geometry.scale, 0.5)
  assert.equal(geometry.maxOffsetX, 10)
  assert.equal(clampCropOffset(50, geometry.maxOffsetX), 10)
  assert.deepEqual(cropSourceRect(geometry, 1600, 400), { x: 20, y: 0, width: 1560, height: 400 })
})
