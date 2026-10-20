// 3D layout of a circuit: geometry and projection, no dependencies.
// The track is sampled as a closed curve from its centre line; a pinhole camera
// turns it into SVG paths in screen space, so the picture stays sharp at any
// size and corner marks can be pinned to projected points.

const DEG = Math.PI / 180
const SAMPLE_STEP = 5 // metres between track samples
const DENSIFY_STEP = 4
const SMOOTH_PASSES = 6
const CLOSING_OVERLAP = 20 // a lap recorded past its own start repeats the first point within this many metres
const NEAR_PLANE = 24 // metres in front of the camera
const COORD_LIMIT = 30000
const FIT_YAW_STEP = 15 // degrees between the yaws the fit is worked out for
const FIT_SAMPLE_EVERY = 6
const FIT_STEPS = 18
const FIT_SLACK = 1.04 // between two worked-out yaws the track may need a touch more room
const GRID_STEP = 100
const GRID_MARGIN = 500
const BADGE_OFFSET = 26 // px from a corner to its mark, away from the middle of the track
const SECTOR_OFFSET = 58 // px from a sector's pin to its mark: an outer ring, clear of the corner marks
const SECTOR_PIN_MARGIN = 0.15 // a sector is pinned away from its ends, by this share of its length
const LIGHT_TAIL = 150 // metres
const DECLUTTER_PASSES = 10
const ROAD = { glow: 2.6, edge: 1.16, dash: 0.055, zone: 0.8, startLine: 0.14, sectorLine: 0.1, sectorLineReach: 1.7, dashLength: 12, dashGap: 10 }

/**
 * @typedef {{ n: number, name?: string, x: number, y: number }} CornerInput A corner may have no name: it then shows its number only.
 * @typedef {{ id: string | number, from: [number, number], to: [number, number] }} ZoneInput
 *   A stretch of the lap between two [corner number, metres] references; corner 0 is the start line.
 *   A zone may run through the start line.
 * @typedef {object} TrackData
 * @property {string} name
 * @property {string | number[][]} points Centre line in metres (x east, y north), start line first: "x,y x,y …" or [[x, y], …].
 * @property {CornerInput[]} [corners]
 * @property {ZoneInput[]} [zones]
 * @property {{ x: number, y: number }[]} [sectorLines] Where the intermediate timing lines cross the track, metres; the start line closes the last sector.
 * @typedef {{ width: number, height: number, padding: number }} View
 * @typedef {{ yaw: number, pitch: number, distance: number, focal: number }} Pose Angles in radians.
 */

function clamp(value, low, high) {
  return value < low ? low : value > high ? high : value
}

function lerp(a, b, k) {
  return a + (b - a) * k
}

function round1(value) {
  return Math.round(value * 10) / 10
}

function fmt(x, y) {
  return `${round1(clamp(x, -COORD_LIMIT, COORD_LIMIT))} ${round1(clamp(y, -COORD_LIMIT, COORD_LIMIT))}`
}

function parsePoints(points) {
  const list = typeof points === 'string'
    ? points.trim().split(/\s+/).map((pair) => pair.split(',').map(Number))
    : points.map((point) => [Number(point[0]), Number(point[1])])
  if (list.length < 4 || list.some((point) => point.length < 2 || !Number.isFinite(point[0]) || !Number.isFinite(point[1]))) {
    throw new Error('Track points must be at least four finite [x, y] pairs in metres')
  }
  const first = list[0]
  const last = list[list.length - 1]
  return Math.hypot(last[0] - first[0], last[1] - first[1]) < CLOSING_OVERLAP ? list.slice(0, -1) : list
}

function densifyClosed(points, step) {
  return points.flatMap((from, index) => {
    const to = points[(index + 1) % points.length]
    const pieces = Math.max(1, Math.ceil(Math.hypot(to[0] - from[0], to[1] - from[1]) / step))
    return Array.from({ length: pieces }, (_, j) => [lerp(from[0], to[0], j / pieces), lerp(from[1], to[1], j / pieces)])
  })
}

function smoothClosed(points, passes) {
  let current = points
  for (let pass = 0; pass < passes; pass += 1) {
    const source = current
    const count = source.length
    current = source.map((point, index) => {
      const before = source[(index + count - 1) % count]
      const after = source[(index + 1) % count]
      return [(before[0] + 2 * point[0] + after[0]) / 4, (before[1] + 2 * point[1] + after[1]) / 4]
    })
  }
  return current
}

function resampleClosed(points, step) {
  const count = points.length
  const lengths = [0]
  for (let i = 0; i < count; i += 1) {
    const next = points[(i + 1) % count]
    lengths.push(lengths[i] + Math.hypot(next[0] - points[i][0], next[1] - points[i][1]))
  }
  const total = lengths[count]
  const samples = Math.round(total / step)
  const spacing = total / samples
  const result = []
  let cursor = 0
  for (let s = 0; s < samples; s += 1) {
    const target = s * spacing
    while (lengths[cursor + 1] < target) cursor += 1
    const k = (target - lengths[cursor]) / (lengths[cursor + 1] - lengths[cursor] || 1)
    const from = points[cursor]
    const to = points[(cursor + 1) % count]
    result.push([lerp(from[0], to[0], k), lerp(from[1], to[1], k)])
  }
  return { points: result, step: spacing, length: total }
}

function nearestIndex(xs, ys, x, y) {
  let best = 0
  let bestDistance = Infinity
  for (let i = 0; i < xs.length; i += 1) {
    const distance = Math.hypot(xs[i] - x, ys[i] - y)
    if (distance < bestDistance) {
      bestDistance = distance
      best = i
    }
  }
  return best
}

/**
 * Prepares a track for drawing: an evenly sampled closed curve with tangents,
 * corners placed along the lap and zones turned into distances.
 * @param {TrackData} data
 */
export function buildTrack(data) {
  const shaped = resampleClosed(smoothClosed(densifyClosed(parsePoints(data.points), DENSIFY_STEP), SMOOTH_PASSES), SAMPLE_STEP)
  const n = shaped.points.length
  const px = Float64Array.from(shaped.points, (point) => point[0])
  const py = Float64Array.from(shaped.points, (point) => point[1])
  const tx = new Float64Array(n)
  const ty = new Float64Array(n)
  for (let i = 0; i < n; i += 1) {
    const dx = px[(i + 1) % n] - px[(i + n - 1) % n]
    const dy = py[(i + 1) % n] - py[(i + n - 1) % n]
    const size = Math.hypot(dx, dy) || 1
    tx[i] = dx / size
    ty[i] = dy / size
  }
  const corners = (data.corners ?? []).map((corner) => {
    const index = nearestIndex(px, py, corner.x, corner.y)
    return { n: corner.n, name: corner.name, x: px[index], y: py[index], s: index * shaped.step }
  })
  const lapAt = [0, ...corners.map((corner) => corner.s)]
  const along = ([cornerNumber, metres]) => {
    if (lapAt[cornerNumber] === undefined) throw new Error(`Zone refers to corner ${cornerNumber}, which the track does not have`)
    return lapAt[cornerNumber] + metres
  }
  // A zone that ends earlier in the lap than it begins runs through the start line.
  const zoneAlong = (zone) => {
    const from = along(zone.from)
    const to = along(zone.to)
    return { id: zone.id, from, to: to < from ? to + shaped.length : to }
  }
  // Timing sectors: from the start line to each intermediate line in turn, the last one back to the start line.
  const sectorEnds = (data.sectorLines ?? []).map((line) => nearestIndex(px, py, line.x, line.y) * shaped.step).sort((a, b) => a - b)
  const sectorBounds = sectorEnds.length ? [0, ...sectorEnds, shaped.length] : []
  const box = { x0: Math.min(...px), x1: Math.max(...px), y0: Math.min(...py), y1: Math.max(...py) }
  const centre = { x: (box.x0 + box.x1) / 2, y: (box.y0 + box.y1) / 2 }
  // A sector's mark hangs on the point where it runs furthest from the middle of the track: there the mark
  // stands outside the layout, whichever way it is turned, instead of among the corners inside it.
  const pinOf = (from, to) => {
    const margin = (to - from) * SECTOR_PIN_MARGIN
    let best = (from + to) / 2
    let bestDistance = -1
    for (let i = Math.ceil((from + margin) / shaped.step); i * shaped.step <= to - margin; i += 1) {
      const distance = Math.hypot(px[i % n] - centre.x, py[i % n] - centre.y)
      if (distance > bestDistance) {
        bestDistance = distance
        best = i * shaped.step
      }
    }
    return best
  }
  return {
    name: data.name,
    n,
    step: shaped.step,
    length: shaped.length,
    px,
    py,
    tx,
    ty,
    corners,
    zones: (data.zones ?? []).map((zone) => zoneAlong(zone)),
    sectors: sectorBounds.slice(0, -1).map((from, index) => ({ n: index + 1, from, to: sectorBounds[index + 1], pin: pinOf(from, sectorBounds[index + 1]) })),
    box,
    centre,
    radius: Math.hypot(box.x1 - box.x0, box.y1 - box.y0) / 2
  }
}

/** Point and unit tangent at distance `s` along the lap (wraps). */
function pointAt(track, s) {
  const wrapped = ((s % track.length) + track.length) % track.length
  const position = wrapped / track.step
  const index = Math.floor(position) % track.n
  const next = (index + 1) % track.n
  const k = position - Math.floor(position)
  const tx = lerp(track.tx[index], track.tx[next], k)
  const ty = lerp(track.ty[index], track.ty[next], k)
  const size = Math.hypot(tx, ty) || 1
  return { x: lerp(track.px[index], track.px[next], k), y: lerp(track.py[index], track.py[next], k), tx: tx / size, ty: ty / size }
}

/**
 * Pinhole camera looking at a ground point.
 * yaw: compass of the view direction (from +x towards +y); pitch: angle below the horizon;
 * anchor: where the target lands on screen.
 */
function makeCamera({ target, yaw, pitch, distance, focal, anchor }) {
  const cp = Math.cos(pitch)
  const sp = Math.sin(pitch)
  const cy = Math.cos(yaw)
  const sy = Math.sin(yaw)
  const fx = cp * cy
  const fy = cp * sy
  const fz = -sp
  const rx = sy
  const ry = -cy
  return {
    cx: target.x - distance * fx, cy: target.y - distance * fy, cz: -distance * fz,
    fx, fy, fz, rx, ry,
    ux: ry * fz, uy: -rx * fz, uz: rx * fy - ry * fx,
    f: focal, ax: anchor.x, ay: anchor.y
  }
}

function depthOf(camera, x, y) {
  return (x - camera.cx) * camera.fx + (y - camera.cy) * camera.fy - camera.cz * camera.fz
}

/** Ground point → [screen x, screen y, depth in metres], or null when behind the near plane. */
function project(camera, x, y) {
  const vx = x - camera.cx
  const vy = y - camera.cy
  const depth = vx * camera.fx + vy * camera.fy - camera.cz * camera.fz
  if (depth < NEAR_PLANE) return null
  const scale = camera.f / depth
  return [camera.ax + (vx * camera.rx + vy * camera.ry) * scale, camera.ay - (vx * camera.ux + vy * camera.uy - camera.cz * camera.uz) * scale, depth]
}

/** A band of the given half-width along the track between two distances, as a filled path in perspective. */
function ribbonPath(track, camera, from, to, halfWidth) {
  if (to - from < 0.05) return ''
  const parts = []
  let left = []
  let right = []
  const flush = () => {
    if (left.length > 1) parts.push(`M${left.join('L')}L${right.slice().reverse().join('L')}Z`)
    left = []
    right = []
  }
  const push = (x, y, tx, ty) => {
    const a = project(camera, x - ty * halfWidth, y + tx * halfWidth)
    const b = project(camera, x + ty * halfWidth, y - tx * halfWidth)
    if (!a || !b) return flush()
    left.push(fmt(a[0], a[1]))
    right.push(fmt(b[0], b[1]))
    return undefined
  }
  const first = pointAt(track, from)
  push(first.x, first.y, first.tx, first.ty)
  for (let i = Math.floor(from / track.step) + 1; i * track.step < to; i += 1) {
    const j = ((i % track.n) + track.n) % track.n
    push(track.px[j], track.py[j], track.tx[j], track.ty[j])
  }
  const last = pointAt(track, to)
  push(last.x, last.y, last.tx, last.ty)
  flush()
  return parts.join('')
}

function dashPath(track, camera, to, halfWidth) {
  const period = ROAD.dashLength + ROAD.dashGap
  const parts = []
  for (let s = 0; s + ROAD.dashLength <= to; s += period) parts.push(ribbonPath(track, camera, s, s + ROAD.dashLength, halfWidth))
  return parts.join('')
}

/** Straight ground segment clipped to the near plane. */
function groundSegment(camera, x1, y1, x2, y2) {
  const d1 = depthOf(camera, x1, y1)
  const d2 = depthOf(camera, x2, y2)
  if (d1 < NEAR_PLANE && d2 < NEAR_PLANE) return ''
  const k1 = d1 < NEAR_PLANE ? (NEAR_PLANE + 0.5 - d1) / (d2 - d1) : 0
  const k2 = d2 < NEAR_PLANE ? (NEAR_PLANE + 0.5 - d2) / (d1 - d2) : 0
  const a = project(camera, lerp(x1, x2, k1), lerp(y1, y2, k1))
  const b = project(camera, lerp(x2, x1, k2), lerp(y2, y1, k2))
  return a && b ? `M${fmt(a[0], a[1])}L${fmt(b[0], b[1])}` : ''
}

function gridPath(track, camera) {
  const snap = (value) => Math.round(value / GRID_STEP) * GRID_STEP
  const box = {
    x0: snap(track.box.x0 - GRID_MARGIN), x1: snap(track.box.x1 + GRID_MARGIN),
    y0: snap(track.box.y0 - GRID_MARGIN), y1: snap(track.box.y1 + GRID_MARGIN)
  }
  const parts = []
  for (let x = box.x0; x <= box.x1; x += GRID_STEP) parts.push(groundSegment(camera, x, box.y0, x, box.y1))
  for (let y = box.y0; y <= box.y1; y += GRID_STEP) parts.push(groundSegment(camera, box.x0, y, box.x1, y))
  return parts.join('')
}

/** Screen box of the track for a camera; null when part of it is behind the camera. */
function screenBounds(track, camera) {
  const bounds = { x0: Infinity, x1: -Infinity, y0: Infinity, y1: -Infinity }
  for (let i = 0; i < track.n; i += FIT_SAMPLE_EVERY) {
    const p = project(camera, track.px[i], track.py[i])
    if (!p) return null
    bounds.x0 = Math.min(bounds.x0, p[0])
    bounds.x1 = Math.max(bounds.x1, p[0])
    bounds.y0 = Math.min(bounds.y0, p[1])
    bounds.y1 = Math.max(bounds.y1, p[1])
  }
  return bounds
}

function cameraFor(track, view, pose, anchor) {
  return makeCamera({ target: track.centre, yaw: pose.yaw, pitch: pose.pitch, distance: pose.distance, focal: pose.focal, anchor })
}

function fitsView(track, view, pose) {
  const bounds = screenBounds(track, cameraFor(track, view, pose, { x: view.width / 2, y: view.height / 2 }))
  return Boolean(bounds) && bounds.x1 - bounds.x0 <= view.width - view.padding * 2 && bounds.y1 - bounds.y0 <= view.height - view.padding * 2
}

function fitDistanceAt(track, view, yaw, pitch, focal) {
  let low = track.radius * 0.3
  let high = track.radius * 60
  for (let i = 0; i < FIT_STEPS; i += 1) {
    const middle = (low + high) / 2
    if (fitsView(track, view, { yaw, pitch, distance: middle, focal })) high = middle
    else low = middle
  }
  return high
}

/**
 * Camera distances at which the track fills the view, one per FIT_YAW_STEP of turn.
 * A long track needs the camera further back when it stands across the view than along it,
 * so the camera eases in and out as the layout turns; the table is softened to keep that even.
 * @param {ReturnType<typeof buildTrack>} track
 * @param {View} view
 * @param {number} pitch radians
 * @param {number} focal px
 * @returns {number[]}
 */
export function fitTable(track, view, pitch, focal) {
  const exact = []
  for (let yaw = 0; yaw < 360; yaw += FIT_YAW_STEP) exact.push(fitDistanceAt(track, view, yaw * DEG, pitch, focal))
  const count = exact.length
  return exact.map((distance, index) => ((exact[(index + count - 1) % count] + 2 * distance + exact[(index + 1) % count]) / 4) * FIT_SLACK)
}

/** Camera distance for a yaw (radians), read from a fit table. */
export function distanceAt(table, yaw) {
  const turn = (((yaw / DEG) % 360) + 360) % 360
  const position = turn / FIT_YAW_STEP
  const index = Math.floor(position) % table.length
  const k = position - Math.floor(position)
  const eased = k * k * (3 - 2 * k)
  return lerp(table[index], table[(index + 1) % table.length], eased)
}

/** A ground point on screen with its mark `offset` px further out from the middle of the track; null behind the camera. */
function markAt(camera, bounds, x, y, offset) {
  const p = project(camera, x, y)
  if (!p) return null
  const dx = p[0] - (bounds.x0 + bounds.x1) / 2
  const dy = p[1] - (bounds.y0 + bounds.y1) / 2
  const size = Math.hypot(dx, dy) || 1
  return {
    x: round1(p[0]),
    y: round1(p[1]),
    markX: round1(p[0] + (dx / size) * offset),
    markY: round1(p[1] + (dy / size) * offset),
    depth: p[2]
  }
}

function cornerMarks(track, camera, bounds) {
  return track.corners.flatMap((corner) => {
    const mark = markAt(camera, bounds, corner.x, corner.y, BADGE_OFFSET)
    return mark ? [{ n: corner.n, name: corner.name, ...mark }] : []
  })
}

/**
 * Each timing sector as its own stretch of road (drawn as far as the lap is), the line across the
 * track where it ends and, once the lap is complete, a mark at its pin for whoever holds it.
 */
function sectorShapes(track, camera, bounds, drawn, half) {
  const complete = drawn >= track.length
  return track.sectors.map((sector) => {
    const to = Math.min(sector.to, drawn)
    const shown = to > sector.from
    const pin = pointAt(track, sector.pin)
    const reach = half * ROAD.sectorLine
    return {
      n: sector.n,
      road: shown ? ribbonPath(track, camera, sector.from, to, half) : '',
      glow: shown ? ribbonPath(track, camera, sector.from, to, half * ROAD.glow) : '',
      line: complete && sector.to < track.length ? ribbonPath(track, camera, sector.to - reach, sector.to + reach, half * ROAD.sectorLineReach) : '',
      mark: complete ? markAt(camera, bounds, pin.x, pin.y, SECTOR_OFFSET) : null
    }
  })
}

/**
 * Moves corner marks apart until none is closer to another than `minDistance` (view px),
 * so the numbers stay readable where corners bunch up or the layout is shown small.
 * Marks keep leaning towards their own corners; nothing is hidden.
 * @param {ReturnType<typeof cornerMarks>} marks
 * @param {number} minDistance
 */
export function declutter(marks, minDistance) {
  let placed = marks.map((mark) => ({ x: mark.markX, y: mark.markY }))
  for (let pass = 0; pass < DECLUTTER_PASSES; pass += 1) {
    const before = placed
    placed = before.map((own, index) => {
      let pushX = 0
      let pushY = 0
      before.forEach((other, otherIndex) => {
        if (otherIndex === index) return
        // Marks that sit exactly on one another are split along a direction fixed by their order.
        const dx = own.x - other.x || (index < otherIndex ? -0.5 : 0.5)
        const dy = own.y - other.y
        const distance = Math.hypot(dx, dy)
        if (distance >= minDistance) return
        const shove = (minDistance - distance) / 2 / distance
        pushX += dx * shove
        pushY += dy * shove
      })
      return { x: own.x + pushX, y: own.y + pushY }
    })
  }
  return marks.map((mark, index) => ({ ...mark, markX: round1(placed[index].x), markY: round1(placed[index].y) }))
}

function lightState(track, camera, at, halfWidth) {
  if (at === null || at === undefined) return { tail: '', head: null }
  const point = pointAt(track, at)
  const p = project(camera, point.x, point.y)
  return {
    tail: ribbonPath(track, camera, at - LIGHT_TAIL, at, halfWidth * 0.28),
    head: p ? { x: round1(p[0]), y: round1(p[1]) } : null
  }
}

/**
 * Everything to draw for one pose: SVG path strings and the corner marks, in the view's own px.
 * @param {ReturnType<typeof buildTrack>} track
 * @param {View} view
 * @param {Pose} pose
 * @param {{ progress?: number, lightAt?: number | null, roadWidth?: number, grid?: boolean, zones?: boolean, sectors?: boolean, startMark?: boolean }} [options]
 *   progress: how much of the lap is drawn, 0…1; lightAt: metres along the lap of the running light; roadWidth: metres, drawn wider than life so it reads;
 *   sectors: also return the timing sectors as separate shapes (off by default: a plain layout does not pay for them);
 *   startMark: also return a mark by the start line (for whoever holds the lap record), once the lap is drawn.
 */
export function sceneAt(track, view, pose, options = {}) {
  const { progress = 1, lightAt = null, roadWidth = 26, grid = true, zones = true, sectors = false, startMark = false } = options
  const centre = { x: view.width / 2, y: view.height / 2 }
  const rough = screenBounds(track, cameraFor(track, view, pose, centre))
  // Perspective pulls the picture off-centre; move the anchor so the track sits in the middle of the view.
  const anchor = rough ? { x: centre.x * 2 - (rough.x0 + rough.x1) / 2, y: centre.y * 2 - (rough.y0 + rough.y1) / 2 } : centre
  const camera = cameraFor(track, view, pose, anchor)
  const bounds = screenBounds(track, camera) ?? { x0: 0, x1: view.width, y0: 0, y1: view.height }
  const half = roadWidth / 2
  const drawn = track.length * clamp(progress, 0, 1)
  const band = (factor) => ribbonPath(track, camera, 0, drawn, half * factor)
  const light = lightState(track, camera, drawn >= track.length ? lightAt : null, half)
  return {
    grid: grid ? gridPath(track, camera) : '',
    glow: band(ROAD.glow),
    edge: band(ROAD.edge),
    road: band(1),
    dashes: dashPath(track, camera, drawn, half * ROAD.dash),
    start: drawn > 0 ? ribbonPath(track, camera, -half * ROAD.startLine, half * ROAD.startLine, half) : '',
    zones: zones && drawn >= track.length ? track.zones.map((zone) => ribbonPath(track, camera, zone.from, zone.to, half * ROAD.zone)).join('') : '',
    lightTail: light.tail,
    light: light.head,
    corners: drawn >= track.length ? cornerMarks(track, camera, bounds) : [],
    sectors: sectors ? sectorShapes(track, camera, bounds, drawn, half) : [],
    startMark: startMark && drawn >= track.length ? markAt(camera, bounds, track.px[0], track.py[0], SECTOR_OFFSET) : null
  }
}
