import { vReveal, vSplit } from './motion/reveal'
import { vMagnet, vSpark, vSpotlight, vTilt } from './motion/pointer'
import { vTrackArt } from './motion/trackArt'

/**
 * Registers the BMRL motion directives globally:
 * v-reveal, v-split, v-spotlight, v-tilt, v-magnet, v-spark, v-track-art.
 * @param {import('vue').App} app
 */
export function installUi(app) {
  app.directive('reveal', vReveal)
  app.directive('split', vSplit)
  app.directive('spotlight', vSpotlight)
  app.directive('tilt', vTilt)
  app.directive('magnet', vMagnet)
  app.directive('spark', vSpark)
  app.directive('track-art', vTrackArt)
}
