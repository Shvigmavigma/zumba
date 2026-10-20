import assert from 'node:assert/strict'
import test from 'node:test'
import { isModLink, modsNoticeKey, requiredMods } from '../src/pages/race/raceMods.js'

test('a race needs mods only when its list has something in it', () => {
  assert.deepEqual(requiredMods({ mods_pack: ['  BMRL pack ', '', null, 'https://example.com/mod'] }), ['BMRL pack', 'https://example.com/mod'])
  assert.deepEqual(requiredMods({ mods_pack: [] }), [])
  assert.deepEqual(requiredMods({}), [])
  assert.deepEqual(requiredMods(null), [])
})

test('the reminder is remembered per race and per list of mods', () => {
  const race = { id: 12, mods_pack: ['BMRL pack', 'Track pack'] }
  assert.equal(modsNoticeKey(race), modsNoticeKey({ id: 12, mods_pack: [' BMRL pack', 'Track pack '] }))
  // Staff changed the list: the pilot has to look again.
  assert.notEqual(modsNoticeKey(race), modsNoticeKey({ id: 12, mods_pack: ['BMRL pack', 'Track pack v2'] }))
  assert.notEqual(modsNoticeKey(race), modsNoticeKey({ id: 13, mods_pack: race.mods_pack }))
  assert.equal(modsNoticeKey({ id: 12, mods_pack: [] }), '')
})

test('a mod is a link when it is an address, with or without the scheme', () => {
  for (const mod of ['https://example.com/pack.zip', 'http://example.com', '//cdn.example.com/a', 'www.example.com/pack', 'drive.google.com/file/d/abc']) {
    assert.equal(isModLink(mod), true, mod)
  }
  // A pack's name is not an address: there is nothing to open.
  for (const mod of ['AC BMRL pack', 'BMRLpack', 'Track pack v2.1', '', null]) {
    assert.equal(isModLink(mod), false, String(mod))
  }
})
