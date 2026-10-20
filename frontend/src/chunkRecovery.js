// Pages load on demand. After a deploy the previous build's chunks are gone, so a
// tab opened earlier fails to load the next page and the click does nothing.
// Reloading at the target URL picks up the new build instead.

const RELOAD_KEY = 'bmrl:chunk-reload-at'
const RETRY_WINDOW_MS = 10000
const CHUNK_ERROR = /Failed to fetch dynamically imported module|Importing a module script failed|error loading dynamically imported module|Unable to preload CSS/i

/**
 * @param {unknown} error
 * @returns {boolean}
 */
export function isChunkLoadError(error) {
  const message = error instanceof Error ? error.message : String(error ?? '')
  return CHUNK_ERROR.test(message)
}

/**
 * Whether a reload may happen now. A second failure within the retry window
 * (offline, broken deploy) is left alone instead of reloading in a loop.
 * @param {number | null} lastReloadAt
 * @param {number} now
 * @returns {boolean}
 */
export function canReloadAgain(lastReloadAt, now) {
  return !lastReloadAt || now - lastReloadAt >= RETRY_WINDOW_MS
}

function readLastReload() {
  try {
    return Number(sessionStorage.getItem(RELOAD_KEY)) || null
  } catch {
    return null
  }
}

function reloadInto(path) {
  const now = Date.now()
  if (!canReloadAgain(readLastReload(), now)) return
  try {
    sessionStorage.setItem(RELOAD_KEY, String(now))
  } catch {
    // Without storage the retry guard is lost; one reload is still worth it.
  }
  window.location.assign(path)
}

/**
 * @param {import('vue-router').Router} router
 */
export function installChunkRecovery(router) {
  router.onError((error, to) => {
    if (isChunkLoadError(error)) reloadInto(to.fullPath)
  })
  // Failed preloads outside navigation. Deferred so a navigation failure,
  // handled above with the right target URL, wins.
  window.addEventListener('vite:preloadError', () => {
    window.setTimeout(() => reloadInto(window.location.pathname + window.location.search + window.location.hash), 0)
  })
}
