// Staff: fill the manual results form from an Assetto Corsa session file
// (Content Manager). The file's drivers are tied to the pilots of the grid —
// by name or number where that is certain, by a person otherwise — and each
// tied driver's laps, total time, best laps and sector times go into the
// pilot's row of the form. Nothing is sent anywhere until the form is saved.
import { computed, ref } from 'vue'
import { acRowTiming, matchAcDrivers, parseAcSession } from './acSessionResults'
import { formatDuration } from './raceFormat'

/** A session file is well under a megabyte; anything far bigger is not one. */
const MAX_FILE_BYTES = 20 * 1024 * 1024
/** What a row goes back to when its driver is untied. */
const EMPTY_ROW = {
  qualification_best_lap_time: '',
  finish_time: '',
  lap_count: 0,
  best_lap_time: '',
  best_sectors_ms: null,
  valid_laps: null,
  qualification_best_sectors_ms: null,
  qualification_valid_laps: null,
  ac_car: null
}

function rowValues(driver) {
  const timing = acRowTiming(driver)
  return {
    ...EMPTY_ROW,
    qualification_best_lap_time: timing.qualification_best_lap_ms ? formatDuration(timing.qualification_best_lap_ms) : '',
    finish_time: timing.finish_ms ? formatDuration(timing.finish_ms) : '',
    lap_count: timing.lap_count,
    best_lap_time: timing.best_lap_ms ? formatDuration(timing.best_lap_ms) : '',
    best_sectors_ms: timing.best_sectors_ms,
    valid_laps: timing.valid_laps,
    qualification_best_sectors_ms: timing.qualification_best_sectors_ms,
    qualification_valid_laps: timing.qualification_valid_laps,
    ac_car: driver.car
  }
}

/**
 * @param {object} options
 * @param {import('vue').Ref<object[]>} options.manualRows  rows of the manual results form
 * @param {import('vue').ComputedRef<object[]>} options.participants  the race's entry list
 * @param {(item: object) => string} options.participantName
 * @param {import('vue').Ref<string>} options.error
 * @param {() => string} options.badFileMessage
 */
export function useAcImport({ manualRows, participants, participantName, error, badFileMessage }) {
  const acFile = ref(null)
  /** car → { userId, how }: who each driver of the file is. */
  const acLinks = ref(new Map())
  /** car → userId: likely pairs, waiting for a person to confirm them. */
  const acGuesses = ref(new Map())

  function applyLinks() {
    const driverByUser = new Map()
    for (const driver of acFile.value.drivers) {
      const link = acLinks.value.get(driver.car)
      if (link) driverByUser.set(link.userId, driver)
    }
    manualRows.value = manualRows.value.map((row) => {
      const driver = driverByUser.get(row.user_id)
      if (driver) return { ...row, ...rowValues(driver) }
      // A row filled from the file earlier and untied since goes back to empty.
      return row.ac_car === null || row.ac_car === undefined ? row : { ...row, ...EMPTY_ROW }
    })
  }

  async function readAcFile(event) {
    const file = event.target.files?.[0]
    if (!file) return
    error.value = ''
    try {
      if (file.size > MAX_FILE_BYTES) throw new Error('The file is too large for a session file')
      const parsed = parseAcSession(JSON.parse((await file.text()).replace(/^﻿/, '')))
      const matches = [...matchAcDrivers(parsed.drivers, participants.value)]
      acFile.value = { name: file.name, ...parsed }
      acLinks.value = new Map(matches.filter(([, match]) => match.how !== 'guess'))
      acGuesses.value = new Map(matches.filter(([, match]) => match.how === 'guess').map(([car, match]) => [car, match.userId]))
      applyLinks()
    } catch {
      // Whatever went wrong (not JSON, another kind of file, no laps), the form says the same thing.
      acFile.value = null
      error.value = badFileMessage()
    }
  }

  /** Ties a driver of the file to a pilot (or to nobody); the pilot's previous driver, if any, is untied. */
  function linkAcDriver(car, userId) {
    if (!acFile.value) return
    const links = new Map([...acLinks.value].filter(([otherCar, link]) => otherCar !== car && link.userId !== userId))
    if (userId) links.set(car, { userId, how: 'manual' })
    acLinks.value = links
    applyLinks()
  }

  const acImport = computed(() => {
    if (!acFile.value) return null
    const labelOf = new Map(participants.value.map((pilot) => [pilot.user_id, participantName(pilot)]))
    const carOf = new Map([...acLinks.value].map(([car, link]) => [link.userId, car]))
    const drivers = acFile.value.drivers
      .map((driver) => {
        const link = acLinks.value.get(driver.car) ?? null
        const guessed = acGuesses.value.get(driver.car)
        const bestLap = driver.race?.bestLapMs ?? driver.qualification?.bestLapMs ?? null
        return {
          car: driver.car,
          name: driver.name,
          laps: driver.race?.laps ?? 0,
          bestLap: bestLap ? formatDuration(bestLap) : '',
          userId: link?.userId ?? null,
          how: link?.how ?? null,
          guess: !link && guessed && !carOf.has(guessed) && labelOf.has(guessed) ? { userId: guessed, label: labelOf.get(guessed) } : null
        }
      })
      .sort((a, b) => b.laps - a.laps || a.car - b.car)
    const pilots = participants.value
      .map((pilot) => ({ userId: pilot.user_id, label: labelOf.get(pilot.user_id), car: carOf.get(pilot.user_id) ?? null }))
      .sort((a, b) => a.label.localeCompare(b.label))
    return { fileName: acFile.value.name, drivers, pilots, linked: acLinks.value.size }
  })

  return { acImport, readAcFile, linkAcDriver }
}
