const SENSITIVE_REGISTRATION_FIELDS = new Set([
  'password',
  'password_confirm',
  'steam_auth_token'
])

export function registrationDraft(form) {
  return Object.fromEntries(
    Object.entries(form || {}).filter(([field]) => !SENSITIVE_REGISTRATION_FIELDS.has(field))
  )
}
