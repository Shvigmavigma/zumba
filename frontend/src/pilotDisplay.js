export function formatRating(value) {
  const rating = Number(value)
  return Number.isFinite(rating) ? Math.round(rating) : '-'
}

export function formatPilotNumber(value) {
  const number = Number(value)
  return Number.isInteger(number) && number >= 0 ? String(number % 1000).padStart(3, '0') : '-'
}

export function teamShortName(name, abbreviation = '') {
  const custom = String(abbreviation || '').trim().toUpperCase()
  if (/^[A-Z]{3}$/.test(custom)) return custom
  const raw = String(name || '').trim()
  if (!raw) return '-'
  const words = raw.split(/[\s_-]+/).filter(Boolean)
  if (words.length > 1) {
    return words.map((word) => word[0]).join('').slice(0, 3).toUpperCase()
  }
  return raw.replace(/[^\p{L}\p{N}]/gu, '').slice(0, 3).toUpperCase() || '-'
}

export function pilotName(user, fallback = '') {
  const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(' ').trim()
  return fullName || user?.nickname || user?.login || fallback
}

export function pilotSearchText(user) {
  return [
    user?.login,
    user?.nickname,
    user?.first_name,
    user?.last_name,
    user?.pilot_number,
    user?.team_name,
    user?.team_abbreviation,
    formatRating(user?.rating),
    user?.sr
  ]
    .filter((value) => value !== undefined && value !== null)
    .join(' ')
    .toLowerCase()
}

export function filterPilots(users, query) {
  const needle = String(query || '').trim().toLowerCase()
  if (!needle) return users
  return users.filter((user) => pilotSearchText(user).includes(needle))
}

export function sortPilots(users, sortMode = 'rating_desc') {
  const sorted = [...users]
  const byName = (a, b) => pilotName(a, a?.login).localeCompare(pilotName(b, b?.login), undefined, { sensitivity: 'base' })
  const byRating = (a, b) => Number(b?.rating || 0) - Number(a?.rating || 0)
  const bySr = (a, b) => Number(b?.sr || 0) - Number(a?.sr || 0)
  sorted.sort((a, b) => {
    if (sortMode === 'alpha_asc') return byName(a, b)
    if (sortMode === 'alpha_desc') return byName(b, a)
    if (sortMode === 'rating_asc') return byRating(b, a) || byName(a, b)
    if (sortMode === 'sr_desc') return bySr(a, b) || byRating(a, b) || byName(a, b)
    if (sortMode === 'sr_asc') return bySr(b, a) || byRating(a, b) || byName(a, b)
    return byRating(a, b) || bySr(a, b) || byName(a, b)
  })
  return sorted
}
