import { reactive } from 'vue'

const savedLocale = localStorage.getItem('locale')
const initialLocale = savedLocale === 'en' ? 'en' : 'ru'
const savedTimeZone = localStorage.getItem('timeZone')

export const state = reactive({
  token: localStorage.getItem('token') || '',
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  theme: localStorage.getItem('theme') || 'light',
  locale: initialLocale,
  timeZone: savedTimeZone || 'UTC'
})

export function setSession(token, user) {
  state.token = token
  state.user = user
  localStorage.setItem('token', token)
  localStorage.setItem('user', JSON.stringify(user))
}

export function clearSession() {
  state.token = ''
  state.user = null
  localStorage.removeItem('token')
  localStorage.removeItem('user')
}
