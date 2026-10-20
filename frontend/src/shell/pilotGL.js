// Draws the GETPC pilot with WebGL (ThemePilot.vue): the pieces of the user's
// drawing — torso, helmet, the two whole arms — each a mesh over its drawn
// pixels, bent every frame (pilotDeform.js) and laid out in the scene. One
// canvas, in front of the dialog box: the torso and the helmet are cut at the
// box's edge, so the box hides what is below it; the arms are cut there too
// while they hang, and drawn whole once they are up, fists over the box.
// An arm is drawn upper half first, then the forearm over it, and the parts of
// the sleeve a hard bend folds over are left out, so the inside of an elbow is
// a clean overlap. Drawn in the same style: the inner edges of the sleeves
// (they show once an arm moves away from the body), the inside of a bent elbow
// (a rounded fold over what the bend squeezes) and an open hand that the fist
// unclenches into.

import { armCurve, bendArm, curveAt, gridMesh, prepareArm, tiltHead } from './pilotDeform'
import { PILOT_RIG as RIG } from './pilotRig'

const PIECES = ['torso', 'head', 'armL', 'armR']
const NEVER = 1e6
// The open hand: how big against the drawing, and where it sits against the wrist.
const HAND_SCALE = 0.85
const HAND_FROM_WRIST = -12
const HAND_POINTS_AT = 40
// The inside of the elbow: from what bend it shows, and fully by how much more.
const ELBOW_FROM = 30
const ELBOW_OVER = 40

const VERTEX = `
attribute vec2 aPos;
attribute vec2 aUv;
attribute float aS;
uniform vec2 uView;
uniform float uScale;
uniform vec2 uShift;
uniform vec3 uBody;
uniform vec2 uHips;
varying vec2 vUv;
varying float vY;
varying float vS;
void main() {
  vec2 p = aPos - uHips;
  float c = cos(uBody.z);
  float s = sin(uBody.z);
  p = vec2(p.x * c - p.y * s, p.x * s + p.y * c) + uHips + uBody.xy;
  vec2 q = p * uScale + uShift;
  vY = q.y;
  vUv = aUv;
  vS = aS;
  gl_Position = vec4(q.x / uView.x * 2.0 - 1.0, 1.0 - q.y / uView.y * 2.0, 0.0, 1.0);
}`

// uFistFrom: where along the arm the fist starts; past it the fist fades to uFist (as the hand opens).
const FRAGMENT = `
precision mediump float;
uniform sampler2D uTex;
uniform float uClip;
uniform float uAlpha;
uniform float uFistFrom;
uniform float uFist;
varying vec2 vUv;
varying float vY;
varying float vS;
void main() {
  if (vY > uClip) discard;
  float fist = mix(1.0, uFist, smoothstep(uFistFrom - 6.0, uFistFrom + 6.0, vS));
  gl_FragColor = texture2D(uTex, vUv) * uAlpha * fist;
}`

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error(`pilot part did not load: ${url}`))
    image.src = url
  })
}

/** Reads an image's alpha, to lay the mesh over what is drawn. */
function alphaOf(image) {
  const canvas = document.createElement('canvas')
  canvas.width = image.naturalWidth
  canvas.height = image.naturalHeight
  const context = canvas.getContext('2d', { willReadFrequently: true })
  context.drawImage(image, 0, 0)
  const { data } = context.getImageData(0, 0, canvas.width, canvas.height)
  return (x, y) => data[(Math.min(canvas.height - 1, y) * canvas.width + Math.min(canvas.width - 1, x)) * 4 + 3]
}

function shader(gl, type, source) {
  const unit = gl.createShader(type)
  gl.shaderSource(unit, source)
  gl.compileShader(unit)
  if (!gl.getShaderParameter(unit, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(unit) || 'shader did not compile')
  return unit
}

/**
 * Sets up the pilot on a canvas. Resolves to null where WebGL is not available.
 * @param {HTMLCanvasElement} canvas
 * @param {Record<string, string>} urls  image URL of each piece: torso, head, armL, armR,
 *   armLEdge, armREdge (the sleeves' inner edges), handL, handR (the open hands), elbow (the inside of a bent elbow)
 */
export async function createPilotGL(canvas, urls) {
  const options = { alpha: true, premultipliedAlpha: true, antialias: true }
  const gl = canvas.getContext('webgl2', options) || canvas.getContext('webgl', options)
  if (!gl) return null
  const modern = typeof WebGL2RenderingContext !== 'undefined' && gl instanceof WebGL2RenderingContext

  const program = gl.createProgram()
  gl.attachShader(program, shader(gl, gl.VERTEX_SHADER, VERTEX))
  gl.attachShader(program, shader(gl, gl.FRAGMENT_SHADER, FRAGMENT))
  gl.linkProgram(program)
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program) || 'program did not link')
  const at = (name) => gl.getUniformLocation(program, name)
  const uniforms = {
    view: at('uView'), scale: at('uScale'), shift: at('uShift'), body: at('uBody'), hips: at('uHips'),
    clip: at('uClip'), alpha: at('uAlpha'), fistFrom: at('uFistFrom'), fist: at('uFist'), tex: at('uTex')
  }
  const attributes = { pos: gl.getAttribLocation(program, 'aPos'), uv: gl.getAttribLocation(program, 'aUv'), s: gl.getAttribLocation(program, 'aS') }

  function texture(image) {
    const unit = gl.createTexture()
    gl.bindTexture(gl.TEXTURE_2D, unit)
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true)
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR)
    if (modern) {
      // The drawing is shown smaller than drawn: mipmaps keep it clean.
      gl.generateMipmap(gl.TEXTURE_2D)
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR)
    } else {
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR)
    }
    return unit
  }

  function buffer(data, kind = gl.ARRAY_BUFFER, usage = gl.STATIC_DRAW) {
    const unit = gl.createBuffer()
    gl.bindBuffer(kind, unit)
    gl.bufferData(kind, data, usage)
    return unit
  }

  const names = [...PIECES, 'armLEdge', 'armREdge', 'handL', 'handR', 'elbow']
  const loaded = Object.fromEntries(names.map((name, index) => [name, index]))
  const images = await Promise.all(names.map((name) => loadImage(urls[name])))

  const pieces = PIECES.map((name) => {
    const image = images[loaded[name]]
    const mesh = gridMesh(alphaOf(image), RIG.parts[name], 10)
    const side = name === 'armL' ? 'L' : name === 'armR' ? 'R' : null
    const arm = side ? prepareArm(RIG[side].spine, mesh.positions) : null
    // Where each point lies along its arm (nothing to fade on the torso or the helmet).
    const along = arm ? Float32Array.from(arm.s) : new Float32Array(mesh.positions.length / 2).fill(-NEVER)
    // An arm's triangles: the upper half first, the forearm after it, so the forearm lies over it at the elbow.
    let indices = mesh.indices
    let upperCount = indices.length
    if (arm) {
      const elbowAt = arm.spine.at[2]
      const upper = []
      const lower = []
      for (let i = 0; i < indices.length; i += 3) {
        const middle = (arm.s[indices[i]] + arm.s[indices[i + 1]] + arm.s[indices[i + 2]]) / 3
        ;(middle < elbowAt ? upper : lower).push(indices[i], indices[i + 1], indices[i + 2])
      }
      indices = Uint16Array.from([...upper, ...lower])
      upperCount = upper.length
    }
    return {
      name,
      side,
      texture: texture(image),
      edge: side ? texture(images[loaded[`arm${side}Edge`]]) : null,
      hand: side ? texture(images[loaded[`hand${side}`]]) : null,
      handSize: side ? [images[loaded[`hand${side}`]].naturalWidth * HAND_SCALE, images[loaded[`hand${side}`]].naturalHeight * HAND_SCALE] : null,
      positions: buffer(mesh.positions, gl.ARRAY_BUFFER, name === 'torso' ? gl.STATIC_DRAW : gl.DYNAMIC_DRAW),
      uvs: buffer(mesh.uvs),
      along: buffer(along),
      indices: buffer(indices, gl.ELEMENT_ARRAY_BUFFER),
      count: indices.length,
      upperCount,
      rest: mesh.positions,
      arm,
      bent: new Float32Array(mesh.positions.length)
    }
  })

  const elbow = { texture: texture(images[loaded.elbow]), w: images[loaded.elbow].naturalWidth, h: images[loaded.elbow].naturalHeight }

  // The open hand and the inside of the elbow: a quad, placed every frame.
  const quad = {
    positions: buffer(new Float32Array(8), gl.ARRAY_BUFFER, gl.DYNAMIC_DRAW),
    uvs: buffer(Float32Array.from([0, 0, 1, 0, 0, 1, 1, 1])),
    along: buffer(new Float32Array(4).fill(-NEVER)),
    indices: buffer(Uint16Array.from([0, 1, 2, 1, 3, 2]), gl.ELEMENT_ARRAY_BUFFER),
    corners: new Float32Array(8)
  }

  function bindMesh(mesh) {
    gl.bindBuffer(gl.ARRAY_BUFFER, mesh.positions)
    gl.enableVertexAttribArray(attributes.pos)
    gl.vertexAttribPointer(attributes.pos, 2, gl.FLOAT, false, 0, 0)
    gl.bindBuffer(gl.ARRAY_BUFFER, mesh.uvs)
    gl.enableVertexAttribArray(attributes.uv)
    gl.vertexAttribPointer(attributes.uv, 2, gl.FLOAT, false, 0, 0)
    gl.bindBuffer(gl.ARRAY_BUFFER, mesh.along)
    gl.enableVertexAttribArray(attributes.s)
    gl.vertexAttribPointer(attributes.s, 1, gl.FLOAT, false, 0, 0)
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, mesh.indices)
  }

  /** Lays the quad's corners (top left, top right, bottom left, bottom right of its image) at a point, turned. */
  function placeQuad(base, turn, corners) {
    const cos = Math.cos(turn)
    const sin = Math.sin(turn)
    corners.forEach(([x, y], i) => {
      quad.corners[i * 2] = base.x + x * cos - y * sin
      quad.corners[i * 2 + 1] = base.y + x * sin + y * cos
    })
    gl.bindBuffer(gl.ARRAY_BUFFER, quad.positions)
    gl.bufferSubData(gl.ARRAY_BUFFER, 0, quad.corners)
  }

  /** The open hand: its cuff at the wrist, fingers the way the wrist sends them (the drawn hand points up). */
  function placeHand(piece, curve) {
    const wristAt = piece.arm.spine.at[3]
    const [w, h] = piece.handSize
    placeQuad(curveAt(curve, wristAt + HAND_FROM_WRIST), curveAt(curve, wristAt + HAND_POINTS_AT).angle + Math.PI / 2,
      [[-w / 2, -h], [w / 2, -h], [-w / 2, 0], [w / 2, 0]])
  }

  /** The inside of the elbow: the half disc's flat side along the arm, its round side into the bend. */
  function placeElbow(piece, curve, bend) {
    const at = curveAt(curve, piece.arm.spine.at[2])
    // Its image runs along the arm with its round side down; turned half round when the bend goes the other way.
    const turn = at.angle + (bend > 0 ? 0 : Math.PI)
    const w = elbow.w
    const h = elbow.h
    placeQuad(at, turn, [[-w / 2, 0], [w / 2, 0], [-w / 2, h], [w / 2, h]])
  }

  /**
   * One frame.
   * @param {object} view  css size of the canvas, pixel ratio, scale of the drawing, where its frame
   *   starts on the canvas, and the canvas row where the box's edge falls
   * @param {Record<string, number>} pose  joint values (pilotPoses.js JOINTS), plus rise (drawing px down)
   * @param {boolean} armsFront  arms drawn whole, over the box
   */
  function draw(view, pose, armsFront) {
    const dpr = view.dpr
    const width = Math.round(view.width * dpr)
    const height = Math.round(view.height * dpr)
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width
      canvas.height = height
    }
    gl.viewport(0, 0, width, height)
    gl.clearColor(0, 0, 0, 0)
    gl.clear(gl.COLOR_BUFFER_BIT)
    gl.enable(gl.BLEND)
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA)
    // A hard bend folds part of a sleeve over: those triangles face away and are not drawn.
    // The meshes run clockwise once y points down the screen, so clockwise is their front.
    gl.enable(gl.CULL_FACE)
    gl.frontFace(gl.CW)
    gl.cullFace(gl.BACK)
    gl.useProgram(program)
    gl.uniform2f(uniforms.view, width, height)
    gl.uniform1f(uniforms.scale, view.scale * dpr)
    gl.uniform2f(uniforms.shift, view.shiftX * dpr, view.shiftY * dpr)
    gl.uniform3f(uniforms.body, pose.x, pose.y + pose.rise, (pose.lean * Math.PI) / 180)
    gl.uniform2f(uniforms.hips, RIG.hips[0], RIG.hips[1])
    gl.uniform1i(uniforms.tex, 0)
    gl.activeTexture(gl.TEXTURE0)

    for (const piece of pieces) {
      const front = piece.arm && armsFront
      gl.uniform1f(uniforms.clip, (front ? view.height : view.edge) * dpr)
      gl.uniform1f(uniforms.alpha, 1)
      gl.uniform1f(uniforms.fistFrom, NEVER)
      gl.uniform1f(uniforms.fist, 1)
      let curve = null
      gl.bindBuffer(gl.ARRAY_BUFFER, piece.positions)
      if (piece.name === 'head') {
        gl.bufferSubData(gl.ARRAY_BUFFER, 0, tiltHead(piece.rest, RIG.neck, pose.tilt, pose.nod, piece.bent))
      } else if (piece.arm) {
        const s = piece.side
        const angles = { shoulder: pose[`${s}s`], elbow: pose[`${s}e`], wrist: pose[`${s}w`] }
        curve = armCurve(piece.arm, angles)
        gl.bufferSubData(gl.ARRAY_BUFFER, 0, bendArm(piece.arm, angles, piece.bent, curve))
      }
      bindMesh(piece)
      gl.bindTexture(gl.TEXTURE_2D, piece.texture)
      if (!piece.arm) {
        gl.drawElements(gl.TRIANGLES, piece.count, gl.UNSIGNED_SHORT, 0)
        continue
      }

      // The fist gives way to the open hand as the hand opens.
      const open = Math.min(1, Math.max(0, pose[`${piece.side}o`] || 0))
      gl.uniform1f(uniforms.fistFrom, piece.arm.spine.at[3] + 6)
      gl.uniform1f(uniforms.fist, 1 - open)
      gl.drawElements(gl.TRIANGLES, piece.upperCount, gl.UNSIGNED_SHORT, 0)
      gl.drawElements(gl.TRIANGLES, piece.count - piece.upperCount, gl.UNSIGNED_SHORT, piece.upperCount * 2)

      // The inside of the elbow, over what the bend squeezes.
      const bend = pose[`${piece.side}e`]
      const fold = Math.min(1, Math.max(0, (Math.abs(bend) - ELBOW_FROM) / ELBOW_OVER))
      if (fold > 0) {
        placeElbow(piece, curve, bend)
        bindMesh(quad)
        gl.bindTexture(gl.TEXTURE_2D, elbow.texture)
        gl.uniform1f(uniforms.fistFrom, NEVER)
        gl.uniform1f(uniforms.alpha, fold)
        gl.drawElements(gl.TRIANGLES, 6, gl.UNSIGNED_SHORT, 0)
        gl.uniform1f(uniforms.alpha, 1)
        gl.uniform1f(uniforms.fistFrom, piece.arm.spine.at[3] + 6)
        bindMesh(piece)
      }

      // The sleeve's inner edge, as the arm leaves the body.
      const away = Math.min(1, Math.max(0, (Math.abs(pose[`${piece.side}s`]) - 8) / 22))
      if (away > 0) {
        gl.bindTexture(gl.TEXTURE_2D, piece.edge)
        gl.uniform1f(uniforms.alpha, away)
        gl.drawElements(gl.TRIANGLES, piece.upperCount, gl.UNSIGNED_SHORT, 0)
        gl.uniform1f(uniforms.alpha, 1)
      }

      if (open > 0.01) {
        placeHand(piece, curve)
        bindMesh(quad)
        gl.bindTexture(gl.TEXTURE_2D, piece.hand)
        gl.uniform1f(uniforms.fistFrom, NEVER)
        gl.uniform1f(uniforms.fist, 1)
        gl.uniform1f(uniforms.alpha, open)
        gl.drawElements(gl.TRIANGLES, 6, gl.UNSIGNED_SHORT, 0)
      }
    }
  }

  function destroy() {
    for (const piece of pieces) {
      for (const unit of [piece.texture, piece.edge, piece.hand]) if (unit) gl.deleteTexture(unit)
      for (const unit of [piece.positions, piece.uvs, piece.along, piece.indices]) gl.deleteBuffer(unit)
    }
    for (const unit of [quad.positions, quad.uvs, quad.along, quad.indices]) gl.deleteBuffer(unit)
    gl.deleteTexture(elbow.texture)
    gl.deleteProgram(program)
  }

  return { draw, destroy }
}
