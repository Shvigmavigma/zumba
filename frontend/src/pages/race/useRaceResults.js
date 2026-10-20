// Result rows for the race page: race classification, qualification (stored
// manual laps or the raw ACC leaderboard), and display-ready rows for the
// podium and the timing table. Pilots outside the rating are not classified
// (raceClassification.js).
import { computed, watch } from 'vue'
import { formatPilotNumber, formatRating, pilotFirstName, pilotSurname, ratingForGame, teamShortName } from '../../pilotDisplay'
import { state } from '../../store'
import { accLineHasActivity, classifiedRows, lapsAnnulled, qualificationOrder } from './raceClassification'
import {
  accDriverName,
  accLineDriver,
  accPlayerId,
  formatDuration,
  isAccMaxTime,
  normalizeAccPlayerId,
  numberLabel,
  personName,
  resultBestLapMs,
  resultFinishMs,
  resultQualificationBestLapMs,
  timeLabel,
  validTimeMs
} from './raceFormat'

/**
 * @param {object} options
 * @param {import('vue').Ref<object|null>} options.race
 * @param {import('vue').ComputedRef<object[]>} options.participants
 * @param {import('vue').Ref<object[]>} options.penalties
 * @param {import('vue').Ref<object>} options.raceAssets
 * @param {import('vue').Ref<string>} options.resultsTab
 * @param {Function} options.t
 */
export function useRaceResults({ race, participants, penalties, raceAssets, resultsTab, t }) {
  const raceRatingGame = computed(() => race.value?.game || 'ACC')

  function participantName(item) {
    return personName(item, `${t('roles.pilot')} ${item.user_id}`)
  }

  function participantSubtitle(item) {
    const number = numberLabel(item)
    return item.nickname ? `${number} - ${item.nickname}` : number
  }

  /** Every stored row, including pilots outside the rating: used to match ACC lines to pilots. */
  const storedRows = computed(() => {
    if (Array.isArray(race.value?.results)) return race.value.results
    return race.value?.results?.rows || []
  })

  const resultRows = computed(() => classifiedRows(storedRows.value, participants.value))

  const resultParticipants = computed(() => {
    const seen = new Set()
    return resultRows.value
      .filter((row) => row.user_id && !seen.has(row.user_id) && seen.add(row.user_id))
      .map((row) => {
        const participant = participants.value.find((item) => item.user_id === row.user_id)
        return {
          user_id: row.user_id,
          login: row.login || participant?.login,
          nickname: row.nickname || participant?.nickname,
          first_name: row.first_name || participant?.first_name || '',
          last_name: row.last_name || participant?.last_name || '',
          pilot_number: row.pilot_number ?? row.race_number ?? participant?.pilot_number,
          avatar_color: row.avatar_color || participant?.avatar_color || '#2563eb',
          avatar_url: row.avatar_url || participant?.avatar_url || '',
          rating: row.rating ?? participant?.rating,
          game_ratings: row.game_ratings || participant?.game_ratings,
          exclude_from_rer: participant?.exclude_from_rer ?? row.exclude_from_rer ?? false,
          sr: row.sr ?? participant?.sr,
          car_model: row.car_model ?? participant?.car_model,
          team_id: row.team_id || participant?.team_id,
          team_name: row.team_name || participant?.team_name,
          team_abbreviation: row.team_abbreviation || participant?.team_abbreviation,
          country: row.country || participant?.country,
          pilot_roles: row.pilot_roles || participant?.pilot_roles || []
        }
      })
  })

  const penaltyParticipants = computed(() => (resultParticipants.value.length ? resultParticipants.value : participants.value))

  const raceRowsByPlayer = computed(() => {
    const rows = new Map()
    storedRows.value.forEach((row) => {
      const key = normalizeAccPlayerId(row.player_id)
      if (key) rows.set(key, row)
    })
    return rows
  })

  const raceRowsByNumber = computed(() => {
    const rows = new Map()
    storedRows.value.forEach((row) => {
      const key = Number(row.race_number)
      if (Number.isFinite(key)) rows.set(key, row)
    })
    return rows
  })

  function manualQualificationRows() {
    const rows = qualificationOrder(resultRows.value)
      // Renumbered: a pilot outside the rating may have left a hole in the stored order.
      .map((row, index) => ({ ...row, position: index + 1, best_lap_ms: row.qualification_best_lap_ms, source: 'qualification' }))
    const leaderLap = rows[0]?.best_lap_ms
    return rows.map((row) => ({ ...row, gap_ms: Number(row.best_lap_ms) - Number(leaderLap) }))
  }

  function accQualificationRow(line, index) {
    const driver = accLineDriver(line)
    const normalized = normalizeAccPlayerId(accPlayerId(driver.playerId || driver.playerID))
    // Steam/player IDs are intentionally redacted from the browser response.
    // ACC race numbers provide the safe fallback link to the stored result.
    const raceNumber = Number(line.car?.raceNumber)
    const raceRow = raceRowsByPlayer.value.get(normalized) || raceRowsByNumber.value.get(raceNumber)
    const participant = raceRow?.user_id
      ? participants.value.find((item) => item.user_id === raceRow.user_id)
      : participants.value.find((item) => Number(item.pilot_number) === raceNumber)
    const timing = line.timing || {}
    return {
      position: index + 1,
      user_id: participant?.user_id || raceRow?.user_id || null,
      login: participant?.login || raceRow?.login || null,
      nickname: participant?.nickname || raceRow?.nickname || null,
      avatar_color: participant?.avatar_color || raceRow?.avatar_color || '#2563eb',
      avatar_url: participant?.avatar_url || raceRow?.avatar_url || '',
      rating: participant?.rating ?? raceRow?.rating,
      exclude_from_rer: participant?.exclude_from_rer ?? raceRow?.exclude_from_rer ?? false,
      sr: participant?.sr ?? raceRow?.sr,
      team_id: participant?.team_id || raceRow?.team_id,
      team_name: participant?.team_name || raceRow?.team_name,
      team_abbreviation: participant?.team_abbreviation || raceRow?.team_abbreviation,
      driver_name: accDriverName(driver),
      player_id: null,
      race_number: line.car?.raceNumber ?? raceRow?.race_number ?? null,
      car_model: line.car?.carModel ?? line.carModel ?? line.forcedCarModel ?? raceRow?.car_model ?? null,
      lap_count: timing.lapCount ?? null,
      best_lap_ms: timing.bestLap,
      source: 'qualification'
    }
  }

  const qualificationRows = computed(() => {
    const lines = race.value?.results?.qualification?.raw?.sessionResult?.leaderBoardLines
    if (!Array.isArray(lines)) return manualQualificationRows()
    const mapped = classifiedRows(lines.filter(accLineHasActivity).map(accQualificationRow), participants.value)
    const leaderLap = mapped.find((row) => Number.isFinite(Number(row.best_lap_ms)))?.best_lap_ms
    return mapped.map((row) => ({
      ...row,
      gap_ms: Number.isFinite(Number(row.best_lap_ms)) && Number.isFinite(Number(leaderLap)) ? Number(row.best_lap_ms) - Number(leaderLap) : null
    }))
  })

  const activeResultRows = computed(() => (resultsTab.value === 'qualification' ? qualificationRows.value : resultRows.value))

  const resultTabOptions = computed(() => [
    { value: 'race', label: t('raceDetails.raceResultsTab'), count: resultRows.value.length },
    // LMU sends one combined result: there is no separate qualification to show.
    ...(qualificationRows.value.length && race.value?.game !== 'LMU' ? [{ value: 'qualification', label: t('raceDetails.qualificationResultsTab'), count: qualificationRows.value.length }] : [])
  ])

  // Keep the open tab one that exists; when only qualification is in so far,
  // open it instead of an empty race tab.
  watch([resultTabOptions, resultRows], ([options, rows]) => {
    const hasQualification = options.some((option) => option.value === 'qualification')
    if (!rows.length && hasQualification) resultsTab.value = 'qualification'
    else if (!options.some((option) => option.value === resultsTab.value)) resultsTab.value = 'race'
  }, { immediate: true })

  /** Everyone who registered or appears in the results (fan vote candidates, name lookups). */
  const knownPilots = computed(() => {
    const candidates = new Map()
    for (const item of participants.value) {
      const id = Number(item.user_id)
      if (Number.isInteger(id) && id > 0) candidates.set(id, item)
    }
    for (const item of resultParticipants.value) {
      const id = Number(item.user_id)
      if (Number.isInteger(id) && id > 0 && !candidates.has(id)) candidates.set(id, item)
    }
    return [...candidates.values()]
  })

  function participantById(userId) {
    return knownPilots.value.find((item) => item.user_id === userId)
  }

  function resultIsDidNotFinish(row, value) {
    return Boolean(race.value?.game === 'ACC' && (isAccMaxTime(value) || row?.status === 'missing' || row?.status === 'dnf'))
  }

  function resultTimeLabel(row, value) {
    if (resultIsDidNotFinish(row, value)) return t('raceDetails.didNotFinish')
    return timeLabel(value)
  }

  function resultPilotName(row) {
    const participant = participantById(row.user_id)
    if (participant) return participantName(participant)
    return row.driver_name || row.nickname || row.login || `${t('roles.pilot')} ${row.user_id || ''}`.trim()
  }

  function resultPilotSubtitle(row) {
    const participant = participantById(row.user_id)
    if (participant) return participantSubtitle(participant)
    const number = row.race_number ?? row.pilot_number
    if (number !== null && number !== undefined) return `#${formatPilotNumber(number)}`
    return row.player_id || '-'
  }

  function resultPilotRatingValue(row) {
    const participant = participantById(row.user_id)
    return row.rating_new ?? ratingForGame(participant, raceRatingGame.value) ?? ratingForGame(row, raceRatingGame.value)
  }

  function resultPilotId(row) {
    const userId = Number(row?.user_id)
    return Number.isInteger(userId) && userId > 0 ? userId : null
  }

  function carModelLabel(value) {
    if (value === null || value === undefined || value === '') return t('common.none')
    if (race.value?.game !== 'ACC') return String(value)
    const numericId = Number(value)
    if (!Number.isInteger(numericId)) return String(value)
    const mapping = raceAssets.value.car_model_ids || {}
    return Object.entries(mapping).find(([, id]) => Number(id) === numericId)?.[0] || String(value)
  }

  function ratingDelta(row) {
    const delta = Number(row.rating_delta ?? 0)
    if (!Number.isFinite(delta)) return { label: '-', tone: 'flat' }
    const rounded = Math.round(delta)
    return { label: `${rounded > 0 ? '+' : ''}${rounded}`, tone: delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat' }
  }

  function resultGap(row) {
    if (resultIsDidNotFinish(row, resultFinishMs(row))) return t('raceDetails.didNotFinish')
    if (row.gap_ms === 0) return t('raceDetails.leaderGap')
    const gap = validTimeMs(row.gap_ms)
    return gap === null ? '-' : `+${formatDuration(gap)}`
  }

  /** Fastest valid lap among the given rows (purple sector, broadcast style). */
  function fastestLapOf(rows) {
    return rows.reduce((best, row) => {
      const lap = lapsAnnulled(row) ? null : validTimeMs(resultBestLapMs(row))
      return lap !== null && (best === null || lap < best) ? lap : best
    }, null)
  }

  function viewRow(row, index, fastestMs) {
    const participant = participantById(row.user_id)
    const delta = ratingDelta(row)
    const timePenaltyMs = Number(row.time_penalty_ms || 0)
    const srPenalty = Number(row.sr_penalty || 0)
    const bestLapMs = lapsAnnulled(row) ? null : validTimeMs(resultBestLapMs(row))
    const bestLap = resultTimeLabel(row, resultBestLapMs(row))
    const finish = resultTimeLabel(row, resultFinishMs(row))
    return {
      key: `${resultsTab.value}-${row.user_id || row.player_id || row.raw_position}-${row.position}-${index}`,
      raw: row,
      position: row.position || '-',
      place: Number(row.position),
      pilotId: resultPilotId(row),
      name: resultPilotName(row),
      subtitle: resultPilotSubtitle(row),
      avatar: participant?.avatar_url || row.avatar_url || '',
      color: participant?.avatar_color || row.avatar_color || '#2563eb',
      roles: participant?.pilot_roles || row.pilot_roles || participants.value.find((item) => item.user_id === row.user_id)?.pilot_roles || [],
      ratingValue: resultPilotRatingValue(row),
      rating: formatRating(resultPilotRatingValue(row)),
      team: teamShortName(participant?.team_name || row.team_name, participant?.team_abbreviation || row.team_abbreviation),
      teamId: participant?.team_id || row.team_id || null,
      laps: row.lap_count ?? '-',
      car: carModelLabel(row.car_model),
      bestLap,
      isFastest: bestLapMs !== null && bestLapMs === fastestMs,
      lapsAnnulled: lapsAnnulled(row),
      qualiLap: resultTimeLabel(row, resultQualificationBestLapMs(row)),
      hasQualiLap: validTimeMs(resultQualificationBestLapMs(row)) !== null,
      finish,
      mainTime: resultsTab.value === 'qualification' ? bestLap : finish,
      hasTimePenalty: timePenaltyMs > 0,
      timePenalty: timePenaltyMs > 0 ? `+${formatDuration(timePenaltyMs)}` : '-',
      hasSrPenalty: srPenalty > 0,
      srPenalty: srPenalty > 0 ? `-${srPenalty.toFixed(1)} SR` : '-',
      adjusted: resultTimeLabel(row, row.adjusted_finish_ms ?? row.finish_ms),
      delta: delta.label,
      deltaTone: delta.tone,
      gap: resultGap(row),
      isDnf: resultIsDidNotFinish(row, resultFinishMs(row)),
      isMe: Boolean(state.user) && Number(row.user_id) === Number(state.user.id)
    }
  }

  const resultView = computed(() => {
    const fastestMs = fastestLapOf(activeResultRows.value)
    return activeResultRows.value.map((row, index) => viewRow(row, index, fastestMs))
  })

  /** Winner and fastest lap of the race classification, for the hero. */
  const raceSummary = computed(() => {
    const rows = resultRows.value
    if (!rows.length) return { winner: null, fastest: null, finishers: 0 }
    const first = rows.find((row) => Number(row.position) === 1) || rows[0]
    const fastestMs = fastestLapOf(rows)
    const fastestRow = fastestMs === null ? null : rows.find((row) => !lapsAnnulled(row) && validTimeMs(resultBestLapMs(row)) === fastestMs)
    return {
      winner: {
        name: resultPilotName(first),
        firstName: pilotFirstName(resultPilotName(first), participantById(first.user_id), first),
        surname: pilotSurname(resultPilotName(first), participantById(first.user_id), first),
        time: resultTimeLabel(first, resultFinishMs(first)),
        pilotId: resultPilotId(first)
      },
      fastest: fastestRow ? { name: resultPilotName(fastestRow), time: formatDuration(fastestMs), pilotId: resultPilotId(fastestRow) } : null,
      finishers: rows.filter((row) => !resultIsDidNotFinish(row, resultFinishMs(row))).length
    }
  })

  function resultPenaltyId(row) {
    const targetId = Number(row.user_id)
    if (!Number.isFinite(targetId)) return null
    return penalties.value.find((penalty) => Number(penalty.target_id) === targetId && penalty.status !== 'canceled')?.id || null
  }

  return {
    raceRatingGame,
    participantName,
    participantSubtitle,
    resultRows,
    resultParticipants,
    penaltyParticipants,
    qualificationRows,
    activeResultRows,
    resultTabOptions,
    knownPilots,
    resultView,
    raceSummary,
    resultPenaltyId
  }
}
