// Fan favourite vote: the staff pick three nominees after the finish, viewers
// cast one vote each. Behaviour unchanged from the original race page.
import { computed, ref } from 'vue'
import { api } from '../../api'

/**
 * @param {object} options
 * @param {import('vue').Ref<object|null>} options.race
 * @param {import('vue').ComputedRef<boolean>} options.canManageRace
 * @param {import('vue').ComputedRef<object[]>} options.candidates registered and classified pilots
 * @param {import('vue').Ref<string>} options.error
 */
export function useFanVote({ race, canManageRace, candidates, error }) {
  const fanVote = ref(null)
  const fanVoteSelection = ref([])
  const fanVoteSaving = ref(false)
  const fanVoteVoting = ref(false)

  const fanVoteCanSetup = computed(() => canManageRace.value && race.value?.status === 'finished' && candidates.value.length >= 3)
  const fanVoteCanSaveSetup = computed(() => fanVoteCanSetup.value && fanVoteSelection.value.length === 3 && !fanVoteSaving.value)

  function toggleFanVoteCandidate(userId) {
    const id = Number(userId)
    if (fanVoteSelection.value.includes(id)) {
      fanVoteSelection.value = fanVoteSelection.value.filter((item) => item !== id)
    } else if (fanVoteSelection.value.length < 3) {
      fanVoteSelection.value = [...fanVoteSelection.value, id]
    }
  }

  function syncFanVoteSelection() {
    if (fanVote.value?.options?.length) {
      fanVoteSelection.value = fanVote.value.options.map((option) => option.user_id).slice(0, 3)
      return
    }
    const participantIds = new Set(candidates.value.map((item) => item.user_id))
    fanVoteSelection.value = fanVoteSelection.value.filter((item) => participantIds.has(item)).slice(0, 3)
  }

  async function refreshFanVote() {
    if (!race.value) return
    fanVote.value = await api(`/races/${race.value.id}/fan-vote`)
    syncFanVoteSelection()
  }

  async function setupFanVote() {
    if (!race.value || fanVoteSelection.value.length !== 3) return
    error.value = ''
    fanVoteSaving.value = true
    try {
      fanVote.value = await api(`/races/${race.value.id}/fan-vote`, { method: 'PATCH', body: { option_user_ids: fanVoteSelection.value } })
      syncFanVoteSelection()
    } catch (err) {
      error.value = err.message
    } finally {
      fanVoteSaving.value = false
    }
  }

  async function castFanVote(targetUserId) {
    if (!race.value || !fanVote.value?.is_open) return
    error.value = ''
    fanVoteVoting.value = true
    try {
      fanVote.value = await api(`/races/${race.value.id}/fan-vote`, { method: 'POST', body: { target_user_id: targetUserId } })
      syncFanVoteSelection()
    } catch (err) {
      error.value = err.message
    } finally {
      fanVoteVoting.value = false
    }
  }

  return {
    fanVote,
    fanVoteSelection,
    fanVoteVoting,
    fanVoteCanSetup,
    fanVoteCanSaveSetup,
    toggleFanVoteCandidate,
    syncFanVoteSelection,
    refreshFanVote,
    setupFanVote,
    castFanVote
  }
}
