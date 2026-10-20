import assert from 'node:assert/strict'
import test from 'node:test'
import { roleList } from '../src/pilotRoles.js'
import { seasonTitleRole } from '../src/seasonChampion.js'

const title = { id: 10, name: 'Победитель BMRL CHAMPIONSHIP 1' }

test('roles are a list, whatever shape the data has them in', () => {
  assert.deepEqual(roleList([title, null, { id: 2, name: 'Steward' }]), [title, { id: 2, name: 'Steward' }])
  // Some stored result rows carry a single role instead of a list.
  assert.deepEqual(roleList(title), [title])
  for (const value of [null, undefined, '', 'Steward', 7, {}, { id: 3 }]) {
    assert.deepEqual(roleList(value), [], JSON.stringify(value))
  }
})

test('a season title is found in a single role as well as in a list', () => {
  assert.equal(seasonTitleRole({ pilot_roles: title }), title)
  assert.equal(seasonTitleRole({ pilot_roles: [title] }), title)
  assert.equal(seasonTitleRole({ pilot_roles: { id: 2, name: 'Steward' } }), null)
  assert.equal(seasonTitleRole({ pilot_roles: 'oops' }), null)
})
