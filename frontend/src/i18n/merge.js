/**
 * Deep-merges locale message trees without mutating the inputs.
 * @param {Record<string, any>} base
 * @param {...Record<string, any>} extras
 * @returns {Record<string, any>}
 */
export function mergeMessages(base, ...extras) {
  return extras.reduce((acc, extra) => mergeTree(acc, extra), base)
}

function mergeTree(left, right) {
  const result = { ...left }
  for (const [key, value] of Object.entries(right || {})) {
    const current = result[key]
    result[key] = isPlainObject(current) && isPlainObject(value) ? mergeTree(current, value) : value
  }
  return result
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}
