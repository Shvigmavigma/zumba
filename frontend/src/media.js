export function isVideoUrl(url = '') {
  return /\.(mp4|webm|mov|mkv)(?:$|[?#])/i.test(String(url || ''))
}

export function isVideoFile(file) {
  if (!file) return false
  return String(file.type || '').startsWith('video/') || /\.(mp4|webm|mov|mkv)$/i.test(file.name || '')
}

export function isGifFile(file) {
  if (!file) return false
  return file.type === 'image/gif' || /\.gif$/i.test(file.name || '')
}

export function isGifUrl(url = '') {
  return /\.gif(?:$|[?#])/i.test(String(url || ''))
}

export const mediaUploadAccept = 'image/png,image/jpeg,image/webp,image/gif,video/mp4,video/webm,video/quicktime,video/x-matroska,.mp4,.webm,.mov,.mkv'
