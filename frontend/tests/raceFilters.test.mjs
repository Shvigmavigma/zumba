import assert from 'node:assert/strict'
import test from 'node:test'
import { appendRaceTypeFilters, defaultRaceTypeFilters } from '../src/raceFilters.js'

test('race type filters omit dimensions with neither or both options checked', () => {
  const params = appendRaceTypeFilters(new URLSearchParams(), defaultRaceTypeFilters())
  assert.equal(params.toString(), '')

  const both = defaultRaceTypeFilters()
  both.teamTrue = true
  both.teamFalse = true
  assert.equal(appendRaceTypeFilters(new URLSearchParams(), both).has('is_team_event'), false)
})

test('race type filters encode the selected true and false options', () => {
  const filters = defaultRaceTypeFilters()
  filters.qualificationTrue = true
  filters.teamFalse = true
  filters.officialTrue = true

  const params = appendRaceTypeFilters(new URLSearchParams(), filters)
  assert.equal(params.get('has_qualification'), 'true')
  assert.equal(params.get('is_team_event'), 'false')
  assert.equal(params.get('is_official'), 'true')
})
