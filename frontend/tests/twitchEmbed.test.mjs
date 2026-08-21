import assert from 'node:assert/strict'
import test from 'node:test'
import { validTwitchParent } from '../src/twitchEmbed.js'

test('Twitch parent accepts domains and rejects IP addresses', () => {
  assert.equal(validTwitchParent('localhost'), 'localhost')
  assert.equal(validTwitchParent('Racing.Example.COM.'), 'racing.example.com')
  assert.equal(validTwitchParent('127.0.0.1'), '')
  assert.equal(validTwitchParent('192.168.1.20'), '')
  assert.equal(validTwitchParent('invalid_host'), '')
})
