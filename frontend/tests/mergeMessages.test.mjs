import assert from 'node:assert/strict'
import test from 'node:test'
import { mergeMessages } from '../src/i18n/merge.js'

test('nested locale trees merge without losing siblings', () => {
  const base = { ru: { common: { save: 'Сохранить' }, nav: { main: 'Главная' } } }
  const extra = { ru: { common: { close: 'Закрыть' } }, en: { common: { close: 'Close' } } }
  const merged = mergeMessages(base, extra)
  assert.deepEqual(merged.ru.common, { save: 'Сохранить', close: 'Закрыть' })
  assert.equal(merged.ru.nav.main, 'Главная')
  assert.equal(merged.en.common.close, 'Close')
})

test('merging never mutates the inputs and arrays replace wholesale', () => {
  const base = { ru: { steps: ['a', 'b'] } }
  const extra = { ru: { steps: ['c'] } }
  const merged = mergeMessages(base, extra)
  assert.deepEqual(merged.ru.steps, ['c'])
  assert.deepEqual(base.ru.steps, ['a', 'b'])
})
