import { reactive } from 'vue'
import { api } from './api'

export const brandingSettings = reactive({
  light_logo_url: '/assets/bmrl-logo-light-cutout.png',
  dark_logo_url: '/assets/bmrl-logo-dark-cutout.png',
  default_avatar_url: '/assets/avatar-template.jpg',
  browser_title: __SITE_TITLE__,
  browser_description: __SITE_DESCRIPTION__,
  browser_icon_url: '/api/app-settings/branding/browser-icon'
})

let pendingLoad = null

function applyBrowserBranding() {
  if (typeof document === 'undefined') return
  document.title = brandingSettings.browser_title || __SITE_TITLE__
  let description = document.querySelector('meta[name="description"]')
  if (!description) {
    description = document.createElement('meta')
    description.name = 'description'
    document.head.appendChild(description)
  }
  description.content = brandingSettings.browser_description || ''
  let ogTitle = document.querySelector('meta[property="og:title"]')
  if (!ogTitle) {
    ogTitle = document.createElement('meta')
    ogTitle.setAttribute('property', 'og:title')
    document.head.appendChild(ogTitle)
  }
  ogTitle.content = brandingSettings.browser_title || __SITE_TITLE__
  let ogDescription = document.querySelector('meta[property="og:description"]')
  if (!ogDescription) {
    ogDescription = document.createElement('meta')
    ogDescription.setAttribute('property', 'og:description')
    document.head.appendChild(ogDescription)
  }
  ogDescription.content = brandingSettings.browser_description || ''
  let icon = document.querySelector('link[rel="icon"]')
  if (!icon) {
    icon = document.createElement('link')
    icon.rel = 'icon'
    document.head.appendChild(icon)
  }
  icon.href = brandingSettings.browser_icon_url || '/api/app-settings/branding/browser-icon'
}

export function setBrandingSettings(value = {}) {
  brandingSettings.light_logo_url = value.light_logo_url || brandingSettings.light_logo_url
  brandingSettings.dark_logo_url = value.dark_logo_url || brandingSettings.dark_logo_url
  brandingSettings.default_avatar_url = value.default_avatar_url || brandingSettings.default_avatar_url
  brandingSettings.browser_title = value.browser_title || brandingSettings.browser_title
  if (typeof value.browser_description === 'string') brandingSettings.browser_description = value.browser_description
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
