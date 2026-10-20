// How the GETPC pilot moves (ThemePilot.vue, rig in pilotRig.js). A pose is a
// set of joint targets — the body's shift and lean, the head's tilt and nod,
// each arm's shoulder, elbow and wrist, and how open each hand is (0 a fist, 1
// open) — in the drawing's pixels and degrees
// (clockwise, like CSS rotate), found by placing the hands where they should
// be and solving for the joints with the bending the scene uses. He never jumps to a pose: every joint is a
// spring pulling towards it, the elbows looser than the shoulders, so the
// forearms follow a beat behind and settle with a little sway, the way arms
// do. On top of the pose he stays alive: he breathes, shifts his weight,
// nods along as he talks, and some poses keep moving (shaking his head in his
// hands, waving, pumping his fist).

export const JOINTS = Object.freeze(['x', 'y', 'lean', 'tilt', 'nod', 'Ls', 'Le', 'Lw', 'Lo', 'Rs', 'Re', 'Rw', 'Ro'])

const pose = (body, head, L, R) => ({
  x: body[0], y: body[1], lean: body[2], tilt: head[0], nod: head[1],
  Ls: L[0], Le: L[1], Lw: L[2], Lo: L[3] ?? 0, Rs: R[0], Re: R[1], Rw: R[2], Ro: R[3] ?? 0
})

export const POSES = Object.freeze({
  // Arms hanging, as drawn: how he comes up from below.
  rise: pose([0, 0, 0], [0, 0], [0, 0, 0], [0, 0, 0]),
  // Before the big move, he gathers himself: knees give, fists draw in.
  crouch: pose([0, 18, 0], [0, 8], [10, -14, 6], [-10, 14, -6]),
  // Both fists up beside his helmet, elbows wide, knuckles up: the boss.
  windup: pose([0, -14, 0], [0, -8], [112, 111, -59], [-114, -124, 57]),
  // Down on the box, hard...
  slam: pose([0, 18, 0], [0, 12], [33, -101, 57], [-27, 90, -69]),
  // ...and leaning on it, fists square on its edge.
  box: pose([0, 6, 0], [0, 0], [33, -101, 57], [-27, 90, -69]),
  // "Are you sure?": he unclenches his fists and holds his helmet, fingers on its sides.
  head: pose([0, 4, 0], [-3, 8], [130, 136, -81, 1], [-139, -142, 79, 1]),
  // "Once, or for good?": hands on his hips, elbows wide, knuckles in.
  hips: pose([0, -6, 0], [4, 0], [51, -122, 25], [-44, 110, -37]),
  // "See ya": a raised fist, the other on his hip.
  wave: pose([-6, -2, -1.5], [-5, 0], [106, 97, -44], [-44, 110, -37]),
  // Backing out: "yes!", elbow by his side and the fist up, the other fist on the box.
  pump: pose([4, 0, 1.5], [4, 4], [33, -101, 57], [11, -149, -38])
})

/** The pose for each line of the talk. */
export const LINE_POSES = Object.freeze({ warn: 'box', sure: 'head', howLong: 'hips', bye: 'wave' })

// How each joint follows: frequency (Hz) and damping (1 = no sway). Elbows are
// looser than shoulders, so forearms trail and swing a little past.
export const SPRINGS = Object.freeze({
  x: [1.8, 0.8],
  y: [2.2, 0.72],
  lean: [1.6, 0.8],
  tilt: [3, 0.55],
  nod: [3.4, 0.5],
  Ls: [2.6, 0.7],
  Rs: [2.6, 0.7],
  Le: [1.6, 0.5],
  Re: [1.6, 0.5],
  Lw: [2.4, 0.6],
  Rw: [2.4, 0.6],
  Lo: [3.2, 0.95],
  Ro: [3.2, 0.95]
})

/** Every joint at rest in a pose, not moving. */
export function restingAt(name) {
  const target = POSES[name]
  return Object.fromEntries(JOINTS.map((joint) => [joint, { value: target[joint], speed: 0 }]))
}

const STEP = 1 / 240

/**
 * Moves every joint towards its target for `dt` seconds, as damped springs.
 * Returns a new state; the old one is left as it was.
 * @param {Record<string, { value: number, speed: number }>} state
 * @param {Record<string, number>} target
 * @param {number} dt  seconds
 * @param {number} [quickness]  >1 makes every spring stiffer (a fast, hard move)
 */
export function stepSprings(state, target, dt, quickness = 1) {
  const next = {}
  for (const joint of JOINTS) {
    const [hz, damping] = SPRINGS[joint]
    const w = 2 * Math.PI * hz * quickness
    let { value, speed } = state[joint]
    const goal = target[joint]
    for (let t = 0; t < dt - 1e-9; t += STEP) {
      const h = Math.min(STEP, dt - t)
      speed += (w * w * (goal - value) - 2 * damping * w * speed) * h
      value += speed * h
    }
    next[joint] = { value, speed }
  }
  return next
}

/** A push on some joints (pixels or degrees per second), e.g. a nod as he speaks or the jolt of the slam. */
export function kick(state, pushes) {
  const next = { ...state }
  for (const [joint, push] of Object.entries(pushes)) next[joint] = { ...state[joint], speed: state[joint].speed + push }
  return next
}

const wave = (seconds, hz, phase = 0) => Math.sin(2 * Math.PI * hz * seconds + phase)

/**
 * Where the joints are headed now: the pose, with him alive on top of it.
 * @param {string} name  the pose
 * @param {number} sinceOpen  ms since the scene opened (breathing, weight)
 * @param {number} sincePose  ms since he took this pose (moves that fade or repeat)
 * @returns {Record<string, number>}
 */
export function liveTarget(name, sinceOpen, sincePose) {
  const t = sinceOpen / 1000
  const p = sincePose / 1000
  const target = { ...POSES[name] }
  // Breathing: chest and shoulders rise and fall.
  const breath = wave(t, 1 / 3.6)
  target.y += breath * 3
  target.Ls += breath * 0.8
  target.Rs -= breath * 0.8
  // Weight shifting from foot to foot.
  target.x += wave(t, 1 / 5.3) * 3
  target.lean += wave(t, 1 / 5.3, 1) * 0.4
  target.tilt += wave(t, 1 / 7.1, 2) * 1.2
  if (name === 'head') target.tilt += wave(p, 1.1) * 7
  if (name === 'wave') {
    target.Le += wave(p, 1.6) * 18
    target.Ls += wave(p, 1.6, 0.5) * 4
    target.Lw += wave(p, 1.6, -0.6) * 10
  }
  if (name === 'pump' && p < 1.4) target.Re -= Math.max(0, wave(p, 2.2)) * 24
  if (name === 'windup') {
    target.Le += wave(p, 9) * 1.5
    target.Re -= wave(p, 9) * 1.5
    target.y += wave(p, 7) * 1
  }
  return target
}

/** The pushes of a spoken word: a small nod, a turn of the head one way or the other. */
export function wordNod(index) {
  return { nod: 42, tilt: index % 2 ? 16 : -16 }
}
