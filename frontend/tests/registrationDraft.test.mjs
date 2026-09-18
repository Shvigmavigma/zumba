import test from 'node:test'
import assert from 'node:assert/strict'
import { registrationDraft } from '../src/registrationDraft.js'

test('registration draft excludes credentials and Steam registration token', () => {
  const draft = registrationDraft({
    login: 'pilot',
    email: 'pilot@example.test',
    password: 'never-store-this',
    password_confirm: 'never-store-this',
    steam_auth_token: 'opaque-token',
    nickname: 'Pilot',
    public_profile_consent: true
  })

  assert.deepEqual(draft, {
    login: 'pilot',
    email: 'pilot@example.test',
    nickname: 'Pilot',
    public_profile_consent: true
  })
})
