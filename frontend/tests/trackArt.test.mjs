import assert from 'node:assert/strict'
import test from 'node:test'
import { classifyTone, measureTone } from '../src/ui/motion/trackArt.js'

function pixels(...rgba) {
  return new Uint8ClampedArray(rgba.flat())
}

test('a white sheet with dark track lines is a diagram', () => {
  const sheet = pixels(...Array(9).fill([250, 250, 250, 255]), [20, 20, 20, 255])
  assert.equal(classifyTone(measureTone(sheet)), 'diagram')
})

test('dark or colourful artwork stays a photo', () => {
  assert.equal(classifyTone(measureTone(pixels([30, 40, 60, 255], [20, 25, 35, 255]))), 'photo')
  assert.equal(classifyTone(measureTone(pixels([255, 210, 40, 255], [90, 200, 255, 255]))), 'photo')
})

test('transparent pixels are ignored and an empty image is a photo', () => {
  const tone = measureTone(pixels([0, 0, 0, 0], [255, 255, 255, 255]))
  assert.equal(tone.luma, 1)
  assert.equal(tone.saturation, 0)
  assert.equal(classifyTone(measureTone(pixels([0, 0, 0, 0]))), 'photo')
})
