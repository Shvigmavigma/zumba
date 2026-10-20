// Maps raw API / Steam callback messages to friendly, translated explanations.
const KNOWN = [
  { match: /^Invalid credentials$/i, key: 'invalidCredentials' },
  { match: /already exists/i, key: 'duplicate', resetSteam: true },
  { match: /^Steam authentication is required$/i, key: 'steamRequired', resetSteam: true },
  { match: /cancelled/i, key: 'steamCancelled' },
  { match: /^Steam authentication failed$|^Steam ID was not returned$/i, key: 'steamFailed' },
  { match: /^Steam account is already linked$/i, key: 'steamLinked' },
  { match: /^Steam account is not linked$/i, key: 'steamNotLinked' },
  { match: /storage is unavailable/i, key: 'storage' }
]

/**
 * @param {(key: string, values?: object) => string} t
 * @param {string} message
 * @returns {{ text: string, resetSteam: boolean }}
 */
export function friendlyAuthError(t, message) {
  const raw = String(message || '')
  const status = raw.match(/^Account status is (\w+)$/i)
  if (status) {
    return { text: t('authPage.serverErrors.accountStatus', { status: t(`statuses.${status[1]}`) }), resetSteam: false }
  }
  const known = KNOWN.find((item) => item.match.test(raw))
  if (!known) return { text: raw, resetSteam: false }
  return { text: t(`authPage.serverErrors.${known.key}`), resetSteam: Boolean(known.resetSteam) }
}
