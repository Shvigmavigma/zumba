import assert from 'node:assert/strict'
import test from 'node:test'
import { fetchAllAdminUserMatches } from '../src/adminUserSearch.js'

test('fetches every page of admin user matches using the selected fingerprint', async () => {
  const requestedOffsets = []
  const api = async (path) => {
    const url = new URL(path, 'https://bmrl.test')
    assert.equal(url.searchParams.get('search_by'), 'device_id')
    assert.equal(url.searchParams.get('search'), 'safe-prefix')
    const offset = Number(url.searchParams.get('offset'))
    requestedOffsets.push(offset)
    return offset === 0
      ? Array.from({ length: 2 }, (_, index) => ({ id: index + 1 }))
      : [{ id: 3 }]
  }

  const matches = await fetchAllAdminUserMatches(api, 'device_id', ' safe-prefix ', 2)

  assert.deepEqual(requestedOffsets, [0, 2])
  assert.deepEqual(matches.map(({ id }) => id), [1, 2, 3])
})
