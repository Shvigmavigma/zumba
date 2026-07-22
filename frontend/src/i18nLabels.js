export function translatedValue(t, scope, value, fallback = (item) => String(item || '').replaceAll('_', ' ')) {
  const key = `${scope}.${value}`
  const translated = t(key)
  return translated === key ? fallback(value) : translated
}

export function roleLabel(t, role) {
  return translatedValue(t, 'roles', role)
}

export function statusLabel(t, status) {
  return translatedValue(t, 'statuses', status)
}

export const GAME_VALUES = ['ACC', 'AC', 'iRacing']

export function gameLabel(t, game) {
  return translatedValue(t, 'games', game)
}

export function gameOptions(t, includeAll = false) {
  const options = GAME_VALUES.map((value) => ({ value, label: gameLabel(t, value) }))
  return includeAll ? [{ value: 'all', label: t('raceFilters.allGames') }, ...options] : options
}

export function countryLabel(t, country) {
  return !country || country === 'Global' ? t('common.global') : country
}

export function raceCountLabel(t, locale, count) {
  if (locale !== 'ru') {
    return `${count} ${t(count === 1 ? 'calendar.raceWordOne' : 'calendar.raceWordMany')}`
  }

  const mod10 = count % 10
  const mod100 = count % 100
  const key = mod10 === 1 && mod100 !== 11
    ? 'calendar.raceWordOne'
    : mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)
      ? 'calendar.raceWordFew'
      : 'calendar.raceWordMany'
  return `${count} ${t(key)}`
}
