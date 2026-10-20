import { computed, onMounted } from 'vue'
import { ensureLicenseSettings } from './licenseSettings'
import { DEFAULT_LICENSE_TIERS } from './pilotDisplay'
import { finishOf, finishOfRating } from './ranks'
import { state } from './store'

/**
 * Pilot finishes for lists: the admin's licence tiers (loaded once per
 * session) and lookups of the key that RankAura, .rank-surface, .rank-avatar
 * and .rank-name take. That key is the pilot's overall rank, except for the
 * season champion, who has a finish of their own ('season').
 */
export function useRanks() {
  const tiers = computed(() => state.licenseTiers || DEFAULT_LICENSE_TIERS)
  onMounted(ensureLicenseSettings)
  return {
    tiers,
    rankOf: (user) => finishOf(user, tiers.value),
    /** For result rows: the rating in that race plus the pilot's roles. */
    rankOfRating: (rating, roles) => finishOfRating(rating, roles, tiers.value)
  }
}
