import test from 'node:test'
import assert from 'node:assert/strict'
import { pilotSurname } from '../src/pilotDisplay.js'

test('the surname is the last name of the first record that knows it', () => {
  assert.equal(pilotSurname('Victor Rezov', { first_name: 'Victor', last_name: 'Rezov' }), 'Rezov')
  assert.equal(pilotSurname('Victor Rezov', null, { last_name: '  Rezov ' }), 'Rezov')
  assert.equal(pilotSurname('Victor Rezov', { last_name: '' }, { last_name: 'Rezov' }), 'Rezov')
})

test('without a last name the pilot keeps the whole name they go by', () => {
  assert.equal(pilotSurname('Senna_88', { first_name: '', last_name: null }), 'Senna_88')
  assert.equal(pilotSurname(' Senna_88 '), 'Senna_88')
  assert.equal(pilotSurname(null), '')
})
