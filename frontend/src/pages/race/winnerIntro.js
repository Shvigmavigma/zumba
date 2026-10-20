// The winner's graphic that opens a finished race, the way the broadcasts show
// it: a wall of one word in big display type, rows sliding past each other.
// Timings and the layout of the wall; the component is WinnerIntro.vue.

/** The word the wall opens with. A broadcast graphic, so it is not translated. */
export const WINNER_WORD = 'Winner'

/**
 * When each part plays, in ms from the moment the race opens: the WINNER wall,
 * the wall turning into the winner's first name, the wall clearing, and the
 * header coming in (with the surname driving in at the bottom).
 */
export const INTRO_TIMING = Object.freeze({
  // The blue screen goes black from the middle out, block by block.
  pixelsAt: 150,
  pixelsMs: 850,
  nameAt: 1000,
  clearAt: 2050,
  clearMs: 450,
  revealAt: 2100
})

/** Size of one block of the blue-to-black change, in CSS pixels. */
export const PIXEL_BLOCK = 22

// How ragged the edge of the black is: the share of a block's turn decided by chance.
const PIXEL_JITTER = 0.22

/**
 * When each block of the screen turns black, from 0 (first) to 1 (last):
 * by its distance from the middle, roughened so the edge reads as pixels,
 * not as a circle. The same blocks turn in the same order on every visit.
 * Blocks run row by row, left to right.
 * @param {number} cols
 * @param {number} rows
 * @returns {Float32Array}
 */
export function pixelOrder(cols, rows) {
  const order = new Float32Array(Math.max(0, cols * rows))
  const cx = (cols - 1) / 2
  const cy = (rows - 1) / 2
  const far = Math.hypot(cx, cy) || 1
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      const index = row * cols + col
      const near = Math.hypot(col - cx, row - cy) / far
      order[index] = near * (1 - PIXEL_JITTER) + noise(index) * PIXEL_JITTER
    }
  }
  return order
}

// A fixed number in [0, 1) for every block (an integer hash, not Math.random).
function noise(index) {
  let x = Math.imul(index + 1, 0x9e3779b1)
  x ^= x >>> 15
  x = Math.imul(x, 0x85ebca6b)
  x ^= x >>> 13
  return (x >>> 0) / 4294967296
}

/** When the intro is over and its layer can go. */
export const INTRO_END_MS = INTRO_TIMING.clearAt + INTRO_TIMING.clearMs

// How the words look along the wall, like the LED screens: mostly lines,
// some lit solid, some dimmed. The middle word of the middle row is the
// accent: lit solid, its first letter in gold.
const LOOKS = ['lines', 'ghost', 'solid', 'lines', 'ghost', 'lines', 'solid']

/**
 * The rows of the wall. Neighbouring rows slide in opposite directions, the
 * middle row barely moves; `far` is how many rows a row is from the middle,
 * for rows that light up from the middle outwards.
 * @param {{ rows?: number, perRow?: number }} [options]
 * @returns {{ id: number, dir: number, far: number, words: { id: number, look: string }[] }[]}
 */
export function wallRows({ rows = 9, perRow = 5 } = {}) {
  const middle = Math.floor(rows / 2)
  const centre = Math.floor(perRow / 2)
  return Array.from({ length: rows }, (_, row) => ({
    id: row,
    dir: row === middle ? 0.25 : (row % 2 ? 1 : -1),
    far: Math.abs(row - middle),
    words: Array.from({ length: perRow }, (_, column) => ({
      id: column,
      look: row === middle && column === centre ? 'accent' : LOOKS[(row * 3 + column * 2) % LOOKS.length]
    }))
  }))
}

/**
 * How much smaller a long word is drawn, so the accent still fits across the
 * header: WINNER and anything up to its length at full size.
 * @param {string} word
 * @returns {number}
 */
export function wallScale(word) {
  const length = Array.from(String(word ?? '').trim()).length
  return length <= 6 ? 1 : Math.max(0.5, 6 / length)
}

/**
 * The word split for the accent: its first letter and the rest. Letters, not
 * UTF-16 halves, so a name never breaks inside a character.
 * @param {string} word
 * @returns {{ first: string, rest: string }}
 */
export function accentParts(word) {
  const [first = '', ...rest] = Array.from(String(word ?? '').trim())
  return { first, rest: rest.join('') }
}
