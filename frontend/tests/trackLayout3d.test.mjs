// node --test tests/trackLayout3d.test.mjs
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { buildTrack, declutter, distanceAt, fitTable, sceneAt } from '../src/ui/track/trackLayout3d.js'
import redBullRing from '../src/ui/track/tracks/red-bull-ring.js'
import silverstone from '../src/ui/track/tracks/silverstone.js'

const VIEW = { width: 960, height: 540, padding: 44 }
const EDGE = VIEW.padding / 2 // the fit is eased between yaws, so the track may use up to half of the padding
const DEG = Math.PI / 180
const FOCAL = 1500

function pose(track, yaw, pitch) {
  return { yaw: yaw * DEG, pitch: pitch * DEG, distance: distanceAt(fitTable(track, VIEW, pitch * DEG, FOCAL), yaw * DEG), focal: FOCAL }
}

/** Every coordinate pair of an SVG path made of M/L commands. */
function pathPoints(d) {
  return [...d.matchAll(/(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)/g)].map((match) => [Number(match[1]), Number(match[2])])
}

test('builds Silverstone as a closed lap with its 18 corners in driving order', () => {
  // Act
  const track = buildTrack(silverstone)

  // Assert
  assert.ok(Math.abs(track.length / 1000 - silverstone.lapKm) < 0.12, `lap is ${(track.length / 1000).toFixed(3)} km`)
  assert.equal(track.corners.length, 18)
  track.corners.forEach((corner, index) => {
    if (index > 0) assert.ok(corner.s > track.corners[index - 1].s, `corner ${corner.n} is out of order`)
  })
  assert.equal(track.zones.length, 2)
  track.zones.forEach((zone) => assert.ok(zone.to > zone.from, `zone ${zone.id} runs backwards`))
})

test('keeps the whole track inside the view whichever way it is turned', () => {
  // Arrange
  const track = buildTrack(silverstone)

  for (const pitch of [30, 58, 84]) {
    for (let yaw = 0; yaw < 360; yaw += 7) {
      // Act
      const points = pathPoints(sceneAt(track, VIEW, pose(track, yaw, pitch), { roadWidth: 1 }).road)

      // Assert
      assert.ok(points.length > 100, 'the road is drawn')
      points.forEach(([x, y]) => {
        assert.ok(x >= EDGE && x <= VIEW.width - EDGE, `x ${x} leaves the view at yaw ${yaw}, pitch ${pitch}`)
        assert.ok(y >= EDGE && y <= VIEW.height - EDGE, `y ${y} leaves the view at yaw ${yaw}, pitch ${pitch}`)
      })
    }
  }
})

test('draws the lap progressively and shows corners only once it is complete', () => {
  // Arrange
  const track = buildTrack(silverstone)
  const at = pose(track, 0, 58)

  // Act
  const empty = sceneAt(track, VIEW, at, { progress: 0 })
  const half = sceneAt(track, VIEW, at, { progress: 0.5 })
  const full = sceneAt(track, VIEW, at, { progress: 1, lightAt: 1200 })

  // Assert
  assert.equal(empty.road, '')
  assert.ok(half.road.length > 0 && half.road.length < full.road.length)
  assert.equal(half.corners.length, 0)
  assert.equal(full.corners.length, 18)
  assert.ok(full.zones.length > 0 && full.lightTail.length > 0 && full.light !== null)
})

test('accepts points as an array and a track without corners or zones', () => {
  // Arrange: a 400 × 200 m rectangle
  const points = [[0, 0], [400, 0], [400, 200], [0, 200]]

  // Act
  const track = buildTrack({ name: 'Box', points })
  const scene = sceneAt(track, VIEW, pose(track, 90, 58))

  // Assert
  assert.ok(Math.abs(track.length - 1200) < 40, `perimeter is ${track.length.toFixed(0)} m`)
  assert.equal(scene.corners.length, 0)
  assert.equal(scene.zones, '')
  assert.ok(scene.road.length > 0)
})

test('rejects malformed points and zones that name a missing corner', () => {
  assert.throws(() => buildTrack({ name: 'Bad', points: '0,0 10,10' }), /at least four/)
  assert.throws(() => buildTrack({ name: 'Bad', points: '0,0 10,x 20,0 5,5' }), /finite/)
  assert.throws(() => buildTrack({ name: 'Bad', points: [[0, 0], [400, 0], [400, 200], [0, 200]], zones: [{ id: 1, from: [3, 0], to: [4, 0] }] }), /corner 3/)
})

test('moves corner marks apart without losing any, even when the layout is shown small', () => {
  // Arrange: a phone-width layout needs about 74 px of the drawing between marks
  const track = buildTrack(silverstone)
  const corners = sceneAt(track, VIEW, pose(track, 0, 58)).corners
  const spacing = 74

  // Act
  const marks = declutter(corners, spacing)

  // Assert
  assert.equal(marks.length, corners.length)
  marks.forEach((mark, index) => {
    marks.slice(index + 1).forEach((other) => {
      const distance = Math.hypot(mark.markX - other.markX, mark.markY - other.markY)
      assert.ok(distance >= spacing * 0.8, `marks ${mark.n} and ${other.n} are ${distance.toFixed(0)} px apart`)
    })
  })
})

test('leaves marks alone when they already have room', () => {
  // Arrange
  const track = buildTrack(silverstone)
  const corners = sceneAt(track, VIEW, pose(track, 0, 58)).corners

  // Act
  const marks = declutter(corners, 4)

  // Assert
  assert.deepEqual(marks.map((mark) => [mark.markX, mark.markY]), corners.map((corner) => [corner.markX, corner.markY]))
})

test('splits Silverstone into its three timing sectors, the lines on the two long straights', () => {
  // Act
  const track = buildTrack(silverstone)
  const corner = (n) => track.corners.find((item) => item.n === n).s

  // Assert
  assert.equal(track.sectors.length, 3)
  assert.deepEqual(track.sectors.map((sector) => sector.n), [1, 2, 3])
  assert.equal(track.sectors[0].from, 0)
  assert.equal(track.sectors[2].to, track.length)
  assert.equal(track.sectors[0].to, track.sectors[1].from)
  assert.equal(track.sectors[1].to, track.sectors[2].from)
  // Sector 1 ends on the Wellington Straight, sector 2 on the Hangar Straight.
  assert.ok(track.sectors[0].to > corner(5) && track.sectors[0].to < corner(6), `sector 1 ends at ${track.sectors[0].to.toFixed(0)} m`)
  assert.ok(track.sectors[1].to > corner(14) && track.sectors[1].to < corner(15), `sector 2 ends at ${track.sectors[1].to.toFixed(0)} m`)
})

test('a track without sector lines has no sectors to show', () => {
  // Arrange
  const track = buildTrack({ name: 'Box', points: [[0, 0], [400, 0], [400, 200], [0, 200]] })

  // Act
  const scene = sceneAt(track, VIEW, pose(track, 90, 58), { sectors: true })

  // Assert
  assert.deepEqual(track.sectors, [])
  assert.deepEqual(scene.sectors, [])
})

test('draws each sector as its own stretch of road with a mark and a line where it ends', () => {
  // Arrange
  const track = buildTrack(silverstone)
  const at = pose(track, 0, 58)

  // Act
  const full = sceneAt(track, VIEW, at, { sectors: true })
  const early = sceneAt(track, VIEW, at, { sectors: true, progress: 0.1 })
  const off = sceneAt(track, VIEW, at)

  // Assert
  assert.equal(full.sectors.length, 3)
  full.sectors.forEach((sector) => {
    assert.ok(sector.road.length > 0 && sector.glow.length > 0, `sector ${sector.n} is drawn`)
    assert.ok(sector.mark, `sector ${sector.n} has a mark`)
    assert.ok(sector.mark.markX > 0 && sector.mark.markX < VIEW.width && sector.mark.markY > 0 && sector.mark.markY < VIEW.height, `mark of sector ${sector.n} is in view`)
  })
  // The last sector ends on the start line, which is drawn already.
  assert.deepEqual(full.sectors.map((sector) => sector.line.length > 0), [true, true, false])
  // Together the sectors cover the lap once: about as many points as the whole road.
  const sectorPoints = full.sectors.reduce((sum, sector) => sum + pathPoints(sector.road).length, 0)
  assert.ok(Math.abs(sectorPoints - pathPoints(full.road).length) <= 12, `sectors have ${sectorPoints} points`)
  // While the lap is being drawn only what is drawn so far is coloured, and nothing is marked.
  assert.deepEqual(early.sectors.map((sector) => sector.road.length > 0), [true, false, false])
  assert.ok(early.sectors.every((sector) => sector.mark === null && sector.line === ''))
  // Sectors are opt-in: the plain layout does not pay for them.
  assert.deepEqual(off.sectors, [])
})

test('pins a sector where it runs furthest from the middle of the track, so the mark stands outside the layout', () => {
  // Arrange
  const track = buildTrack(silverstone)
  const fromCentre = (s) => {
    const index = Math.round(s / track.step) % track.n
    return Math.hypot(track.px[index] - track.centre.x, track.py[index] - track.centre.y)
  }

  track.sectors.forEach((sector) => {
    // Assert: inside the sector, clear of its ends, and no nearer the middle than the sector's halfway point
    const length = sector.to - sector.from
    assert.ok(sector.pin > sector.from + length * 0.1 && sector.pin < sector.to - length * 0.1, `pin of sector ${sector.n} is at ${sector.pin.toFixed(0)} m`)
    assert.ok(fromCentre(sector.pin) >= fromCentre((sector.from + sector.to) / 2), `pin of sector ${sector.n} is nearer the middle than its halfway point`)
  })
})

test('marks the start line on request, once the lap is drawn', () => {
  // Arrange
  const track = buildTrack(silverstone)
  const at = pose(track, 0, 58)

  // Act
  const full = sceneAt(track, VIEW, at, { startMark: true })
  const early = sceneAt(track, VIEW, at, { startMark: true, progress: 0.5 })
  const off = sceneAt(track, VIEW, at)

  // Assert
  assert.ok(full.startMark && full.startMark.markX > 0 && full.startMark.markX < VIEW.width && full.startMark.markY > 0 && full.startMark.markY < VIEW.height)
  assert.equal(early.startMark, null)
  assert.equal(off.startMark, null)
})

test('builds Red Bull Ring as a closed lap with its 10 corners in driving order', () => {
  // Act
  const track = buildTrack(redBullRing)

  // Assert: the driven line of the timing map is a little shorter than the official 4.326 km
  assert.ok(Math.abs(track.length / 1000 - redBullRing.lapKm) < 0.06, `lap is ${(track.length / 1000).toFixed(3)} km`)
  assert.equal(track.corners.length, 10)
  track.corners.forEach((corner, index) => {
    if (index > 0) assert.ok(corner.s > track.corners[index - 1].s, `corner ${corner.n} is out of order`)
  })
  // The lap starts at the start line, 311 m before the first corner.
  assert.ok(Math.abs(track.corners[0].s - 311) < 12, `corner 1 is ${track.corners[0].s.toFixed(0)} m into the lap`)
})

test('splits Red Bull Ring where the simulator times its sectors', () => {
  // Act
  const track = buildTrack(redBullRing)
  const corner = (n) => track.corners.find((item) => item.n === n).s

  // Assert: Assetto Corsa's gates stand 1095 m and 2705 m into the lap
  assert.equal(track.sectors.length, 3)
  assert.ok(Math.abs(track.sectors[0].to - 1095) < 12, `sector 1 ends at ${track.sectors[0].to.toFixed(0)} m`)
  assert.ok(Math.abs(track.sectors[1].to - 2705) < 12, `sector 2 ends at ${track.sectors[1].to.toFixed(0)} m`)
  assert.ok(track.sectors[0].to > corner(2) && track.sectors[0].to < corner(3))
  assert.ok(track.sectors[1].to > corner(6) && track.sectors[1].to < corner(7))
  assert.equal(track.sectors[2].to, track.length)
})

test('keeps Red Bull Ring inside the view whichever way it is turned', () => {
  // Arrange
  const track = buildTrack(redBullRing)

  for (let yaw = 0; yaw < 360; yaw += 15) {
    // Act
    const points = pathPoints(sceneAt(track, VIEW, pose(track, yaw, 58), { roadWidth: 1 }).road)

    // Assert
    assert.ok(points.length > 100, 'the road is drawn')
    points.forEach(([x, y]) => {
      assert.ok(x >= EDGE && x <= VIEW.width - EDGE, `x ${x} leaves the view at yaw ${yaw}`)
      assert.ok(y >= EDGE && y <= VIEW.height - EDGE, `y ${y} leaves the view at yaw ${yaw}`)
    })
  }
})

test('a zone that runs through the start line is drawn whole', () => {
  // Arrange: a 400 × 200 m rectangle with a corner 100 m into the lap and one 100 m before its end
  const points = [[0, 0], [400, 0], [400, 200], [0, 200]]
  const corners = [{ n: 1, name: 'First', x: 100, y: 0 }, { n: 2, name: 'Last', x: 0, y: 100 }]

  // Act
  const track = buildTrack({ name: 'Box', points, corners, zones: [{ id: 'through', from: [2, 30], to: [1, -40] }] })
  const scene = sceneAt(track, VIEW, pose(track, 90, 58))
  const [zone] = track.zones

  // Assert: 70 m to the line and 60 m after it
  assert.ok(zone.to > zone.from, 'the zone runs forwards')
  assert.ok(Math.abs(zone.to - zone.from - 130) < 12, `the zone is ${(zone.to - zone.from).toFixed(0)} m long`)
  assert.ok(scene.zones.length > 0, 'the zone is drawn')
})

test('Red Bull Ring has three DRS zones, the last one through the start line', () => {
  // Act
  const track = buildTrack(redBullRing)
  const lengths = track.zones.map((zone) => zone.to - zone.from)

  // Assert
  assert.equal(track.zones.length, 3)
  lengths.forEach((length, index) => assert.ok(length > 300 && length < 800, `zone ${index + 1} is ${length.toFixed(0)} m long`))
  assert.ok(track.zones[2].to > track.length, 'the third zone ends after the start line')
})

test('a corner without a name keeps its number and has no name to show', () => {
  // Act
  const track = buildTrack(redBullRing)
  const scene = sceneAt(track, VIEW, pose(track, 90, 58))
  const named = scene.corners.filter((corner) => corner.name)

  // Assert
  assert.equal(scene.corners.length, 10)
  assert.deepEqual(named.map((corner) => corner.n), [1, 2, 3, 4, 7, 9])
  assert.equal(scene.corners.find((corner) => corner.n === 5).name, undefined)
})
