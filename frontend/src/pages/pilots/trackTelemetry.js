// A decorative speed trace for a track's header: fast straights, hard braking
// into each corner, a slower climb out of it. It is drawn from the track's
// name, not from data, so every track keeps a trace of its own between visits.
import { seededRandom } from '../../ui/rank/sparks.js'

const MIN_CORNERS = 5
const EXTRA_CORNERS = 5
// The trace keeps clear of the box's top and bottom edges.
const EDGE = 0.07

/**
 * A stable number for a track name (FNV-1a); case and outer spaces are ignored.
 * @param {string | null | undefined} name
 * @returns {number}
 */
export function trackSeed(name) {
  const text = String(name ?? '').trim().toLowerCase()
  let hash = 2166136261
  for (let index = 0; index < text.length; index += 1) {
    hash = Math.imul(hash ^ text.charCodeAt(index), 16777619)
  }
  return hash >>> 0
}

function round(value) {
  return Math.round(value * 10) / 10
}

/**
 * The trace of one lap inside a width x height box.
 * @param {string | null | undefined} name
 * @param {{ width?: number, height?: number }} [box]
 * @returns {{ points: number[][], line: string, area: string, sectors: number[] }}
 *   `line` is the smoothed trace, `area` the same closed down to the box's
 *   bottom edge, `sectors` the x of the two sector borders.
 */
export function speedTrace(name, { width = 1000, height = 200 } = {}) {
  const random = seededRandom(trackSeed(name))
  const between = (from, to) => from + random() * (to - from)
  const y = (speed) => round((EDGE + (1 - speed) * (1 - 2 * EDGE)) * height)

  const corners = MIN_CORNERS + Math.floor(random() * EXTRA_CORNERS)
  const step = width / (corners + 1)
  const points = [[0, y(between(0.62, 0.82))]]
  for (let corner = 1; corner <= corners; corner += 1) {
    const apex = step * corner + between(-0.25, 0.25) * step
    // Top speed just before the braking point, then the dip to the apex.
    points.push([round(apex - between(0.07, 0.13) * step), y(between(0.72, 1))])
    points.push([round(apex), y(between(0.12, 0.5))])
  }
  points.push([width, y(between(0.7, 0.95))])

  // Curves through the midpoints: every stored point bends the line, none is a kink.
  const curves = points.slice(1, -1).map((point, index) => {
    const next = points[index + 2]
    return `Q${point[0]} ${point[1]} ${round((point[0] + next[0]) / 2)} ${round((point[1] + next[1]) / 2)}`
  })
  const last = points[points.length - 1]
  const line = [`M0 ${points[0][1]}`, ...curves, `L${last[0]} ${last[1]}`].join(' ')

  return {
    points,
    line,
    area: `${line} L${width} ${height} L0 ${height} Z`,
    sectors: [Math.round(width * between(0.3, 0.38)), Math.round(width * between(0.62, 0.7))]
  }
}
