// Which columns the results table shows. At a glance it keeps to what fits
// beside the race's side panels without a sideways scroll; "all information"
// gives the table the whole width of the page and every column it has.

/**
 * @typedef {'pos' | 'pilot' | 'car' | 'laps' | 'bestLap' | 'qualiLap' | 'finish' | 'timePenalty' | 'srPenalty' | 'adjusted' | 'delta' | 'gap'} ResultColumn
 */

/** Every column in the order it stands, and whether it is there at a glance. */
const COLUMNS = {
  race: [
    ['pos', true],
    ['pilot', true],
    ['car', false],
    ['laps', false],
    ['bestLap', true],
    ['qualiLap', false],
    ['finish', false],
    ['timePenalty', false],
    ['srPenalty', false],
    ['adjusted', true],
    ['delta', true],
    ['gap', true]
  ],
  qualification: [
    ['pos', true],
    ['pilot', true],
    ['car', false],
    ['bestLap', true],
    ['gap', true]
  ]
}

function columnsOf(mode) {
  return COLUMNS[mode] || COLUMNS.race
}

/**
 * The columns to show, in order.
 * @param {'race' | 'qualification'} mode
 * @param {{ detailed?: boolean, hasQuali?: boolean }} [options]
 *   detailed: the whole table; hasQuali: somebody in the race has a qualifying lap.
 * @returns {ResultColumn[]}
 */
export function resultColumns(mode, { detailed = false, hasQuali = false } = {}) {
  return columnsOf(mode)
    .filter(([key, glance]) => (glance || detailed) && (key !== 'qualiLap' || hasQuali))
    .map(([key]) => key)
}

/**
 * A column that only the whole table has: it comes in with the table's unfolding.
 * @param {'race' | 'qualification'} mode
 * @param {ResultColumn} column
 * @returns {boolean}
 */
export function isExtraColumn(mode, column) {
  return columnsOf(mode).some(([key, glance]) => key === column && !glance)
}
