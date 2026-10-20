import assert from 'node:assert/strict'
import test from 'node:test'
import { DEFAULT_TEAM_COLOR, isBrightTeamColor, teamInk, teamStyle } from '../src/pages/teams/teamUtils.js'

test('a bright team colour takes dark ink, a deep one takes white', () => {
  assert.equal(isBrightTeamColor('#f59e0b'), true)
  assert.equal(teamInk('#f59e0b'), '#05070c')
  assert.equal(isBrightTeamColor('#1652d8'), false)
  assert.equal(teamInk('#1652d8'), '#ffffff')
})

test('an invalid colour falls back to the default livery', () => {
  assert.equal(isBrightTeamColor('not-a-colour'), isBrightTeamColor(DEFAULT_TEAM_COLOR))
  assert.deepEqual(teamStyle(''), { '--team': DEFAULT_TEAM_COLOR, '--team-ink': teamInk(DEFAULT_TEAM_COLOR) })
})
