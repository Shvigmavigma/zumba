export function validTwitchParent(hostname) {
  const host = String(hostname || '').trim().toLowerCase().replace(/\.$/, '')
  if (host === 'localhost') return host
  if (!host.includes('.') || host.length > 253) return ''
  const labels = host.split('.')
  const validLabels = labels.every((label) => /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(label))
  return validLabels && !/^\d+$/.test(labels.at(-1)) ? host : ''
}
