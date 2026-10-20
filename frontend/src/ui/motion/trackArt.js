// v-track-art — classifies admin-uploaded track artwork once it loads.
// Light, colourless images are track diagrams (black lines on white): the dark
// theme shows them as glowing white lines (see design/fx.css). Photos are left
// untouched. Cross-origin images cannot be sampled and are left as they are.

const SAMPLE_W = 32
const SAMPLE_H = 18
const LIGHT_LUMA = 0.62
const MAX_DIAGRAM_SATURATION = 0.16
const toneCache = new Map()

/**
 * Average luminance (0–1) and saturation (0–1) of an RGBA pixel buffer.
 * @param {Uint8ClampedArray} data
 * @returns {{ luma: number, saturation: number }}
 */
export function measureTone(data) {
  let luma = 0
  let saturation = 0
  let count = 0
  for (let index = 0; index < data.length; index += 4) {
    if (data[index + 3] < 16) continue
    const r = data[index] / 255
    const g = data[index + 1] / 255
    const b = data[index + 2] / 255
    const max = Math.max(r, g, b)
    const min = Math.min(r, g, b)
    luma += 0.2126 * r + 0.7152 * g + 0.0722 * b
    saturation += max === 0 ? 0 : (max - min) / max
    count += 1
  }
  return count ? { luma: luma / count, saturation: saturation / count } : { luma: 0, saturation: 0 }
}

/**
 * @param {{ luma: number, saturation: number }} tone
 * @returns {'diagram' | 'photo'}
 */
export function classifyTone(tone) {
  return tone.luma >= LIGHT_LUMA && tone.saturation <= MAX_DIAGRAM_SATURATION ? 'diagram' : 'photo'
}

function sample(img) {
  const canvas = document.createElement('canvas')
  canvas.width = SAMPLE_W
  canvas.height = SAMPLE_H
  const context = canvas.getContext('2d', { willReadFrequently: true })
  context.drawImage(img, 0, 0, SAMPLE_W, SAMPLE_H)
  return classifyTone(measureTone(context.getImageData(0, 0, SAMPLE_W, SAMPLE_H).data))
}

function apply(img) {
  const src = img.currentSrc || img.src
  if (!src) return
  if (toneCache.has(src)) {
    img.dataset.tone = toneCache.get(src)
    return
  }
  try {
    const tone = sample(img)
    toneCache.set(src, tone)
    img.dataset.tone = tone
  } catch {
    // Tainted canvas (cross-origin image): keep the artwork as uploaded.
    toneCache.set(src, 'unknown')
  }
}

const listeners = new WeakMap()

export const vTrackArt = {
  mounted(img) {
    const onLoad = () => apply(img)
    listeners.set(img, onLoad)
    img.addEventListener('load', onLoad)
    if (img.complete && img.naturalWidth) apply(img)
  },
  updated(img) {
    const src = img.currentSrc || img.src
    if (toneCache.has(src)) img.dataset.tone = toneCache.get(src)
    else delete img.dataset.tone
  },
  unmounted(img) {
    const onLoad = listeners.get(img)
    if (onLoad) img.removeEventListener('load', onLoad)
    listeners.delete(img)
  }
}
