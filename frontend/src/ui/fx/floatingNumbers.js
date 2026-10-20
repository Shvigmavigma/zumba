// Pure helpers for FloatingNumbers: where the numbers sit and how a number
// flips to the next one digit by digit, like a timing board.

/**
 * Spreads `count` points over the box without clumping: the box is cut into a
 * grid, random cells are taken and each point lands somewhere inside its cell.
 * @param {number} count
 * @param {{ cols?: number, rows?: number, random?: () => number }} [options]
 * @returns {{ x: number, y: number }[]} positions in percent of the box
 */
export function scatter(count, { cols = 4, rows = 5, random = Math.random } = {}) {
  const cells = Array.from({ length: cols * rows }, (_, index) => index)
  const shuffled = cells
    .map((cell) => ({ cell, key: random() }))
    .sort((a, b) => a.key - b.key)
    .map((item) => item.cell)
  return shuffled.slice(0, Math.min(count, cells.length)).map((cell) => {
    const col = cell % cols
    const row = Math.floor(cell / cols)
    // Keep a margin inside the cell so neighbours never touch.
    return {
      x: ((col + 0.15 + random() * 0.7) / cols) * 100,
      y: ((row + 0.15 + random() * 0.7) / rows) * 100
    }
  })
}

/**
 * A pilot number as it appears on a car: three digits, 000–999.
 * @param {() => number} [random]
 * @returns {string}
 */
export function randomPlate(random = Math.random) {
  return String(Math.floor(random() * 1000)).padStart(3, '0')
}

/**
 * One frame of a flip towards `target`: digits lock in from left to right as
 * `progress` goes from 0 to 1, the rest keep cycling. Other characters stay.
 * @param {string} target
 * @param {number} progress 0–1
 * @param {() => number} [random]
 * @returns {string}
 */
export function scrambleFrame(target, progress, random = Math.random) {
  const digits = [...target].filter((char) => /\d/.test(char)).length
  const locked = Math.floor(Math.min(Math.max(progress, 0), 1) * digits)
  let seen = 0
  return [...target].map((char) => {
    if (!/\d/.test(char)) return char
    seen += 1
    return seen <= locked ? char : String(Math.floor(random() * 10))
  }).join('')
}
