// Profile fields that wait for a moderator before they go live (backend:
// users.update_me stores every submitted one in pending_profile_changes).
export const MODERATED_FIELDS = ['email', 'first_name', 'last_name', 'nickname', 'country', 'discord', 'games', 'avatar_color']

const NULLABLE_FIELDS = new Set(['country', 'discord'])

function comparable(field, value) {
  if (field === 'games') return [...(value || [])].sort().join(',')
  if (value === undefined || value === null) return ''
  const text = String(value).trim()
  return field === 'avatar_color' || field === 'email' ? text.toLowerCase() : text
}

function payloadValue(field, value) {
  if (field === 'games') return [...(value || [])]
  if (NULLABLE_FIELDS.has(field)) return value || null
  return value
}

function pendingChanges(user) {
  const pending = user?.pending_profile_changes
  return pending && typeof pending === 'object' ? pending : {}
}

/**
 * The moderated fields to PATCH: those that differ from the approved profile,
 * plus any field already awaiting review, so taking an edit back replaces the
 * pending request instead of leaving it untouched. Other fields are left out
 * so a moderator only reviews real edits.
 * @param {Record<string, unknown>} form
 * @param {Record<string, unknown> | null | undefined} approved
 * @returns {Record<string, unknown>}
 */
export function changedProfileFields(form, approved) {
  const pending = pendingChanges(approved)
  return Object.fromEntries(MODERATED_FIELDS
    .filter((field) => field in pending || comparable(field, form[field]) !== comparable(field, approved?.[field]))
    .map((field) => [field, payloadValue(field, form[field])]))
}

/**
 * The values to edit: the approved profile with any edits still awaiting
 * review on top, so saving again keeps them.
 * @param {Record<string, unknown> | null | undefined} user
 * @returns {Record<string, unknown>}
 */
export function editableProfile(user) {
  return { ...(user || {}), ...pendingChanges(user) }
}
