import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { readFileSync } from 'node:fs'

const brandingConfig = new URL('../branding/site.env', import.meta.url)

function readBrandingConfig() {
  return Object.fromEntries(readFileSync(brandingConfig, 'utf8')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith('#'))
    .map((line) => {
      const separator = line.indexOf('=')
      if (separator < 0) return null
      const key = line.slice(0, separator).trim()
      let value = line.slice(separator + 1).trim()
      if (value.startsWith('"')) {
        try { value = JSON.parse(value) } catch { /* Keep plain text if an edited value is malformed. */ }
      } else if (value.startsWith("'") && value.endsWith("'")) {
        value = value.slice(1, -1)
      }
      return [key, value]
    })
    .filter(Boolean))
}

function escapeHtml(value) {
  return String(value).replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
}

const siteBranding = readBrandingConfig()
const siteTitle = (siteBranding.SITE_TITLE || 'BMRL - BeamMP Racing League').slice(0, 120)
const siteDescription = (siteBranding.SITE_DESCRIPTION || '').slice(0, 320)

export default defineConfig({
  define: {
    __SITE_TITLE__: JSON.stringify(siteTitle),
    __SITE_DESCRIPTION__: JSON.stringify(siteDescription)
  },
  plugins: [vue(), {
    name: 'site-branding',
    transformIndexHtml(html) {
      return html
        .replaceAll('%SITE_TITLE%', escapeHtml(siteTitle))
        .replaceAll('%SITE_DESCRIPTION%', escapeHtml(siteDescription))
    }
  }],
  server: {
    port: 8080,
    proxy: {
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000'
    }
  }
})

