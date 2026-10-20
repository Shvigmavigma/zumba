// How the GETPC pilot's drawing bends without tearing (ThemePilot.vue draws
// it with WebGL, pilotGL.js). Each arm is one piece of the drawing laid along
// a spine — from inside the shoulder, through the shoulder joint, the elbow
// and the wrist, to the end of the fist. Every point of the arm keeps where it
// sits along the spine and how far to the side of it; to pose the arm, the
// spine bends at its joints, each bend spread over a short stretch the way a
// sleeve bends over a joint, and every point follows. The top of the spine
// never moves, so the arm stays on the shoulder; the elbow bends rather than
// breaks; the fist turns at the wrist with the arm still in one piece. The helmet
// tilts the same way: fully at the top, not at all at the chin, so it stays on
// the collar. All in the drawing's own pixels; angles clockwise, like CSS.

const STEP = 2

const smooth = (t) => (t <= 0 ? 0 : t >= 1 ? 1 : t * t * (3 - 2 * t))
// A joint bends as an even arc over its stretch: the least stretch on the outside for the angle.
const ramp = (t) => (t <= 0 ? 0 : t >= 1 ? 1 : t)

/**
 * A spine through the given points, with each stretch's length and direction.
 * @param {number[][]} points  [x, y] from the shoulder's inside to the end of the fist
 */
export function makeSpine(points) {
  const segments = []
  let length = 0
  for (let i = 0; i < points.length - 1; i += 1) {
    const [ax, ay] = points[i]
    const [bx, by] = points[i + 1]
    const len = Math.hypot(bx - ax, by - ay)
    segments.push({ ax, ay, ux: (bx - ax) / len, uy: (by - ay) / len, len, s0: length, angle: Math.atan2(by - ay, bx - ax) })
    length += len
  }
  // Where each point of the spine lies along it: the joints.
  const at = [0]
  segments.forEach((segment) => at.push(segment.s0 + segment.len))
  return { points, segments, length, at }
}

/**
 * Where a point stands against the spine: s along it, d across it (+ to the
 * right of the way it runs). Beyond its ends the spine goes on straight.
 */
export function project(spine, x, y) {
  let best = null
  spine.segments.forEach((segment, index) => {
    const along = (x - segment.ax) * segment.ux + (y - segment.ay) * segment.uy
    const first = index === 0
    const last = index === spine.segments.length - 1
    const t = Math.min(last ? Infinity : segment.len, Math.max(first ? -Infinity : 0, along))
    const cx = segment.ax + segment.ux * t
    const cy = segment.ay + segment.uy * t
    const distance = Math.hypot(x - cx, y - cy)
    if (!best || distance < best.distance) {
      const d = (x - cx) * -segment.uy + (y - cy) * segment.ux
      best = { s: segment.s0 + t, d, distance }
    }
  })
  return { s: best.s, d: best.d }
}

function restAngle(spine, s) {
  const { segments } = spine
  for (let i = segments.length - 1; i >= 0; i -= 1) if (s >= segments[i].s0) return segments[i].angle
  return segments[0].angle
}

/**
 * The bent spine, sampled every two pixels: where it runs and which way.
 * @param {object} spine
 * @param {{ at: number, angle: number, soft: number }[]} bends  angle in degrees at s = at, spread over ±soft
 * @param {number} from  first s to sample (may be before the spine's start)
 * @param {number} to  last s
 */
export function bendSpine(spine, bends, from, to) {
  const count = Math.ceil((to - from) / STEP) + 1
  const xs = new Float64Array(count)
  const ys = new Float64Array(count)
  const as = new Float64Array(count)
  const turn = (s) => bends.reduce((sum, bend) => sum + ((bend.angle * Math.PI) / 180) * ramp((s - bend.at + bend.soft) / (2 * bend.soft)), 0)
  const first = spine.segments[0]
  xs[0] = first.ax + first.ux * from
  ys[0] = first.ay + first.uy * from
  as[0] = restAngle(spine, from) + turn(from)
  for (let i = 1; i < count; i += 1) {
    const mid = from + (i - 0.5) * STEP
    const angle = restAngle(spine, mid) + turn(mid)
    xs[i] = xs[i - 1] + Math.cos(angle) * STEP
    ys[i] = ys[i - 1] + Math.sin(angle) * STEP
    as[i] = restAngle(spine, from + i * STEP) + turn(from + i * STEP)
  }
  return { from, xs, ys, as }
}

function placeOn(curve, s, d) {
  const position = (s - curve.from) / STEP
  const i = Math.max(0, Math.min(curve.xs.length - 2, Math.floor(position)))
  const f = Math.max(0, Math.min(1, position - i))
  const x = curve.xs[i] + (curve.xs[i + 1] - curve.xs[i]) * f
  const y = curve.ys[i] + (curve.ys[i + 1] - curve.ys[i]) * f
  const a = curve.as[i] + (curve.as[i + 1] - curve.as[i]) * f
  return [x - Math.sin(a) * d, y + Math.cos(a) * d]
}

/**
 * Everything an arm needs to bend: its spine and where each of its points sits on it.
 * @param {number[][]} spinePoints  shoulder inside, shoulder joint, elbow, wrist, fist end
 * @param {Float32Array} positions  the arm's points at rest, x and y in turn
 */
export function prepareArm(spinePoints, positions) {
  const spine = makeSpine(spinePoints)
  const count = positions.length / 2
  const s = new Float64Array(count)
  const d = new Float64Array(count)
  let low = Infinity
  let high = -Infinity
  for (let i = 0; i < count; i += 1) {
    const p = project(spine, positions[i * 2], positions[i * 2 + 1])
    s[i] = p.s
    d[i] = p.d
    low = Math.min(low, p.s)
    high = Math.max(high, p.s)
  }
  const from = Math.floor(low) - STEP
  const to = Math.ceil(high) + STEP
  return { spine, rest: positions, s, d, from, to, restCurve: bendSpine(spine, [], from, to) }
}

/** How soft each joint of an arm is: the stretch (in pixels along the arm) a bend spreads over. */
export const JOINT_SOFTNESS = Object.freeze({ shoulder: 64, elbow: 60, wrist: 28 })

/**
 * The arm's spine bent for a pose (angles in degrees at the shoulder, elbow and wrist).
 * @param {object} arm  from prepareArm
 * @param {{ shoulder: number, elbow: number, wrist: number }} pose
 */
export function armCurve(arm, pose) {
  const [, shoulderAt, elbowAt, wristAt] = arm.spine.at
  return bendSpine(arm.spine, [
    { at: shoulderAt, angle: pose.shoulder, soft: JOINT_SOFTNESS.shoulder },
    { at: elbowAt, angle: pose.elbow, soft: JOINT_SOFTNESS.elbow },
    { at: wristAt, angle: pose.wrist, soft: JOINT_SOFTNESS.wrist }
  ], arm.from, arm.to)
}

/**
 * A point of a bent spine and the way it runs there (radians), e.g. the wrist, to hold a hand.
 * @returns {{ x: number, y: number, angle: number }}
 */
export function curveAt(curve, s) {
  const [x, y] = placeOn(curve, s, 0)
  const position = (s - curve.from) / STEP
  const i = Math.max(0, Math.min(curve.as.length - 1, Math.round(position)))
  return { x, y, angle: curve.as[i] }
}

/**
 * The arm's points for a pose. At rest it gives back exactly the drawing.
 * @param {object} arm  from prepareArm
 * @param {{ shoulder: number, elbow: number, wrist: number }} pose  degrees
 * @param {Float32Array} [out]
 * @param {object} [curve]  the bent spine, if already worked out (armCurve)
 */
export function bendArm(arm, pose, out = new Float32Array(arm.rest.length), curve = armCurve(arm, pose)) {
  for (let i = 0; i < arm.s.length; i += 1) {
    const s = arm.s[i]
    const d = arm.d[i]
    // Bent minus straight: the drawing itself where nothing bends.
    const [bx, by] = placeOn(curve, s, d)
    const [rx, ry] = placeOn(arm.restCurve, s, d)
    out[i * 2] = arm.rest[i * 2] + bx - rx
    out[i * 2 + 1] = arm.rest[i * 2 + 1] + by - ry
  }
  return out
}

/**
 * The helmet's points for a tilt and a nod about the neck: the whole tilt from
 * 60 px above the neck up, none at the chin, a smooth blend between.
 * @param {Float32Array} rest
 * @param {number[]} neck  [x, y]
 * @param {number} tilt  degrees
 * @param {number} nod  pixels down
 * @param {Float32Array} [out]
 */
export function tiltHead(rest, [nx, ny], tilt, nod, out = new Float32Array(rest.length)) {
  for (let i = 0; i < rest.length; i += 2) {
    const x = rest[i]
    const y = rest[i + 1]
    const weight = smooth((ny + 14 - y) / 74)
    const angle = (tilt * weight * Math.PI) / 180
    const cos = Math.cos(angle)
    const sin = Math.sin(angle)
    out[i] = nx + (x - nx) * cos - (y - ny) * sin
    out[i + 1] = ny + (x - nx) * sin + (y - ny) * cos + nod * weight
  }
  return out
}

/**
 * A mesh over the drawn part of an image: a grid of points every `cell`
 * pixels, a pair of triangles for every cell with something drawn in it.
 * @param {(x: number, y: number) => number} alphaAt  0..255 at a pixel of the part
 * @param {{ x: number, y: number, w: number, h: number }} box  where the part sits in the frame
 * @param {number} [cell]
 */
export function gridMesh(alphaAt, box, cell = 10) {
  const cols = Math.ceil(box.w / cell)
  const rows = Math.ceil(box.h / cell)
  const index = new Map()
  const positions = []
  const uvs = []
  const triangles = []
  const vertex = (gx, gy) => {
    const key = gy * (cols + 1) + gx
    if (!index.has(key)) {
      const px = Math.min(box.w, gx * cell)
      const py = Math.min(box.h, gy * cell)
      index.set(key, positions.length / 2)
      positions.push(box.x + px, box.y + py)
      uvs.push(px / box.w, py / box.h)
    }
    return index.get(key)
  }
  for (let gy = 0; gy < rows; gy += 1) {
    for (let gx = 0; gx < cols; gx += 1) {
      let drawn = false
      for (let y = gy * cell; y < Math.min(box.h, (gy + 1) * cell) && !drawn; y += 2) {
        for (let x = gx * cell; x < Math.min(box.w, (gx + 1) * cell); x += 2) {
          if (alphaAt(x, y) > 8) {
            drawn = true
            break
          }
        }
      }
      if (!drawn) continue
      const a = vertex(gx, gy)
      const b = vertex(gx + 1, gy)
      const c = vertex(gx, gy + 1)
      const d = vertex(gx + 1, gy + 1)
      triangles.push(a, b, c, b, d, c)
    }
  }
  return { positions: Float32Array.from(positions), uvs: Float32Array.from(uvs), indices: Uint16Array.from(triangles) }
}
