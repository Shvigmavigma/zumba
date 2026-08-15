import { api } from './api'
import { DEFAULT_LICENSE_TIERS, normalizeLicenseTiers } from './pilotDisplay'
import { state } from './store'

let pendingLicenseLoad = null

export function setLicenseTiers(data) {
  state.licenseTiers = normalizeLicenseTiers(data)
  state.licenseTiersLoaded = true
  return state.licenseTiers
}

export async function ensureLicenseSettings() {
  if (state.licenseTiersLoaded) return state.licenseTiers || DEFAULT_LICENSE_TIERS
  if (pendingLicenseLoad) return pendingLicenseLoad
  pendingLicenseLoad = api('/app-settings/licenses')
    .then(setLicenseTiers)
    .catch(() => setLicenseTiers(DEFAULT_LICENSE_TIERS))
    .finally(() => {
      pendingLicenseLoad = null
    })
  return pendingLicenseLoad
}
