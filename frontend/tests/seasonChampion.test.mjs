import assert from 'node:assert/strict'
import test from 'node:test'
import { seasonTitleEvent, seasonTitleRole } from '../src/seasonChampion.js'

const pilotWith = (...names) => ({ pilot_roles: names.map((name, index) => ({ id: index + 1, name })) })

test('the winner of a BMRL Championship holds the season title', () => {
  const role = seasonTitleRole(pilotWith('Победитель Nascar', 'Победитель BMRL CHAMPIONSHIP 1'))
  assert.equal(role?.name, 'Победитель BMRL CHAMPIONSHIP 1')
})

test('the role is recognised whatever its case, spacing or language', () => {
  for (const name of ['победитель  bmrl championship 2', 'BMRL Championship Winner', 'Чемпион BMRL Championship', 'BMRL CHAMPIONSHIP 3 — champion']) {
    assert.equal(seasonTitleRole(pilotWith(name))?.name, name, name)
  }
})

test('other roles do not make a season champion', () => {
  for (const name of ['Победитель Nascar', 'Участник BMRL CHAMPIONSHIP 1', '[SIM] Чемпион сезона', 'BMRL CHAMPIONSHIP 1', 'Championship winner']) {
    assert.equal(seasonTitleRole(pilotWith(name)), null, name)
  }
})

test('a pilot without roles, or with hidden roles, has no title', () => {
  assert.equal(seasonTitleRole(null), null)
  assert.equal(seasonTitleRole({}), null)
  assert.equal(seasonTitleRole({ pilot_roles: [] }), null)
  assert.equal(seasonTitleRole({ pilot_roles: [null, { id: 1 }] }), null)
})

test('the championship is read from the role name', () => {
  assert.equal(seasonTitleEvent({ name: 'Победитель BMRL CHAMPIONSHIP 1' }), 'BMRL CHAMPIONSHIP 1')
  assert.equal(seasonTitleEvent({ name: 'BMRL  Championship   Winner' }), 'BMRL Championship')
  assert.equal(seasonTitleEvent(null), '')
})
