import { clearSession, state } from './store'

export const API_BASE = import.meta.env.VITE_API_BASE || '/api'
const TRANSIENT_RETRY_DELAY_MS = 350

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
    },
    'A team can have at most 4 livery images': {
      ru: 'У команды может быть максимум 4 изображения ливреи.',
      en: 'A team can have at most 4 livery images.'
    },
    'Choose a livery folder': {
      ru: 'Выберите папку с ливреей.',
      en: 'Choose a livery folder.'
    },
    'Choose one .json file from the ACC Cars folder': {
      ru: 'Выберите один .json-файл из папки Cars.',
      en: 'Choose one .json file from the ACC Cars folder.'
    },
    'Car file must be a valid ACC JSON file': {
      ru: 'Файл автомобиля должен содержать корректный JSON из ACC.',
      en: 'The car file must be a valid ACC JSON file.'
    },
    'Car JSON must contain a valid customSkinName folder name': {
      ru: 'В JSON автомобиля должно быть корректное имя папки customSkinName.',
      en: 'The car JSON must contain a valid customSkinName folder name.'
    },
    'Car JSON file is empty': {
      ru: 'Файл JSON пуст.',
      en: 'The car JSON file is empty.'
    },
    'Car JSON file is larger than 5 MB': {
      ru: 'Файл JSON больше 5 МБ.',
      en: 'The car JSON file is larger than 5 MB.'
    },
    'Choose the complete livery folder': {
      ru: 'Выберите всю папку ливреи целиком.',
      en: 'Choose the complete livery folder.'
    },
    'Select the complete livery folder, not individual files': {
      ru: 'Выберите всю папку ливреи, а не отдельные файлы.',
      en: 'Select the complete livery folder, not individual files.'
    },
    'Only PNG, JPG, WEBP and GIF livery images are allowed': {
      ru: 'Для скриншотов подходят PNG, JPG, WEBP и GIF.',
      en: 'Only PNG, JPG, WEBP and GIF livery images are allowed.'
    },
    'Preview file content does not match its image type': {
      ru: 'Формат файла скриншота не совпадает с его содержимым.',
      en: 'The preview file content does not match its image type.'
    },
    'A livery can have at most 4 preview images': {
      ru: 'Можно добавить не более 4 скриншотов ливреи.',
      en: 'A livery can have at most 4 preview images.'
    },
    'Livery archive is larger than 500 MB': {
      ru: 'Архив ливреи больше 500 МБ.',
      en: 'The livery archive is larger than 500 MB.'
    },
    'No team livery archives are available': {
      ru: 'Актуальных архивов ливрей пока нет.',
      en: 'No team livery archives are available.'
    },
  }
  const folderMismatch = text.match(/^Livery folder must be named exactly '(.+)', as specified by customSkinName in the car JSON$/)
  if (folderMismatch) {
    return locale === 'en'
      ? `The folder must be named exactly "${folderMismatch[1]}" to match customSkinName in the car JSON.`
      : `Папка должна называться точно «${folderMismatch[1]}», как указано в customSkinName в JSON.`
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

function canRetry(options) {
  return !options.method || options.method.toUpperCase() === 'GET'
}

function isTransientResponse(response) {
  return response.status === 408 || response.status === 429 || response.status >= 500
}

function waitForRetry() {
  return new Promise((resolve) => globalThis.setTimeout(resolve, TRANSIENT_RETRY_DELAY_MS))
}

async function requestWithRetry(path, options = {}) {
  const retryOnce = canRetry(options)

  for (let attempt = 0; attempt <= Number(retryOnce); attempt += 1) {
    try {
      const response = await request(path, options)
      if (attempt === 0 && retryOnce && isTransientResponse(response)) {
        await waitForRetry()
        continue
      }
      return response
    } catch (error) {
      if (attempt === 0 && retryOnce) {
        await waitForRetry()
        continue
      }
      throw error
    }
  }
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
  const response = await requestWithRetry(path, options)
  await ensureOk(response)
  if (response.status === 204) return null
  return response.json()
}

export async function apiDownload(path, options = {}) {
  const response = await requestWithRetry(path, options)
  await ensureOk(response)
  return response.blob()
}
