import assert from 'node:assert/strict'
import test from 'node:test'
import { safeHttpUrl } from '../src/safeUrl.js'

test('web links and same-site paths pass unchanged', () => {
  assert.equal(safeHttpUrl('https://getpc.ru/racing'), 'https://getpc.ru/racing')
  assert.equal(safeHttpUrl(' http://example.com '), 'http://example.com')
  assert.equal(safeHttpUrl('/championships'), '/championships')
  assert.equal(safeHttpUrl('//cdn.example.com/a'), 'https://cdn.example.com/a')
})

test('script and data links are dropped', () => {
  assert.equal(safeHttpUrl('javascript:alert(1)'), '')
  assert.equal(safeHttpUrl(' JaVaScRiPt:alert(1)'), '')
  assert.equal(safeHttpUrl('data:text/html,<b>x</b>'), '')
  assert.equal(safeHttpUrl('vbscript:msgbox(1)'), '')
})

test('empty, malformed and ambiguous values are dropped', () => {
  assert.equal(safeHttpUrl(''), '')
  assert.equal(safeHttpUrl(null), '')
  assert.equal(safeHttpUrl('not a url'), '')
  assert.equal(safeHttpUrl('/\\evil.example.com'), '')
})
