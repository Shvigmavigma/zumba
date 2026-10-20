// Which tracks of the site have a 3D layout (TrackLayout3D), and how to get
// its data. A layout is one configuration of a circuit: another configuration
// of the same place (National, Historic…) is another track and is not matched.
// The data of a layout is loaded only when it is asked for, so pages without
// one do not carry it.

/**
 * @typedef {object} TrackLayoutEntry
 * @property {string} id  The site's track id for this layout.
 * @property {string[]} names  Normalised names the simulators give it.
 * @property {() => Promise<object>} load  Resolves to the data TrackLayout3D takes.
 */

/** @type {TrackLayoutEntry[]} */
const LAYOUTS = [
  {
    id: 'silverstone',
    names: ['silverstone', 'silverstone circuit', 'silverstone gp', 'silverstone grand prix', 'silverstone grand prix circuit'],
    load: () => import('./tracks/silverstone.js').then((module) => module.default)
  },
  {
    id: 'red-bull-ring',
    names: [
      'red bull ring', 'redbull ring', 'red bull ring gp', 'red bull ring gp lfm', 'red bull ring grand prix', 'red bull ring grand prix circuit',
      'red bull ring gt2 pack', 'ks red bull ring', 'spielberg'
    ],
    load: () => import('./tracks/red-bull-ring.js').then((module) => module.default)
  }
]

/**
 * A track name reduced to what identifies it: lower case, no accents, any
 * punctuation as a single space.
 * @param {string | null | undefined} name
 * @returns {string}
 */
export function normalizeTrackName(name) {
  return String(name ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim()
}

/**
 * The 3D layout of a track of the site, or null when none is drawn for it.
 * The site's own track id is tried first: it survives a renamed track.
 * @param {{ track?: string | null, trackId?: string | number | null } | null | undefined} query
 * @returns {TrackLayoutEntry | null}
 */
export function findTrackLayout(query) {
  const id = normalizeTrackName(query?.trackId)
  const name = normalizeTrackName(query?.track)
  if (!id && !name) return null
  return LAYOUTS.find((layout) => (id && normalizeTrackName(layout.id) === id) || (name && layout.names.includes(name)))
    || (id ? LAYOUTS.find((layout) => layout.names.includes(id)) : null)
    || null
}
