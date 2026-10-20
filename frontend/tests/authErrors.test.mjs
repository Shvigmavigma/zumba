import assert from 'node:assert/strict'
import test from 'node:test'
import { friendlyAuthError } from '../src/authErrors.js'

const t = (key, values) => (values ? `${key}:${JSON.stringify(values)}` : key)

test('known server messages map to friendly copy', () => {
  assert.deepEqual(friendlyAuthError(t, 'Invalid credentials'), { text: 'authPage.serverErrors.invalidCredentials', resetSteam: false })
  assert.equal(friendlyAuthError(t, 'Steam authentication was cancelled').text, 'authPage.serverErrors.steamCancelled')
  assert.equal(friendlyAuthError(t, 'Steam account is not linked').text, 'authPage.serverErrors.steamNotLinked')
})

test('single-use Steam confirmations are reset after a consuming error', () => {
  assert.equal(friendlyAuthError(t, 'Login, email or Steam ID already exists').resetSteam, true)
  assert.equal(friendlyAuthError(t, 'Steam authentication is required').resetSteam, true)
  assert.equal(friendlyAuthError(t, 'Invalid credentials').resetSteam, false)
})

test('account status errors include the translated status', () => {
  const result = friendlyAuthError(t, 'Account status is banned')
  assert.equal(result.text, 'authPage.serverErrors.accountStatus:{"status":"statuses.banned"}')
})

test('unknown messages pass through unchanged', () => {
  assert.deepEqual(friendlyAuthError(t, 'Something else'), { text: 'Something else', resetSteam: false })
  assert.deepEqual(friendlyAuthError(t, undefined), { text: '', resetSteam: false })
})
