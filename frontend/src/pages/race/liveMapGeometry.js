export function mapIsPortrait(geometry) {
  return geometry.HEIGHT > geometry.WIDTH
}

export function mapPoint(position, geometry, flip = false) {
  const x = ((position.x + geometry.X_OFFSET) / geometry.SCALE_FACTOR + geometry.PADDING) / geometry.WIDTH
  const y = ((position.z + geometry.Z_OFFSET) / geometry.SCALE_FACTOR + geometry.PADDING) / geometry.HEIGHT
  const point = mapIsPortrait(geometry)
    ? { left: (1 - y) * 100, top: x * 100 }
    : { left: x * 100, top: y * 100 }
  return flip ? { left: 100 - point.left, top: 100 - point.top } : point
}
