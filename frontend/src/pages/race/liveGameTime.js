// Sol setups created by Server Manager may encode a fixed date and time in
// the start timestamp, while Content Manager can encode seconds after midnight.
export function readGameTime(weather) {
  const fields = Object.fromEntries(
    [...String(weather || '').matchAll(/_(time|mult|start)=(-?\d+)/g)]
      .map(match => [match[1], Number(match[2])])
  )
  if (!Number.isFinite(fields.time) || fields.time < 0 || fields.time >= 86400 || fields.mult !== 0) return null
  if (fields.time === 0 && fields.start > 0) {
    const date = new Date(fields.start * 1000)
    if (!Number.isFinite(date.getTime())) return null
    return { value: new Intl.DateTimeFormat('en-GB', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(date), estimated: false }
  }
  const hours = String(Math.floor(fields.time / 3600)).padStart(2, '0')
  const minutes = String(Math.floor(fields.time % 3600 / 60)).padStart(2, '0')
  return { value: `${hours}:${minutes}`, estimated: false }
}
