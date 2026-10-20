/**
 * Fuel amount without the unit, as the calculator has always shown it:
 * whole numbers from 100 up, one decimal below.
 * @param {number} value
 * @returns {string}
 */
export function fuelFixed(value) {
  if (!Number.isFinite(value)) return '0'
  return value >= 100 ? value.toFixed(0) : value.toFixed(1)
}
