import { clearSession, state } from './store'

export const API_BASE = import.meta.env.VITE_API_BASE || '/api'

function apiErrorMessage(message) {
  const text = Array.isArray(message) ? message.map((item) => item.msg).join(', ') : String(message || '')
  const locale = state.locale === 'en' ? 'en' : 'ru'
  const friendly = {
    'Pilot number is already taken in this race': {
      ru: 'Этот номер уже занят в этой гонке. Выберите другой номер.',
      en: 'This pilot number is already taken in this race. Choose another number.'
    },
    'Pilot number is already taken in this championship': {
      ru: 'Этот номер уже занят в этом чемпионате. Выберите другой номер.',
      en: 'This pilot number is already taken in this championship. Choose another number.'
    },
    'Car is required': {
      ru: 'Выберите машину для заявки.',
      en: 'Choose a car for the application.'
    },
    'Car is not allowed': {
      ru: 'Эта машина недоступна для выбранного класса чемпионата.',
      en: 'This car is not available for the selected championship class.'
    }
  }
  return friendly[text]?.[locale] || text
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {})
  const isFormData = options.body instanceof FormData
  if (!headers.has('Content-Type') && options.body && !isFormData) {
    headers.set('Content-Type', 'application/json')
  }
  if (state.token) {
    headers.set('Authorization', `Bearer ${state.token}`)
  }

  return fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    body: options.body && typeof options.body !== 'string' && !isFormData ? JSON.stringify(options.body) : options.body
  })
}

async function ensureOk(response) {
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
    throw new Error(apiErrorMessage(message))
  }
}

export async function api(path, options = {}) {
  const response = await request(path, options)
  await ensureOk(response)
  if (response.status === 204) return null
  return response.json()
}

export async function apiDownload(path, options = {}) {
  const response = await request(path, options)
  await ensureOk(response)
  return response.blob()
}
