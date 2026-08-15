export function formatRating(value) {
  const rating = Number(value)
  return Number.isFinite(rating) ? Math.round(rating) : '-'
}

export const DEFAULT_LICENSE_TIERS = [
  { min_rating: 0, max_rating: 1499, name: 'Rookie', color: '#64748b' },
  { min_rating: 1500, max_rating: 2499, name: 'Bronze', color: '#b45309' },
  { min_rating: 2500, max_rating: 3999, name: 'Silver', color: '#94a3b8' },
  { min_rating: 4000, max_rating: 5499, name: 'Gold', color: '#ca8a04' },
  { min_rating: 5500, max_rating: 6999, name: 'Platinum', color: '#0891b2' },
  { min_rating: 7000, max_rating: 8499, name: 'Diamond', color: '#2563eb' },
  { min_rating: 8500, max_rating: 10000, name: 'Champ', color: '#7c3aed' }
]

export const RATING_GAMES = ['ACC', 'AC', 'iRacing', 'LMU']
export const OVERALL_RATING_GAME = 'all'

export function normalizeRatingGame(game) {
  return RATING_GAMES.includes(game) ? game : RATING_GAMES[0]
}

export function gameRatingValues(user) {
  return RATING_GAMES
    .map((game) => Number(user?.game_ratings?.[game]?.rating))
    .filter((rating) => Number.isFinite(rating))
}

export function ratingForGame(user, game = RATING_GAMES[0]) {
  if (game === OVERALL_RATING_GAME) {
    const ratings = gameRatingValues(user)
    return ratings.length ? Math.max(...ratings) : user?.rating
  }
  const normalizedGame = normalizeRatingGame(game)
  const item = user?.game_ratings?.[normalizedGame]
  return item?.rating ?? user?.rating
}

export function ratingRaceCountForGame(user, game = RATING_GAMES[0]) {
  if (game === OVERALL_RATING_GAME) {
    return RATING_GAMES.reduce((sum, itemGame) => sum + Number(user?.game_ratings?.[itemGame]?.race_count || 0), 0)
  }
  const normalizedGame = normalizeRatingGame(game)
  const item = user?.game_ratings?.[normalizedGame]
  return item?.race_count ?? user?.rating_race_count ?? 0
}

export function normalizeLicenseTiers(data) {
  const items = Array.isArray(data?.tiers) ? data.tiers : Array.isArray(data) ? data : []
  return DEFAULT_LICENSE_TIERS.map((fallback, index) => {
    const item = items[index] || {}
    const color = /^#[0-9A-Fa-f]{6}$/.test(item.color || '') ? item.color : fallback.color
    return { ...fallback, name: String(item.name || fallback.name).trim() || fallback.name, color }
  })
}

export function ratingLicenseTier(value, tiers = DEFAULT_LICENSE_TIERS) {
  const rating = Number(value)
  if (!Number.isFinite(rating)) return DEFAULT_LICENSE_TIERS[0]
  return (tiers || DEFAULT_LICENSE_TIERS).find((tier) => rating >= tier.min_rating && rating <= tier.max_rating) || DEFAULT_LICENSE_TIERS[0]
}

export function ratingLicense(value, tiers) {
  return ratingLicenseTier(value, tiers)?.name || '-'
}

export function licenseBadgeStyle(tier) {
  return { '--license-color': tier?.color || DEFAULT_LICENSE_TIERS[0].color }
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

export function teamHref(teamId) {
  const id = Number(teamId)
  return Number.isInteger(id) && id > 0 ? `/teams?team=${id}` : '/teams'
}

export function pilotName(user, fallback = '') {
  const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(' ').trim()
  return fullName || user?.nickname || user?.login || fallback
}

export function pilotSearchText(user) {
  const ratings = RATING_GAMES.flatMap((game) => [formatRating(ratingForGame(user, game)), ratingLicense(ratingForGame(user, game))])
  return [
    user?.login,
    user?.nickname,
    user?.first_name,
    user?.last_name,
    user?.pilot_number,
    user?.team_name,
    user?.team_abbreviation,
    ...ratings,
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

export function sortPilots(users, sortMode = 'rating_desc', ratingGame = RATING_GAMES[0]) {
  const sorted = [...users]
  const byName = (a, b) => pilotName(a, a?.login).localeCompare(pilotName(b, b?.login), undefined, { sensitivity: 'base' })
  const byRating = (a, b) => Number(ratingForGame(b, ratingGame) || 0) - Number(ratingForGame(a, ratingGame) || 0)
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
