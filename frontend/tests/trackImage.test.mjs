import assert from 'node:assert/strict'
import test from 'node:test'
import { DEFAULT_TRACK_FRAME, trackAsset, trackImageFrame, trackImageStyle } from '../src/pages/race/trackImage.js'

const config = {
  track_ids: { Spa: 'spa', Monza: 7 },
  track_images: { Spa: '/img/spa.webp', monza: '/img/monza.webp' },
  track_image_crops: { Spa: { zoom: 1.6, x: 30, y: 70 } }
}

test('a track asset is found by name, whatever the letter case', () => {
  assert.equal(trackAsset(config, 'track_images', 'Spa'), '/img/spa.webp')
  assert.equal(trackAsset(config, 'track_images', ' spa '), '/img/spa.webp')
  assert.equal(trackAsset(config, 'track_images', 'Monza'), '/img/monza.webp')
  assert.equal(trackAsset(config, 'track_images', 'Imola'), null)
  assert.equal(trackAsset(config, 'track_images', ''), null)
  assert.equal(trackAsset(null, 'track_images', 'Spa'), null)
})

test('the track id wins over a renamed track, numbers and strings alike', () => {
  assert.equal(trackAsset(config, 'track_images', 'Spa-Francorchamps', 'spa'), '/img/spa.webp')
  assert.equal(trackAsset(config, 'track_images', 'Autodromo', '7'), '/img/monza.webp')
  // An unknown id falls back to the name.
  assert.equal(trackAsset(config, 'track_images', 'Spa', 'nope'), '/img/spa.webp')
})

test('a track without a saved frame shows the whole image, centred', () => {
  assert.deepEqual(trackImageFrame(config, 'Monza'), DEFAULT_TRACK_FRAME)
  assert.deepEqual(trackImageFrame(config, 'Spa'), { zoom: 1.6, x: 30, y: 70 })
})

test('a broken saved frame cannot push the image out of its box', () => {
  const broken = { track_image_crops: { Spa: { zoom: 9, x: -20, y: 'abc' } } }
  assert.deepEqual(trackImageFrame(broken, 'Spa'), { zoom: 3, x: 0, y: 50 })
  assert.deepEqual(trackImageFrame({ track_image_crops: { Spa: { zoom: 0.2, x: 140, y: 12 } } }, 'Spa'), { zoom: 1, x: 100, y: 12 })
  assert.deepEqual(trackImageFrame({ track_image_crops: { Spa: 'oops' } }, 'Spa'), DEFAULT_TRACK_FRAME)
})

test('the frame becomes a focus point and a zoom around it', () => {
  assert.deepEqual(trackImageStyle({ zoom: 1.6, x: 30, y: 70 }), {
    objectPosition: '30% 70%',
    transformOrigin: '30% 70%',
    transform: 'scale(1.6)'
  })
  // Nothing to apply for the default frame: the image keeps its own styles.
  assert.deepEqual(trackImageStyle(DEFAULT_TRACK_FRAME), {})
  assert.deepEqual(trackImageStyle(null), {})
})
