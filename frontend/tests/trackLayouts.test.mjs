import assert from 'node:assert/strict'
import test from 'node:test'
import { findTrackLayout, normalizeTrackName } from '../src/ui/track/trackLayouts.js'

test('a track name is compared without case, accents, punctuation or extra spaces', () => {
  assert.equal(normalizeTrackName('  Silverstone  Circuit '), 'silverstone circuit')
  assert.equal(normalizeTrackName('Silverstone - GP'), 'silverstone gp')
  assert.equal(normalizeTrackName('Nürburgring_GP'), 'nurburgring gp')
  assert.equal(normalizeTrackName('Spa-Francorchamps'), 'spa francorchamps')
  assert.equal(normalizeTrackName(null), '')
})

test('Silverstone is found under the names the simulators give its Grand Prix layout', () => {
  for (const track of ['Silverstone', 'silverstone', 'Silverstone Circuit', 'Silverstone GP', 'Silverstone - GP', 'Silverstone Grand Prix', 'SILVERSTONE  CIRCUIT']) {
    assert.equal(findTrackLayout({ track })?.id, 'silverstone', track)
  }
})

test('the site\'s track id finds the layout whatever the track is called', () => {
  assert.equal(findTrackLayout({ track: 'Сильверстоун', trackId: 'silverstone' })?.id, 'silverstone')
  assert.equal(findTrackLayout({ track: '', trackId: 'Silverstone' })?.id, 'silverstone')
})

test('another layout of the same circuit is another track', () => {
  for (const track of ['Silverstone National', 'Silverstone - International', 'Silverstone 1967', 'Silverstone Historic GP', 'Silverstone Stowe']) {
    assert.equal(findTrackLayout({ track }), null, track)
  }
})

test('a track without a drawn layout has none', () => {
  for (const track of ['Imola', 'Spa-Francorchamps', 'Zandvoort', '', null, undefined]) {
    assert.equal(findTrackLayout({ track }), null, String(track))
  }
  assert.equal(findTrackLayout({ track: 'Monza', trackId: 'monza' }), null)
  assert.equal(findTrackLayout(null), null)
})

test('a layout is loaded on demand, with the centre line the component draws', async () => {
  const layout = findTrackLayout({ track: 'Silverstone' })
  assert.equal(typeof layout.load, 'function')
  const data = await layout.load()
  assert.equal(data.id, 'silverstone')
  assert.ok(typeof data.points === 'string' && data.points.length > 100)
  assert.equal(data.sectorLines.length, 2)
})

test('Red Bull Ring is found under the names the simulators give its Grand Prix layout', () => {
  for (const track of ['Red Bull Ring', 'red bull ring', 'Red Bull Ring GP', 'Red Bull Ring - GP', 'Red Bull Ring GP - LFM', 'Red Bull Ring Grand Prix', 'RedBull Ring', 'ks_red_bull_ring', 'Spielberg', 'Red Bull Ring (GT2 Pack)']) {
    assert.equal(findTrackLayout({ track })?.id, 'red-bull-ring', track)
  }
})

test('the site\'s track id finds Red Bull Ring, hyphens and all', () => {
  assert.equal(findTrackLayout({ track: 'Ред Булл Ринг', trackId: 'red-bull-ring' })?.id, 'red-bull-ring')
  assert.equal(findTrackLayout({ track: '', trackId: 'Red-Bull-Ring' })?.id, 'red-bull-ring')
  // ACC keeps the name of the add-on in the track's name and id
  assert.equal(findTrackLayout({ track: 'Ред Булл Ринг', trackId: 'red-bull-ring-gt2-pack' })?.id, 'red-bull-ring')
})

test('the short layouts of the Red Bull Ring are other tracks', () => {
  for (const track of ['Red Bull Ring National', 'Red Bull Ring - Südschleife', 'Red Bull Ring Short', 'Red Bull Ring MotoGP', 'Österreichring']) {
    assert.equal(findTrackLayout({ track }), null, track)
  }
})

test('Red Bull Ring is loaded on demand with its ten corners and two sector lines', async () => {
  const data = await findTrackLayout({ trackId: 'red-bull-ring' }).load()
  assert.equal(data.id, 'red-bull-ring')
  assert.ok(typeof data.points === 'string' && data.points.length > 100)
  assert.deepEqual(data.corners.map((corner) => corner.n), [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
  assert.equal(data.sectorLines.length, 2)
})
