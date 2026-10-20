import assert from 'node:assert/strict'
import test from 'node:test'
import { speedTrace, trackSeed } from '../src/pages/pilots/trackTelemetry.js'

const BOX = { width: 1000, height: 200 }

test('a track always gets the same trace', () => {
  assert.equal(trackSeed('Barcelona'), trackSeed('Barcelona'))
  assert.deepEqual(speedTrace('Barcelona', BOX), speedTrace('Barcelona', BOX))
})

test('different tracks get different traces', () => {
  assert.notEqual(trackSeed('Barcelona'), trackSeed('Imola'))
  assert.notEqual(speedTrace('Barcelona', BOX).line, speedTrace('Imola', BOX).line)
  // Letter case and stray spaces do not make it another track.
  assert.equal(speedTrace(' barcelona ', BOX).line, speedTrace('Barcelona', BOX).line)
})

test('the trace runs left to right and stays inside its box', () => {
  for (const name of ['Barcelona', 'Imola', 'Spa-Francorchamps', 'Нижегородское кольцо', '']) {
    const { points } = speedTrace(name, BOX)
    assert.ok(points.length >= 12, name)
    assert.equal(points[0][0], 0, name)
    assert.equal(points[points.length - 1][0], BOX.width, name)
    points.forEach(([x, y], index) => {
      assert.ok(y >= 0 && y <= BOX.height, `${name}: y of point ${index}`)
      if (index > 0) assert.ok(x > points[index - 1][0], `${name}: x of point ${index}`)
    })
  }
})

test('the line and the area under it are valid paths over the same points', () => {
  const { line, area, points } = speedTrace('Monza', BOX)
  assert.match(line, /^M0 [\d.]+( [QLT][\d. ]+)+$/)
  assert.ok(area.startsWith(line))
  assert.ok(area.endsWith(`L${BOX.width} ${BOX.height} L0 ${BOX.height} Z`))
  assert.ok(!/NaN|undefined/.test(line))
  assert.ok(line.includes(String(points[points.length - 1][1])))
})

test('a lap has three sectors', () => {
  const { sectors } = speedTrace('Monza', BOX)
  assert.equal(sectors.length, 2)
  assert.ok(sectors[0] > BOX.width * 0.25 && sectors[0] < BOX.width * 0.42)
  assert.ok(sectors[1] > BOX.width * 0.58 && sectors[1] < BOX.width * 0.75)
})
