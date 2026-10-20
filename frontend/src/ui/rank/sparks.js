// Shared by the rank effects that throw sparks (RankScene, RankAura): a seeded
// random, so a card looks the same on every render, and the plan of where a
// spark emitter stands on each of its cycles.

/** Mulberry32: tiny seeded generator, stable layouts without storing them. */
export function seededRandom(seed) {
  let state = seed >>> 0
  return () => {
    state = (state + 0x6d2b79f5) | 0
    let t = Math.imul(state ^ (state >>> 15), 1 | state)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

// An emitter visits these zones in turn. No two in a row are the same or
// neighbours, also from the last back to the first and with the two end zones
// counted as neighbours (they touch on a closed rim).
const HOP_ZONES = [0, 2, 5, 3, 1, 4]
export const HOP_COUNT = HOP_ZONES.length
const MIN_STRENGTH = 0.65
const MAX_STRENGTH = 1.15
// Keeps a place away from its zone's borders, so two hops never end up side by side.
const ZONE_MARGIN = 0.1

/**
 * Where an emitter stands on each of its cycles (--x0..5, a number between min
 * and max) and how strong that shower is (--k0..5). The hop keyframes read
 * these; each emitter starts the round at a random zone.
 */
export function hopVars(rnd, min, max) {
  const between = (from, to) => from + rnd() * (to - from)
  const first = Math.floor(rnd() * HOP_COUNT)
  const zoneWidth = (max - min) / HOP_COUNT
  return Object.fromEntries(
    HOP_ZONES.flatMap((_, hop) => {
      const zone = HOP_ZONES[(hop + first) % HOP_COUNT]
      return [
        [`--x${hop}`, (min + (zone + between(ZONE_MARGIN, 1 - ZONE_MARGIN)) * zoneWidth).toFixed(1)],
        [`--k${hop}`, between(MIN_STRENGTH, MAX_STRENGTH).toFixed(2)]
      ]
    })
  )
}
