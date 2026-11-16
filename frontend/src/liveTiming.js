import { onMounted, onBeforeUnmount, reactive, watch } from 'vue'
import { API_BASE } from './api'

export const timing = reactive({ active: false, stale: false, loaded: false, session: null, updated: 0 })

// One poller feeds both the navigation indicator and the open timing page.
export function useTimingPolling(route) {
  let timer
  let controller
  let stop

  async function poll() {
    clearTimeout(timer)
    controller?.abort()
    if (document.hidden) return
    const current = new AbortController()
    controller = current
    const full = route.path === '/live/ac'
    const timeout = setTimeout(() => current.abort(), 9000)
    try {
      const response = await fetch(API_BASE + '/live-timing/ac' + (full ? '' : '?status_only=true'), {
        signal: current.signal, cache: 'no-store'
      })
      if (!response.ok) throw new Error(String(response.status))
      const data = await response.json()
      if (controller !== current) return
      timing.active = data.active
      timing.stale = data.stale
      timing.updated = data.updated
      if (full) Object.assign(timing, { session: data.session, updated: data.updated, loaded: true })
    } catch {
      if (controller !== current) return
      timing.active = timing.updated > 0 && Date.now() / 1000 - timing.updated < 60
      timing.stale = timing.active
      if (full) {
        timing.loaded = true
        if (Date.now() / 1000 - timing.updated >= 60) timing.session = null
      }
    } finally {
      clearTimeout(timeout)
      if (controller === current && !document.hidden) timer = setTimeout(poll, full ? 2000 : 15000)
    }
  }

  onMounted(() => {
    stop = watch(() => route.path === '/live/ac', poll, { immediate: true })
    document.addEventListener('visibilitychange', poll)
  })
  onBeforeUnmount(() => {
    stop?.()
    clearTimeout(timer)
    controller?.abort()
    controller = null
    document.removeEventListener('visibilitychange', poll)
  })
}
