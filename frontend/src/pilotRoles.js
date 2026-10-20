// Pilot roles as the API hands them over. They should be a list, but some
// stored race results carry a single role object in a row, and a pilot who
// hides their roles arrives with none; everything that shows roles reads them
// through here.

/**
 * A pilot's roles as a list of role objects.
 * @param {unknown} value  `pilot_roles` of a pilot or of a result row
 * @returns {Array<{ id?: number, name: string }>}
 */
export function roleList(value) {
  if (Array.isArray(value)) return value.filter(Boolean)
  return value && typeof value === 'object' && typeof value.name === 'string' ? [value] : []
}
