// Admin force-registration: candidate search (debounced), defaults for the
// chosen pilot and the POST that registers them. Behaviour unchanged from the
// original race page.
import { onBeforeUnmount, ref, watch } from 'vue'
import { api } from '../../api'
import { state } from '../../store'
import { pilotNumberDraft } from './raceFormat'

const SEARCH_DELAY_MS = 240

/**
 * @param {object} options
 * @param {import('vue').Ref<object|null>} options.race
 * @param {import('vue').ComputedRef<boolean>} options.canForce
 * @param {import('vue').Ref<string>} options.error
 * @param {import('vue').Ref<boolean>} options.actionPending
 * @param {(value: string) => number} options.parsePilotNumber
 * @param {Function} options.t
 */
export function useForceRegistration({ race, canForce, error, actionPending, parsePilotNumber, t }) {
  const forcePilotId = ref('')
  const forcePilotNumber = ref('')
  const forcePilotCar = ref('')
  const forcePilotCandidates = ref([])
  const forcePilotLoading = ref(false)
  const forcePilotSearch = ref('')
  let searchTimer = null
  let searchRequest = 0

  function updateForcePilotDefaults() {
    const pilot = forcePilotCandidates.value.find((item) => Number(item.id) === Number(forcePilotId.value)) || null
    forcePilotNumber.value = pilot ? pilotNumberDraft(pilot.pilot_number) : ''
    forcePilotCar.value = race.value?.allowed_cars?.[0] || ''
  }

  async function loadForcePilotCandidates(currentRace, search = forcePilotSearch.value) {
    const requestId = ++searchRequest
    forcePilotCandidates.value = []
    forcePilotId.value = ''
    forcePilotNumber.value = ''
    forcePilotCar.value = currentRace?.allowed_cars?.[0] || ''
    if (state.user?.role !== 'admin' || currentRace?.is_team_event || ['ongoing', 'finished'].includes(currentRace?.status)) return
    forcePilotLoading.value = true
    try {
      const params = new URLSearchParams({ limit: '100', rating_game: currentRace.game || 'ACC' })
      if (String(search || '').trim()) params.set('search', String(search).trim())
      const candidates = await api(`/users/pilots?${params.toString()}`)
      if (requestId === searchRequest) forcePilotCandidates.value = candidates
    } catch {
      // An empty candidate list (the count chip shows 0) is the visible state.
      if (requestId === searchRequest) forcePilotCandidates.value = []
    } finally {
      if (requestId === searchRequest) forcePilotLoading.value = false
    }
  }

  async function forceRegisterPilot() {
    if (!race.value || !canForce.value) return
    error.value = ''
    actionPending.value = true
    try {
      if (!forcePilotId.value) throw new Error(t('raceDetails.forceRegistrationPilotRequired'))
      const raceId = race.value.id
      await api(`/races/${raceId}/registrations/${Number(forcePilotId.value)}`, {
        method: 'POST',
        body: {
          car_model: forcePilotCar.value || race.value.allowed_cars?.[0] || 'TBD',
          pilot_number: parsePilotNumber(forcePilotNumber.value)
        }
      })
      // Refresh the race payload so the participant list updates immediately,
      // even when a proxy serves a response without the expanded registrations.
      race.value = await api(`/races/${raceId}`)
      forcePilotId.value = ''
      forcePilotNumber.value = ''
    } catch (err) {
      error.value = err.message
    } finally {
      actionPending.value = false
    }
  }

  watch(forcePilotSearch, () => {
    if (searchTimer) clearTimeout(searchTimer)
    if (!race.value || !canForce.value) return
    searchTimer = setTimeout(() => {
      loadForcePilotCandidates(race.value, forcePilotSearch.value)
    }, SEARCH_DELAY_MS)
  })

  onBeforeUnmount(() => {
    if (searchTimer) clearTimeout(searchTimer)
  })

  return {
    forcePilotId,
    forcePilotNumber,
    forcePilotCar,
    forcePilotCandidates,
    forcePilotLoading,
    forcePilotSearch,
    updateForcePilotDefaults,
    loadForcePilotCandidates,
    forceRegisterPilot
  }
}
