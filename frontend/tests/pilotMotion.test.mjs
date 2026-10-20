import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { PILOT_RIG } from '../src/shell/pilotRig.js'
import { JOINTS, LINE_POSES, POSES, SPRINGS, kick, liveTarget, restingAt, stepSprings, wordNod } from '../src/shell/pilotPoses.js'

const settle = (state, target, seconds, quickness = 1) => {
  let next = state
  for (let t = 0; t < seconds; t += 1 / 60) next = stepSprings(next, target, 1 / 60, quickness)
  return next
}

// ---------- The rig ----------

test('every part of the drawing is there and sits inside its frame', () => {
  const { frame, parts } = PILOT_RIG
  for (const [name, box] of Object.entries(parts)) {
    const file = fileURLToPath(new URL(`../src/assets/pilot/pilot-${name}.webp`, import.meta.url))
    assert.ok(existsSync(file), name)
    // A WebP: RIFF....WEBP.
    const head = readFileSync(file).subarray(0, 12).toString('latin1')
    assert.ok(head.startsWith('RIFF') && head.endsWith('WEBP'), name)
    assert.ok(box.x >= 0 && box.y >= 0 && box.x + box.w <= frame.w && box.y + box.h <= frame.h, name)
  }
})

test('the spines run where a body has them: shoulders under the helmet, elbows below, the box at the belt', () => {
  const { neck, L, R, edge, gloveDepth, parts } = PILOT_RIG
  for (const [side, arm, outward] of [['L', L, -1], ['R', R, 1]]) {
    const [inside, shoulder, elbow, wrist, end] = arm.spine
    assert.equal(arm.spine.length, 5, side)
    assert.ok(Math.sign(shoulder[0] - neck[0]) === outward, `${side}: the shoulder is on its side`)
    assert.ok(inside[1] < shoulder[1] && shoulder[1] < elbow[1] && elbow[1] < wrist[1] && wrist[1] < end[1], `${side}: top to bottom`)
    const box = parts[`arm${side}`]
    for (const [x, y] of arm.spine.slice(1)) assert.ok(x >= box.x && x <= box.x + box.w && y >= box.y && y <= box.y + box.h, `${side}: inside its piece`)
  }
  assert.ok(edge > parts.head.y + parts.head.h, 'the box edge is well below the helmet')
  assert.ok(edge < parts.torso.y + parts.torso.h, 'and the torso goes on behind it')
  assert.ok(gloveDepth > 0 && gloveDepth < 150)
})

// ---------- Poses ----------

test('every pose sets every joint, and every line of the talk has its pose', () => {
  for (const [name, pose] of Object.entries(POSES)) {
    for (const joint of JOINTS) assert.equal(typeof pose[joint], 'number', `${name}.${joint}`)
  }
  assert.deepEqual(LINE_POSES, { warn: 'box', sure: 'head', howLong: 'hips', bye: 'wave' })
  for (const name of [...Object.values(LINE_POSES), 'rise', 'crouch', 'windup', 'slam', 'pump']) assert.ok(POSES[name], name)
})

test('the arms mirror each other where a pose is symmetrical, as near as the drawing allows', () => {
  for (const name of ['crouch', 'windup', 'slam', 'box', 'head', 'hips']) {
    for (const joint of ['s', 'e', 'w']) {
      const left = POSES[name][`L${joint}`]
      const right = POSES[name][`R${joint}`]
      assert.ok(Math.abs(left + right) <= 15, `${name}.${joint}: ${left} / ${right}`)
    }
  }
})

// ---------- Springs ----------

test('he settles into a pose and stays there', () => {
  const end = settle(restingAt('rise'), POSES.hips, 4)
  for (const joint of JOINTS) assert.ok(Math.abs(end[joint].value - POSES.hips[joint]) < 0.05, joint)
  for (const joint of JOINTS) assert.ok(Math.abs(end[joint].speed) < 0.5, joint)
})

test('elbows trail the shoulders and swing a little past, like real arms', () => {
  assert.ok(SPRINGS.Le[0] < SPRINGS.Ls[0] && SPRINGS.Le[1] < SPRINGS.Ls[1])
  let state = restingAt('rise')
  let peak = -Infinity
  const shoulderAt = []
  const elbowAt = []
  for (let t = 0; t < 2; t += 1 / 60) {
    state = stepSprings(state, POSES.windup, 1 / 60)
    peak = Math.max(peak, state.Le.value)
    if (Math.abs(t - 0.15) < 1 / 120) {
      shoulderAt.push(state.Ls.value / POSES.windup.Ls)
      elbowAt.push(state.Le.value / POSES.windup.Le)
    }
  }
  assert.ok(peak > POSES.windup.Le, 'the forearm swings past')
  assert.ok(elbowAt[0] < shoulderAt[0], 'and gets there later')
})

test('a stiffer move gets there sooner: the slam', () => {
  const slow = settle(restingAt('windup'), POSES.slam, 0.12)
  const fast = settle(restingAt('windup'), POSES.slam, 0.12, 2.8)
  const left = (state) => Math.abs(state.Ls.value - POSES.slam.Ls)
  assert.ok(left(fast) < left(slow))
})

test('a step leaves the state it was given untouched', () => {
  const state = restingAt('rise')
  const copy = JSON.parse(JSON.stringify(state))
  stepSprings(state, POSES.box, 0.1)
  kick(state, { y: 100 })
  assert.deepEqual(state, copy)
})

test('a kick moves him and he comes back', () => {
  const pushed = kick(restingAt('box'), { y: 260, nod: 170 })
  assert.equal(pushed.y.speed, 260)
  let state = pushed
  let lowest = state.y.value
  for (let t = 0; t < 3; t += 1 / 60) {
    state = stepSprings(state, POSES.box, 1 / 60)
    lowest = Math.max(lowest, state.y.value)
  }
  assert.ok(lowest > POSES.box.y + 5, 'the jolt shows')
  assert.ok(Math.abs(state.y.value - POSES.box.y) < 0.1, 'and settles')
})

// ---------- Alive ----------

test('alive, he breathes and shifts his weight, but stays near the pose', () => {
  const samples = [0, 700, 1400, 2100, 2800].map((ms) => liveTarget('box', ms, ms))
  assert.ok(new Set(samples.map((s) => s.y.toFixed(2))).size > 2, 'breathing')
  for (const s of samples) {
    assert.ok(Math.abs(s.y - POSES.box.y) <= 4)
    assert.ok(Math.abs(s.x - POSES.box.x) <= 4)
  }
})

test('the poses that move keep moving: head shaking, waving, the fist pump that stops', () => {
  const tilts = [0, 200, 400, 600].map((ms) => liveTarget('head', 0, ms).tilt)
  assert.ok(Math.max(...tilts) - Math.min(...tilts) > 6, 'shaking his head')
  const waves = [0, 150, 300, 450].map((ms) => liveTarget('wave', 0, ms).Le)
  assert.ok(Math.max(...waves) - Math.min(...waves) > 15, 'waving')
  const pumps = [0, 110, 220, 330].map((ms) => liveTarget('pump', 0, ms).Re)
  assert.ok(Math.min(...pumps) < POSES.pump.Re - 10, 'pumping')
  assert.equal(liveTarget('pump', 0, 2000).Re, POSES.pump.Re, 'then still')
})

test('as he talks, each word is a small nod, the head turning one way, then the other', () => {
  assert.ok(wordNod(0).nod > 0)
  assert.equal(Math.sign(wordNod(0).tilt), -Math.sign(wordNod(1).tilt))
})
