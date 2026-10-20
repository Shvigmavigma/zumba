// Browser cache for a team's livery screenshots, so a visitor who already
// asked for them does not download the list again. Purely an optimisation:
// every failure is swallowed and the server stays the source of truth.
import { API_BASE } from '../../api'

const CACHE_NAME = 'bmrl-team-liveries-v1'

function cacheUrl(teamId) {
  return `${API_BASE}/teams/${teamId}/liveries`
}

function storageKey(teamId) {
  return `${CACHE_NAME}:${teamId}`
}

/**
 * The cached screenshots of a team, or null when nothing usable is cached.
 * @param {number | string} teamId
 * @returns {Promise<object[] | null>}
 */
export async function readTeamLiveryCache(teamId) {
  if (typeof window === 'undefined') return null
  if ('caches' in window) {
    try {
      const cache = await window.caches.open(CACHE_NAME)
      const response = await cache.match(cacheUrl(teamId))
      if (response) {
        const cached = await response.json()
        if (Array.isArray(cached?.images)) return cached.images
      }
    } catch {
      // Fall back to local storage below.
    }
  }
  try {
    const cached = JSON.parse(window.localStorage.getItem(storageKey(teamId)) || 'null')
    return Array.isArray(cached?.images) ? cached.images : null
  } catch {
    return null
  }
}

/**
 * Remembers a team's screenshots in both stores that are available.
 * @param {number | string} teamId
 * @param {object[]} images
 * @returns {Promise<void>}
 */
export async function writeTeamLiveryCache(teamId, images) {
  if (typeof window === 'undefined') return
  const cached = JSON.stringify({ images })
  try {
    window.localStorage.setItem(storageKey(teamId), cached)
  } catch {
    // Cache storage below may still be available.
  }
  if (!('caches' in window)) return
  try {
    const cache = await window.caches.open(CACHE_NAME)
    await cache.put(cacheUrl(teamId), new Response(cached, { headers: { 'Content-Type': 'application/json' } }))
  } catch {
    // Cache storage is optional.
  }
}
