import test from 'node:test'
import assert from 'node:assert/strict'
import { bendArm, gridMesh, makeSpine, prepareArm, project, tiltHead } from '../src/shell/pilotDeform.js'
import { PILOT_RIG } from '../src/shell/pilotRig.js'

// An arm like the drawing's left one: a band about 120 px wide along its spine, points every 10 px.
const SPINE = PILOT_RIG.L.spine
function armPoints() {
  const spine = makeSpine(SPINE)
  const points = []
  for (let s = 0; s <= spine.length; s += 10) {
    for (let d = -55; d <= 55; d += 10) {
      const segment = spine.segments.find((item) => s <= item.s0 + item.len) || spine.segments.at(-1)
      const t = s - segment.s0
      points.push(segment.ax + segment.ux * t - segment.uy * d, segment.ay + segment.uy * t + segment.ux * d)
    }
  }
  return Float32Array.from(points)
}
const columns = 12
const neighbours = (points) => {
  const pairs = []
  const count = points.length / 2
  for (let i = 0; i < count; i += 1) {
    if ((i + 1) % columns) pairs.push([i, i + 1])
    if (i + columns < count) pairs.push([i, i + columns])
  }
  return pairs
}
const gap = (points, [a, b]) => Math.hypot(points[a * 2] - points[b * 2], points[a * 2 + 1] - points[b * 2 + 1])

test('a point is found along the spine and across it', () => {
  const spine = makeSpine([[0, 0], [0, 100], [0, 200]])
  assert.deepEqual(project(spine, 10, 50), { s: 50, d: -10 })
  assert.deepEqual(project(spine, -5, 150), { s: 150, d: 5 })
  // Beyond the ends the spine goes on straight.
  assert.equal(project(spine, 0, -20).s, -20)
  assert.equal(project(spine, 0, 230).s, 230)
})

test('at rest the arm is exactly the drawing', () => {
  const rest = armPoints()
  const arm = prepareArm(SPINE, rest)
  const out = bendArm(arm, { shoulder: 0, elbow: 0, wrist: 0 })
  for (let i = 0; i < rest.length; i += 1) assert.ok(Math.abs(out[i] - rest[i]) < 1e-3, `point ${i}`)
})

test('bent hard, the arm does not tear: neighbouring points stay neighbours', () => {
  const rest = armPoints()
  const arm = prepareArm(SPINE, rest)
  for (const pose of [
    { shoulder: 125, elbow: 122, wrist: -74 },
    { shoulder: 50, elbow: -107, wrist: 20 },
    { shoulder: 120, elbow: 83, wrist: -30 },
    { shoulder: -40, elbow: -153, wrist: 19 }
  ]) {
    const out = bendArm(arm, pose)
    for (const pair of neighbours(rest)) {
      // Never torn apart: at most stretched to two and a half times, on the outside of a hard bend.
      const stretch = gap(out, pair) / gap(rest, pair)
      assert.ok(stretch < 2.5, `${JSON.stringify(pose)} ${pair} x${stretch.toFixed(2)}`)
    }
  }
})

test('the top of the arm stays on the shoulder whatever the arm does', () => {
  const rest = armPoints()
  const arm = prepareArm(SPINE, rest)
  const out = bendArm(arm, { shoulder: 125, elbow: 122, wrist: 0 })
  // The first rows: the inside of the shoulder.
  for (let i = 0; i < columns * 2; i += 1) {
    assert.ok(Math.abs(out[i * 2] - rest[i * 2]) < 0.5 && Math.abs(out[i * 2 + 1] - rest[i * 2 + 1]) < 0.5, `point ${i}`)
  }
})

test('the shoulder carries the whole arm round: the fist goes where the angle sends it', () => {
  const rest = armPoints()
  const arm = prepareArm(SPINE, rest)
  const out = bendArm(arm, { shoulder: 90, elbow: 0, wrist: 0 })
  const [sx, sy] = SPINE[1]
  const last = rest.length / 2 - columns / 2
  const restAngle = Math.atan2(rest[last * 2 + 1] - sy, rest[last * 2] - sx)
  const bentAngle = Math.atan2(out[last * 2 + 1] - sy, out[last * 2] - sx)
  let turned = ((bentAngle - restAngle) * 180) / Math.PI
  turned = ((turned % 360) + 360) % 360
  assert.ok(Math.abs(turned - 90) < 12, `turned ${turned.toFixed(1)}°`)
})

test('the fist turns at the wrist; the sleeve up to it stays as it is', () => {
  const rest = armPoints()
  const arm = prepareArm(SPINE, rest)
  const out = bendArm(arm, { shoulder: 0, elbow: 0, wrist: 60 })
  const [, , , wristAt] = arm.spine.at
  for (let i = 0; i < arm.s.length; i += 1) {
    const moved = Math.hypot(out[i * 2] - rest[i * 2], out[i * 2 + 1] - rest[i * 2 + 1])
    if (arm.s[i] < wristAt - 30) assert.ok(moved < 1e-3, 'sleeve still')
    else if (arm.s[i] > wristAt + 80) assert.ok(moved > 40, 'fist turned')
  }
})

test('the helmet tilts at the top and holds at the chin', () => {
  const neck = [100, 300]
  const rest = Float32Array.from([100, 320, 60, 314, 100, 200, 160, 180])
  const out = tiltHead(rest, neck, 10, 6)
  assert.ok(Math.abs(out[0] - 100) < 1e-6 && Math.abs(out[1] - 320) < 1e-6, 'below the chin line: still')
  assert.ok(Math.abs(out[2] - 60) < 1e-6 && Math.abs(out[3] - 314) < 1e-6, 'at the chin: still')
  const top = Math.hypot(out[4] - 100, out[5] - 200)
  assert.ok(top > 15, 'the top swings')
  assert.ok(Math.abs(Math.hypot(out[6] - 100, out[7] - 306) - Math.hypot(160 - 100, 180 - 300)) < 8, 'about the neck, nodded down')
})

test('a mesh covers what is drawn and nothing more', () => {
  // A 40 x 30 part with a drawn 10 x 10 square in its middle.
  const alphaAt = (x, y) => (x >= 15 && x < 25 && y >= 10 && y < 20 ? 255 : 0)
  const mesh = gridMesh(alphaAt, { x: 100, y: 200, w: 40, h: 30 }, 10)
  assert.ok(mesh.indices.length >= 6 && mesh.indices.length <= 6 * 4)
  for (let i = 0; i < mesh.positions.length; i += 2) {
    assert.ok(mesh.positions[i] >= 100 && mesh.positions[i] <= 140)
    assert.ok(mesh.positions[i + 1] >= 200 && mesh.positions[i + 1] <= 230)
  }
  for (const uv of mesh.uvs) assert.ok(uv >= 0 && uv <= 1)
  assert.equal(gridMesh(() => 0, { x: 0, y: 0, w: 30, h: 30 }).indices.length, 0)
})
