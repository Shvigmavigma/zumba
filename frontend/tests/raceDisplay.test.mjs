import assert from 'node:assert/strict'
import { register } from 'node:module'
import test from 'node:test'

register('./helpers/resolveJs.mjs', import.meta.url)

// raceDisplay imports the store, which reads localStorage at module load.
const storage = new Map()
globalThis.localStorage = {
  getItem: (key) => (storage.has(key) ? storage.get(key) : null),
  setItem: (key, value) => storage.set(key, String(value)),
  removeItem: (key) => storage.delete(key)
}

const { dominantWeatherKey, fillPercent, registeredCount, trackImageFor, weatherLabelKey } = await import('../src/raceDisplay.js')

test('grid fill counts pilots or teams and caps at 100%', () => {
  assert.equal(registeredCount({ registered_pilots: [{}, {}, {}] }), 3)
  assert.equal(registeredCount({ is_team_event: true, team_registrations: [{}] }), 1)
  assert.equal(fillPercent({ max_pilots: 4, registered_pilots: [{}, {}] }), 50)
  assert.equal(fillPercent({ max_pilots: 1, registered_pilots: [{}, {}] }), 100)
  assert.equal(fillPercent({ game: 'LMU', max_pilots: 10, registered_pilots: [{}] }), 0)
})

test('the most likely weather wins and maps to an i18n key', () => {
  assert.equal(dominantWeatherKey({ weather_chances: { clear: 20, light_rain: 60 } }), 'light_rain')
  assert.equal(dominantWeatherKey({}), 'clear')
  assert.equal(weatherLabelKey('partly_cloudy'), 'weather.partlyCloudy')
  assert.equal(weatherLabelKey('heavy_rain'), 'weather.heavyRain')
})

test('track artwork is matched per game and case-insensitively', () => {
  const assets = {
    track_images: { Monza: '/acc-monza.png' },
    games: { LMU: { track_images: { 'Spa-Francorchamps': '/lmu-spa.png' } } }
  }
  assert.equal(trackImageFor(assets, { game: 'LMU', track: 'spa-francorchamps' }), '/lmu-spa.png')
  assert.equal(trackImageFor(assets, { game: 'ACC', track: 'monza' }), '/acc-monza.png')
  assert.equal(trackImageFor(assets, { game: 'AC', track: 'Monza' }), '')
  assert.equal(trackImageFor(null, { track: 'Monza' }), '')
})
