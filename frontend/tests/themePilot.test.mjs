import test from 'node:test'
import assert from 'node:assert/strict'
import { DIALOGUE, FIRST_LINE, PILOT_ASK_KEY, THEME_ONCE_KEY, answer, pilotStillAsks, readTheme, saveTheme, stopPilotAsking } from '../src/shell/themePilot.js'

function memoryStorage(initial = {}) {
  const data = new Map(Object.entries(initial))
  return {
    getItem: (key) => (data.has(key) ? data.get(key) : null),
    setItem: (key, value) => data.set(key, String(value)),
    removeItem: (key) => data.delete(key),
    data
  }
}

const blocked = {
  getItem() { throw new Error('blocked') },
  setItem() { throw new Error('blocked') },
  removeItem() { throw new Error('blocked') }
}

// ---------- The talk ----------

test('he opens with the warning, and the answers come in the order they were asked for', () => {
  assert.equal(FIRST_LINE, 'warn')
  assert.deepEqual(DIALOGUE.warn.map((choice) => choice.id), ['refuse', 'want'])
  assert.deepEqual(DIALOGUE.sure.map((choice) => choice.id), ['yes', 'refuse'])
  assert.deepEqual(DIALOGUE.howLong.map((choice) => choice.id), ['once', 'forever'])
  assert.deepEqual(DIALOGUE.bye, [])
})

test('seeing it through: warning, are you sure, once or for good, goodbye', () => {
  assert.deepEqual(answer('warn', 'want'), { line: 'sure', outcome: null })
  assert.deepEqual(answer('sure', 'yes'), { line: 'howLong', outcome: null })
  assert.deepEqual(answer('howLong', 'once'), { line: 'bye', outcome: 'once' })
  assert.deepEqual(answer('howLong', 'forever'), { line: 'bye', outcome: 'forever' })
})

test('backing out at either question ends the talk and leaves the theme alone', () => {
  assert.deepEqual(answer('warn', 'refuse'), { line: null, outcome: null })
  assert.deepEqual(answer('sure', 'refuse'), { line: null, outcome: null })
})

test('an answer he does not know ends the talk too', () => {
  assert.deepEqual(answer('warn', 'yes'), { line: null, outcome: null })
  assert.deepEqual(answer('nope', 'want'), { line: null, outcome: null })
})

// ---------- Asking, and keeping the theme ----------

test('he asks until told not to, and asks anyway when storage is blocked', () => {
  const local = memoryStorage()
  assert.equal(pilotStillAsks(local), true)
  stopPilotAsking(local)
  assert.equal(local.getItem(PILOT_ASK_KEY), 'never')
  assert.equal(pilotStillAsks(local), false)
  assert.equal(pilotStillAsks(blocked), true)
  assert.equal(pilotStillAsks(null), true)
  assert.doesNotThrow(() => stopPilotAsking(blocked))
})

test('light just this once lives in the tab; the saved choice stays dark', () => {
  const local = memoryStorage()
  const session = memoryStorage()
  saveTheme('light', true, local, session)
  assert.equal(local.getItem('theme'), 'dark')
  assert.equal(session.getItem(THEME_ONCE_KEY), 'light')
  assert.deepEqual(readTheme(local, session), { theme: 'light', once: true })
  // A new tab (an empty session) opens dark again.
  assert.deepEqual(readTheme(local, memoryStorage()), { theme: 'dark', once: false })
})

test('light for good is saved as before, and dark undoes a light taken once', () => {
  const local = memoryStorage()
  const session = memoryStorage({ [THEME_ONCE_KEY]: 'light' })
  saveTheme('light', false, local, session)
  assert.equal(local.getItem('theme'), 'light')
  assert.equal(session.getItem(THEME_ONCE_KEY), null)
  assert.deepEqual(readTheme(local, session), { theme: 'light', once: false })

  const tab = memoryStorage({ [THEME_ONCE_KEY]: 'light' })
  saveTheme('dark', false, local, tab)
  assert.equal(local.getItem('theme'), 'dark')
  assert.equal(tab.getItem(THEME_ONCE_KEY), null)
})

test('without storage the site opens dark and keeping the theme does not throw', () => {
  assert.deepEqual(readTheme(blocked, blocked), { theme: 'dark', once: false })
  assert.deepEqual(readTheme(null, null), { theme: 'dark', once: false })
  assert.doesNotThrow(() => saveTheme('light', true, blocked, blocked))
})

