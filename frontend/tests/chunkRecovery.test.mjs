import assert from 'node:assert/strict'
import test from 'node:test'
import { canReloadAgain, isChunkLoadError } from '../src/chunkRecovery.js'

test('missing page chunks are recognised in every major browser', () => {
  assert.ok(isChunkLoadError(new TypeError('Failed to fetch dynamically imported module: https://bmrl.site/assets/TeamList-1.js')))
  assert.ok(isChunkLoadError(new TypeError('Importing a module script failed.')))
  assert.ok(isChunkLoadError(new TypeError('error loading dynamically imported module')))
  assert.ok(isChunkLoadError(new Error('Unable to preload CSS for /assets/TeamList-1.css')))
})

test('ordinary errors do not trigger a reload', () => {
  assert.equal(isChunkLoadError(new Error('Race not found')), false)
  assert.equal(isChunkLoadError(null), false)
})

test('a second failure within ten seconds does not reload again', () => {
  assert.equal(canReloadAgain(null, 1000), true)
  assert.equal(canReloadAgain(1000, 5000), false)
  assert.equal(canReloadAgain(1000, 11000), true)
})
