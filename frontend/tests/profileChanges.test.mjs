import assert from 'node:assert/strict'
import test from 'node:test'
import { changedProfileFields, editableProfile } from '../src/profileChanges.js'

const approved = {
  email: 'pilot@example.com',
  first_name: 'Ivan',
  last_name: 'Petrov',
  nickname: 'Ivan',
  country: null,
  discord: null,
  games: ['ACC', 'AC'],
  avatar_color: '#1652d8'
}

test('an untouched form sends no moderated fields', () => {
  const form = { ...approved, country: '', discord: '', games: ['AC', 'ACC'], avatar_color: '#1652D8' }
  assert.deepEqual(changedProfileFields(form, approved), {})
})

test('only edited fields are sent, with empty optional values as null', () => {
  const form = { ...approved, nickname: 'Ivan QA', discord: '', country: 'Russia' }
  assert.deepEqual(changedProfileFields(form, approved), { nickname: 'Ivan QA', country: 'Russia' })
  assert.deepEqual(changedProfileFields({ ...approved, discord: '' }, { ...approved, discord: 'ivan' }), { discord: null })
})

test('the editable profile keeps edits that still await review', () => {
  const user = { ...approved, pending_profile_changes: { nickname: 'Ivan QA' } }
  assert.equal(editableProfile(user).nickname, 'Ivan QA')
  assert.equal(editableProfile(user).email, approved.email)
  assert.deepEqual(editableProfile(null), {})
})

test('taking back a pending edit sends the approved value again', () => {
  const user = { ...approved, pending_profile_changes: { nickname: 'Ivan QA' } }
  assert.deepEqual(changedProfileFields({ ...approved }, user), { nickname: 'Ivan' })
})
