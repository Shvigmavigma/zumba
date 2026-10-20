// Links typed in by staff (sponsor banners, donations, race servers, videos)
// end up in href attributes. Only web links and same-site paths are allowed,
// so a value such as "javascript:..." can never run in a visitor's browser.

const ALLOWED_PROTOCOLS = new Set(['http:', 'https:'])

/**
 * The link if it is an http(s) URL or a same-site path, otherwise ''.
 * Protocol-relative links ("//host/path") are upgraded to https.
 * @param {unknown} value
 * @returns {string}
 */
export function safeHttpUrl(value) {
  const raw = String(value ?? '').trim()
  if (!raw) return ''
  if (raw.startsWith('//')) return safeHttpUrl(`https:${raw}`)
  if (raw.startsWith('/')) return /^\/[^/\\]/.test(raw) || raw === '/' ? raw : ''
  try {
    return ALLOWED_PROTOCOLS.has(new URL(raw).protocol) ? raw : ''
  } catch {
    return ''
  }
}
