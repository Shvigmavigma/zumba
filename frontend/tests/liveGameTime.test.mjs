import test from 'node:test'
import assert from 'node:assert/strict'
import { readGameTime } from '../src/pages/race/liveGameTime.js'

test('reads a fixed Sol timestamp independently of the viewer time zone', () => {
  assert.deepEqual(readGameTime('sol_03_scattered_clouds_type=17_time=0_mult=0_start=1795219800'), { value: '00:10', estimated: false })
})

test('reads fixed time encoded as seconds since midnight', () => {
  assert.deepEqual(readGameTime('sol_01_clear_type=15_time=64800_mult=0_start=1719700000', null), { value: '18:00', estimated: false })
})

test('leaves uncertain accelerated or unknown time unavailable', () => {
  assert.deepEqual(readGameTime('sol_time=0_mult=0_start=1795219800'), { value: '00:10', estimated: false })
  assert.equal(readGameTime('sol_time=36000_mult=5_start=1795219800', 'Europe/Rome'), null)
  assert.equal(readGameTime('sol_01_clear', 'Europe/Rome'), null)
})
