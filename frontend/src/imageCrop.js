export function calculateCropGeometry(naturalWidth, naturalHeight, frameWidth, frameHeight, zoom, offsetX, offsetY) {
  if (!naturalWidth || !naturalHeight || !frameWidth || !frameHeight) return null
  const baseScale = Math.max(frameWidth / naturalWidth, frameHeight / naturalHeight)
  const scale = baseScale * zoom
  const displayWidth = naturalWidth * scale
  const displayHeight = naturalHeight * scale
  return {
    scale,
    displayWidth,
    displayHeight,
    maxOffsetX: Math.max(0, (displayWidth - frameWidth) / 2),
    maxOffsetY: Math.max(0, (displayHeight - frameHeight) / 2),
    left: (frameWidth - displayWidth) / 2 + offsetX,
    top: (frameHeight - displayHeight) / 2 + offsetY,
    frameWidth,
    frameHeight
  }
}

export function clampCropOffset(value, maximum) {
  return Math.min(maximum, Math.max(-maximum, value))
}

export function cropSourceRect(geometry, naturalWidth, naturalHeight) {
  const sourceX = Math.max(0, -geometry.left / geometry.scale)
  const sourceY = Math.max(0, -geometry.top / geometry.scale)
  return {
    x: sourceX,
    y: sourceY,
    width: Math.min(naturalWidth - sourceX, geometry.frameWidth / geometry.scale),
    height: Math.min(naturalHeight - sourceY, geometry.frameHeight / geometry.scale)
  }
}
