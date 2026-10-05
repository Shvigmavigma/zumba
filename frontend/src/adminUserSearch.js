export async function fetchAllAdminUserMatches(api, searchBy, search, limit = 200) {
  const value = String(search || '').trim()
  if (!value) return []

  const matches = []
  for (let offset = 0; ; offset += limit) {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
      sort: 'rating_desc',
      rating_game: 'ACC',
      search_by: searchBy,
      search: value
    })
    const page = await api(`/users/admin?${params.toString()}`)
    if (!Array.isArray(page)) throw new Error('Unexpected admin user search response')
    matches.push(...page)
    if (page.length < limit) return matches
  }
}
