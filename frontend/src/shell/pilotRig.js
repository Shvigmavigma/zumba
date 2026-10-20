// The GETPC pilot's rig: the user's pixel art (src/assets/pilot) in four
// pieces — torso, helmet and the two whole arms, shoulder cap to fist — where
// each sits in the drawing's frame (its own pixels), and the lines the body
// bends along (pilotDeform.js). The arms' inner edges were cut along the
// sleeves' seams; what the arms and the chin covered on the torso is filled in
// suit black, so a raised arm shows the suit's side, not a hole.

export const PILOT_RIG = Object.freeze({
  frame: { w: 980, h: 1140 },
  /** The row where the dialog box's top edge falls: the belt sits just above it. */
  edge: 890,
  /** How far below the edge the fists reach when they come down on the box. */
  gloveDepth: 90,
  /** The helmet tilts about here; below it, it stays on the collar. */
  neck: [445, 330],
  /** The body leans about here. */
  hips: [466, 900],
  // Each arm's spine: inside the shoulder (never moves), the shoulder joint, the elbow, the wrist, the end of the fist.
  L: { spine: [[264, 375], [252, 455], [211, 720], [160, 985], [165, 1125]] },
  R: { spine: [[661, 370], [680, 450], [744, 715], [772, 980], [757, 1125]] },
  parts: {
    torso: { x: 234, y: 250, w: 425, h: 710 },
    head: { x: 304, y: 17, w: 280, h: 327 },
    armL: { x: 112, y: 354, w: 195, h: 776 },
    armR: { x: 598, y: 354, w: 227, h: 776 }
  }
})
