// Draft rows for the staff manual-results form. Rows are prefilled from the
// stored result (so a saved manual result can be reopened and replaced); LMU
// races add drivers through a pilot search instead of the registration list.
import { ref, watch } from 'vue'
import { api } from '../../api'
import { formatDuration } from './raceFormat'

/** What a row says about the pilot's laps beyond the form's fields (sector times, the stewards' annulment); sent back as it is. */
const TIMING_FIELDS = ['best_sectors_ms', 'valid_laps', 'qualification_best_sectors_ms', 'qualification_valid_laps', 'laps_annulled']

function rowTiming(source) {
  return Object.fromEntries(TIMING_FIELDS.filter((field) => source[field] !== null && source[field] !== undefined).map((field) => [field, source[field]]))
}

/**
 * @param {object} options
 * @param {import('vue').ComputedRef<boolean>} options.isLmuRace
 * @param {import('vue').ComputedRef<object[]>} options.resultRows
 * @param {import('vue').ComputedRef<object[]>} options.resultParticipants
 * @param {import('vue').ComputedRef<object[]>} options.participants
 * @param {import('vue').ComputedRef<string>} options.raceRatingGame
 * @param {(item: object) => string} options.participantName
 * @param {import('vue').Ref<string>} options.error
 */
export function useManualResults({ isLmuRace, resultRows, resultParticipants, participants, raceRatingGame, participantName, error }) {
  const manualRows = ref([])
  const manualPilotSearch = ref('')
  const manualPilotResults = ref([])
  const manualPilotLoading = ref(false)

  function manualRowFromPilot(item, existing = {}) {
    const userId = item.user_id ?? item.id
    const pilot = { ...item, user_id: userId }
    return {
      user_id: userId,
      label: participantName(pilot),
      rating: pilot.rating,
      game_ratings: pilot.game_ratings,
      qualification_best_lap_time: existing.qualification_best_lap_ms ? formatDuration(existing.qualification_best_lap_ms) : '',
      finish_time: existing.finish_ms ? formatDuration(existing.finish_ms) : '',
      lap_count: existing.lap_count || 0,
      best_lap_time: existing.best_lap_ms ? formatDuration(existing.best_lap_ms) : '',
      ...rowTiming(existing)
    }
  }

  function fillManualRows() {
    const existingRows = new Map(resultRows.value.filter((item) => item.user_id).map((item) => [item.user_id, item]))
    const source = isLmuRace.value ? resultParticipants.value : participants.value
    manualRows.value = source.map((item) => manualRowFromPilot(item, existingRows.get(item.user_id) || {}))
  }

  async function searchManualPilots() {
    if (!manualPilotSearch.value.trim()) {
      manualPilotResults.value = []
      return
    }
    manualPilotLoading.value = true
    try {
      const params = new URLSearchParams({ search: manualPilotSearch.value, limit: '12', rating_game: raceRatingGame.value })
      manualPilotResults.value = await api(`/users/pilots?${params.toString()}`)
    } catch (err) {
      error.value = err.message
    } finally {
      manualPilotLoading.value = false
    }
  }

  function addManualPilot(pilot) {
    const userId = pilot.user_id ?? pilot.id
    if (!userId || manualRows.value.some((row) => row.user_id === userId)) return
    manualRows.value = [...manualRows.value, manualRowFromPilot({ ...pilot, user_id: userId })]
  }

  function removeManualRow(userId) {
    manualRows.value = manualRows.value.filter((row) => row.user_id !== userId)
  }

  function updateManualRow(userId, field, value) {
    manualRows.value = manualRows.value.map((row) => (row.user_id === userId ? { ...row, [field]: value } : row))
  }

  /**
   * The filled rows as the results endpoint takes them.
   * @param {{ withQualification: boolean, parseDuration: (value: string, required: boolean) => number | null }} options
   */
  function manualPayloadRows({ withQualification, parseDuration }) {
    return manualRows.value
      .filter((row) => String(row.finish_time || '').trim())
      .map((row) => ({
        user_id: row.user_id,
        qualification_best_lap_ms: withQualification ? parseDuration(row.qualification_best_lap_time, false) : null,
        finish_ms: parseDuration(row.finish_time, true),
        lap_count: Number(row.lap_count || 0),
        best_lap_ms: parseDuration(row.best_lap_time, false),
        ...rowTiming(row)
      }))
  }

  watch(manualPilotSearch, () => {
    if (manualPilotSearch.value.trim().length >= 1) searchManualPilots()
    else manualPilotResults.value = []
  })

  return {
    manualRows,
    manualPilotSearch,
    manualPilotResults,
    manualPilotLoading,
    fillManualRows,
    addManualPilot,
    removeManualRow,
    updateManualRow,
    manualPayloadRows
  }
}
