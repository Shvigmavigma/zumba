import assert from 'node:assert/strict'
import test from 'node:test'
import { countryCode } from '../src/countries.js'

test('country codes resolve from English, Russian or ISO values', () => {
  assert.equal(countryCode('Russia'), 'RU')
  assert.equal(countryCode('Казахстан'), 'KZ')
  assert.equal(countryCode('de'), 'DE')
})

test('unknown or empty countries have no code', () => {
  assert.equal(countryCode(''), '')
  assert.equal(countryCode(null), '')
  assert.equal(countryCode('Atlantis'), '')
})
