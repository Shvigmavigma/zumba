import { reactive } from 'vue'

const savedLocale = localStorage.getItem('locale')
const initialLocale = savedLocale === 'en' ? 'en' : 'ru'
const savedTimeZone = localStorage.getItem('timeZone')
const savedTimeZoneVersion = localStorage.getItem('timeZonePreferenceVersion')
const initialTimeZone = savedTimeZone && (savedTimeZone !== 'UTC' || savedTimeZoneVersion === '2')
  ? savedTimeZone
  : 'Europe/Moscow'

export const state = reactive({
  token: localStorage.getItem('token') || '',
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  theme: localStorage.getItem('theme') || 'light',
  locale: initialLocale,
  timeZone: initialTimeZone,
  licenseTiers: null,
  licenseTiersLoaded: false
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
