import { reactive } from 'vue'
import { api } from './api'

export const brandingSettings = reactive({
  light_logo_url: '/assets/bmrl-logo-light-cutout.png',
  dark_logo_url: '/assets/bmrl-logo-dark-cutout.png',
  default_avatar_url: '/assets/avatar-template.jpg'
})

let pendingLoad = null

export function setBrandingSettings(value = {}) {
  brandingSettings.light_logo_url = value.light_logo_url || brandingSettings.light_logo_url
  brandingSettings.dark_logo_url = value.dark_logo_url || brandingSettings.dark_logo_url
  brandingSettings.default_avatar_url = value.default_avatar_url || brandingSettings.default_avatar_url
  return brandingSettings
}

export function ensureBrandingSettings() {
  if (!pendingLoad) {
    pendingLoad = api('/app-settings/branding').then(setBrandingSettings).finally(() => {
      pendingLoad = null
    })
  }
  return pendingLoad
}
