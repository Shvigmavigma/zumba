export function defaultRaceTypeFilters() {
  return {
    qualificationTrue: false,
    qualificationFalse: false,
    teamTrue: false,
    teamFalse: false,
    officialTrue: false,
    officialFalse: false
  }
}

export function appendRaceTypeFilters(params, filters) {
  const pairs = [
    ['has_qualification', 'qualificationTrue', 'qualificationFalse'],
    ['is_team_event', 'teamTrue', 'teamFalse'],
    ['is_official', 'officialTrue', 'officialFalse']
  ]

  pairs.forEach(([queryKey, trueKey, falseKey]) => {
    if (Boolean(filters[trueKey]) !== Boolean(filters[falseKey])) {
      params.set(queryKey, filters[trueKey] ? 'true' : 'false')
    }
  })
  return params
}
