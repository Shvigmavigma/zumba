// Track artwork from the race-assets config: the image itself and the frame
// staff chose for it (a zoom and a focus point, set on the race page). The
// original file is never cropped; the frame only changes how it is shown.

export const DEFAULT_TRACK_FRAME = Object.freeze({ zoom: 1, x: 50, y: 50 })

const MIN_ZOOM = 1
const MAX_ZOOM = 3

/**
 * One per-track value of a game's assets (`track_images`, `track_image_crops`,
 * …). The track is matched by its id when the config knows it, so a renamed
 * track keeps its artwork, and otherwise by name without regard to case.
 * @param {object | null | undefined} config  assets of one game
 * @param {string} key
 * @param {string | null | undefined} track
 * @param {string | number} [trackId]
 * @returns {any} the value, or null when the track has none
 */
export function trackAsset(config, key, track, trackId = '') {
  const byId = trackId !== '' && trackId !== null && trackId !== undefined
    ? Object.entries(config?.track_ids || {}).find(([, id]) => String(id) === String(trackId))?.[0]
    : ''
  const name = String(byId || track || '').trim().toLowerCase()
  if (!name) return null
  const assets = config?.[key] || {}
  const assetKey = Object.keys(assets).find((item) => item.toLowerCase() === name)
  return assetKey ? assets[assetKey] : null
}

function clamp(value, min, max, fallback) {
  const number = typeof value === 'number' ? value : Number.parseFloat(value)
  return Number.isFinite(number) ? Math.min(max, Math.max(min, number)) : fallback
}

/**
 * The frame saved for a track, always within what the image box can show.
 * @param {object | null | undefined} config
 * @param {string | null | undefined} track
 * @param {string | number} [trackId]
 * @returns {{ zoom: number, x: number, y: number }}
 */
export function trackImageFrame(config, track, trackId = '') {
  const saved = trackAsset(config, 'track_image_crops', track, trackId)
  if (!saved || typeof saved !== 'object') return DEFAULT_TRACK_FRAME
  return {
    zoom: clamp(saved.zoom, MIN_ZOOM, MAX_ZOOM, DEFAULT_TRACK_FRAME.zoom),
    x: clamp(saved.x, 0, 100, DEFAULT_TRACK_FRAME.x),
    y: clamp(saved.y, 0, 100, DEFAULT_TRACK_FRAME.y)
  }
}

/**
 * Inline styles that show an `object-fit: cover` image in the given frame.
 * The default frame needs none, so the image keeps its own styles.
 * @param {{ zoom: number, x: number, y: number } | null | undefined} frame
 * @returns {Record<string, string>}
 */
export function trackImageStyle(frame) {
  if (!frame) return {}
  const { zoom, x, y } = frame
  if (zoom === DEFAULT_TRACK_FRAME.zoom && x === DEFAULT_TRACK_FRAME.x && y === DEFAULT_TRACK_FRAME.y) return {}
  return {
    objectPosition: `${x}% ${y}%`,
    transformOrigin: `${x}% ${y}%`,
    transform: `scale(${zoom})`
  }
}
