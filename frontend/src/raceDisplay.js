import { state } from './store'

export const WEATHER_KEYS = ['clear', 'partly_cloudy', 'overcast', 'light_rain', 'heavy_rain', 'storm']

/** @param {object} race */
export function registeredCount(race) {
  if (race?.game === 'LMU') return 0
  if (race?.is_team_event) return race.team_registrations?.length || 0
  return race?.registered_pilots?.length || 0
}

/** @param {object} race */
export function isRaceRegistered(race) {
  if (!race || race.game === 'LMU') return false
  if (race.is_team_event) {
    return Boolean(state.user?.team_id && race.team_registrations?.some((item) => item.team_id === state.user.team_id))
  }
  return Boolean(state.user && race.registered_pilots?.some((item) => item.user_id === state.user.id))
}

/** @param {object} race @returns {number} 0–100 */
export function fillPercent(race) {
  if (!race || race.game === 'LMU' || !race.max_pilots) return 0
  return Math.min(100, Math.round((registeredCount(race) / race.max_pilots) * 100))
}

/** @param {object} race */
export function dominantWeatherKey(race) {
  const chances = race?.weather_chances || {}
  return WEATHER_KEYS.reduce((best, key) => (Number(chances[key] || 0) > Number(chances[best] || 0) ? key : best), WEATHER_KEYS[0])
}

/**
 * @param {object} race
 * @param {Record<string, string>} weatherSettings
 */
export function weatherImageUrl(race, weatherSettings) {
  const theme = state.theme === 'dark' ? 'dark' : 'light'
  const condition = dominantWeatherKey(race)
  return weatherSettings?.[`${condition}_${theme}_url`]
    || weatherSettings?.[`${condition}_${theme === 'dark' ? 'light' : 'dark'}_url`]
    || ''
}

/** i18n key for a weather condition. @param {string} key */
export function weatherLabelKey(key) {
  return `weather.${key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())}`
}

/** Race status → tone used by chips and status dots. */
export function raceStatusTone(status) {
  return { registration_open: 'green', ongoing: 'red', not_started: 'blue', finished: '' }[status] ?? ''
}

let raceAssetsPromise = null

/** Loads /race-assets once per session and shares the result. */
export function loadRaceAssets() {
  if (!raceAssetsPromise) {
    // Imported lazily so the pure helpers above stay usable without the API client.
    raceAssetsPromise = import('./api').then(({ api }) => api('/race-assets')).catch((error) => {
      raceAssetsPromise = null
      throw error
    })
  }
  return raceAssetsPromise
}

/** Replaces the shared copy after staff change the assets, so every page shows the update. */
export function updateRaceAssetsCache(config) {
  raceAssetsPromise = config ? Promise.resolve(config) : null
}

/**
 * Finds the admin-uploaded artwork for a race's track.
 * @param {object | null} assets result of /race-assets
 * @param {{ game?: string, track?: string }} race
 */
export function trackImageFor(assets, race) {
  if (!assets || !race?.track) return ''
  const gameAssets = assets.games?.[race.game] || (race.game === 'ACC' || !race.game ? assets : null)
  const images = gameAssets?.track_images || {}
  const name = String(race.track).trim().toLowerCase()
  const match = Object.entries(images).find(([track]) => track.toLowerCase() === name)
  return match?.[1] || ''
}
