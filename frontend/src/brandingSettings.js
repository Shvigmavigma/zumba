import { reactive } from 'vue'
import { api } from './api'

export const brandingSettings = reactive({
  light_logo_url: '/assets/bmrl-logo-light-cutout.png',
  dark_logo_url: '/assets/bmrl-logo-dark-cutout.png',
  default_avatar_url: '/assets/avatar-template.jpg',
  browser_title: 'BMRL Race Control',
  browser_icon_url: '/assets/bmrl-logo-light-cutout.png'
})

let pendingLoad = null

function applyBrowserBranding() {
  if (typeof document === 'undefined') return
  document.title = brandingSettings.browser_title || 'BMRL Race Control'
  let icon = document.querySelector('link[rel="icon"]')
  if (!icon) {
    icon = document.createElement('link')
    icon.rel = 'icon'
    document.head.appendChild(icon)
  }
  icon.href = brandingSettings.browser_icon_url || brandingSettings.light_logo_url
}

export function setBrandingSettings(value = {}) {
  brandingSettings.light_logo_url = value.light_logo_url || brandingSettings.light_logo_url
  brandingSettings.dark_logo_url = value.dark_logo_url || brandingSettings.dark_logo_url
  brandingSettings.default_avatar_url = value.default_avatar_url || brandingSettings.default_avatar_url
  brandingSettings.browser_title = value.browser_title || brandingSettings.browser_title
  brandingSettings.browser_icon_url = value.browser_icon_url || brandingSettings.browser_icon_url
  applyBrowserBranding()
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

applyBrowserBranding()
