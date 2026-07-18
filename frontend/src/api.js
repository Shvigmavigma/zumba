import { clearSession, state } from './store'

export const API_BASE = import.meta.env.VITE_API_BASE || '/api'

export async function api(path, options = {}) {
  const headers = new Headers(options.headers || {})
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json')
  }
  if (state.token) {
    headers.set('Authorization', `Bearer ${state.token}`)
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    body: options.body && typeof options.body !== 'string' ? JSON.stringify(options.body) : options.body
  })

  if (response.status === 401) {
    clearSession()
  }
  if (!response.ok) {
    let message = response.statusText
    try {
      const data = await response.json()
      message = data.detail || message
    } catch {
      // Keep status text.
    }
    throw new Error(Array.isArray(message) ? message.map((item) => item.msg).join(', ') : message)
  }
  if (response.status === 204) return null
  return response.json()
}
