<script setup>
// Staff: upload the ACC JSON files or enter / replace results by hand. LMU
// races pick their drivers by search; other races list the registered grid.
// An Assetto Corsa race can fill its rows from the game's session file: each
// driver of the file is tied to a pilot of the grid, by name or by hand.
import { useI18n } from 'vue-i18n'
import { FileJson, Plus, Save, Search, Trash2 } from 'lucide-vue-next'
import LicenseBadge from '../../components/LicenseBadge.vue'
import PilotRoles from '../../components/PilotRoles.vue'
import UserAvatar from '../../components/UserAvatar.vue'
import { formatPilotNumber, formatRating, ratingForGame } from '../../pilotDisplay'
import { looseNumber, personName } from './raceFormat'

defineProps({
  race: { type: Object, required: true },
  pending: { type: Boolean, default: false },
  showAccUpload: { type: Boolean, default: false },
  withQualification: { type: Boolean, default: false },
  /** ACC ranks its grid from these laps and needs them all; elsewhere they are kept for the track records. */
  qualificationRequired: { type: Boolean, default: true },
  isLmu: { type: Boolean, default: false },
  game: { type: String, default: 'ACC' },
  rows: { type: Array, default: () => [] },
  pilotResults: { type: Array, default: () => [] },
  pilotLoading: { type: Boolean, default: false },
  showAcImport: { type: Boolean, default: false },
  /** The session file once it is read: its drivers with the pilots they are tied to (see useAcImport). */
  acImport: { type: Object, default: null }
})
const emit = defineEmits(['acc-file', 'upload-acc', 'upload-manual', 'add-pilot', 'remove-row', 'update-row', 'ac-file', 'ac-link'])
const pilotSearch = defineModel('pilotSearch', { type: String, default: '' })
const { t } = useI18n()

function pilotLabel(pilot) {
  return personName({ ...pilot, user_id: pilot.id }, `${t('roles.pilot')} ${pilot.id}`)
}

function update(row, field, value) {
  emit('update-row', row.user_id, field, value)
}

function hasSectors(row) {
  return Boolean(row.best_sectors_ms || row.qualification_best_sectors_ms)
}
</script>

<template>
  <form v-if="showAccUpload" class="staff-block" @submit.prevent="emit('upload-acc')">
    <div class="staff-block__head">
      <strong><FileJson :size="15" /> {{ race.game === 'LMU' ? t('raceDetails.uploadSimulatorResults') : t('raceDetails.uploadAccResults') }}</strong>
      <span>{{ t('racePage.staff.accHint') }}</span>
    </div>
    <div class="results-form__files">
      <label v-if="race.has_qualification" class="results-form__file">
        <span class="ui-label">{{ t('raceDetails.qualificationResultsJson') }}</span>
        <input class="staff-file" type="file" accept=".json,application/json" required @change="emit('acc-file', 'qualification', $event)" />
      </label>
      <label class="results-form__file">
        <span class="ui-label">{{ t('raceDetails.raceResultsJson') }}</span>
        <input class="staff-file" type="file" accept=".json,application/json" required @change="emit('acc-file', 'race', $event)" />
      </label>
    </div>
    <div class="staff-actions">
      <button class="ui-btn ui-btn--primary" type="submit" :disabled="pending">
        <FileJson :size="16" />{{ race.game === 'LMU' ? t('raceDetails.uploadSimulatorResults') : t('raceDetails.uploadAccResults') }}
      </button>
    </div>
  </form>

  <section v-if="showAcImport" class="staff-block ac-import">
    <div class="staff-block__head">
      <strong><FileJson :size="15" /> {{ t('racePage.staff.acImport.title') }}</strong>
      <span>{{ t('racePage.staff.acImport.hint') }}</span>
    </div>
    <label class="results-form__file">
      <span class="ui-label">{{ t('racePage.staff.acImport.file') }}</span>
      <input class="staff-file" type="file" accept=".json,application/json" @change="emit('ac-file', $event)" />
    </label>
    <template v-if="acImport">
      <p class="ac-import__summary ui-num" role="status">
        {{ t('racePage.staff.acImport.summary', { drivers: acImport.drivers.length, linked: acImport.linked, open: acImport.drivers.length - acImport.linked }) }}
      </p>
      <ul class="ac-import__list">
        <li v-for="driver in acImport.drivers" :key="driver.car" class="ac-import__row" :class="{ 'is-open': !driver.userId }">
          <span class="ac-import__driver">
            <strong>{{ driver.name || '—' }}</strong>
            <small class="ui-num">{{ t('racePage.staff.acImport.laps', { laps: driver.laps }) }}<template v-if="driver.bestLap"> · {{ driver.bestLap }}</template></small>
          </span>
          <select
            class="ui-input ac-import__select"
            :value="driver.userId ?? ''"
            :aria-label="`${driver.name}: ${t('racePage.staff.acImport.pilot')}`"
            @change="emit('ac-link', driver.car, Number($event.target.value) || null)"
          >
            <option value="">{{ t('racePage.staff.acImport.notLinked') }}</option>
            <option v-for="pilot in acImport.pilots" :key="pilot.userId" :value="pilot.userId" :disabled="pilot.car !== null && pilot.car !== driver.car">{{ pilot.label }}</option>
          </select>
          <span v-if="driver.how" class="ui-chip ac-import__how">{{ t(`racePage.staff.acImport.how.${driver.how}`) }}</span>
          <button v-else-if="driver.guess" class="ui-btn ui-btn--sm ac-import__guess" type="button" @click="emit('ac-link', driver.car, driver.guess.userId)">
            {{ t('racePage.staff.acImport.guess', { name: driver.guess.label }) }}
          </button>
          <span v-else class="ac-import__how"></span>
        </li>
      </ul>
      <p class="ac-import__note">{{ t('racePage.staff.acImport.note') }}</p>
    </template>
  </section>

  <form class="staff-block" @submit.prevent="emit('upload-manual')">
    <div class="staff-block__head">
      <strong>{{ t('racePage.staff.manualTitle') }}</strong>
      <span>{{ withQualification && qualificationRequired ? t('raceDetails.manualAccResultsHint') : t('raceDetails.manualResultsHint') }} {{ t('racePage.staff.timeFormat') }}</span>
    </div>

    <template v-if="isLmu">
      <label class="results-form__search">
        <Search :size="16" aria-hidden="true" />
        <input v-model="pilotSearch" class="ui-input" type="search" :placeholder="t('championships.pilotSearchPlaceholder')" :aria-label="t('championships.pilotSearchPlaceholder')" />
        <span class="ui-chip ui-num">{{ pilotLoading ? t('common.loading') : pilotResults.length }}</span>
      </label>
      <div v-if="pilotResults.length" class="results-form__found">
        <button
          v-for="pilot in pilotResults"
          :key="`manual-pilot-${pilot.id}`"
          class="results-form__pilot"
          type="button"
          :disabled="rows.some((row) => row.user_id === pilot.id)"
          @click="emit('add-pilot', pilot)"
        >
          <UserAvatar mini :src="pilot.avatar_url || ''" :color="pilot.avatar_color" :label="pilotLabel(pilot)" />
          <span class="results-form__pilot-main">
            <span class="results-form__pilot-name">{{ pilotLabel(pilot) }}<LicenseBadge :user="pilot" :game="game" /><PilotRoles :roles="pilot.pilot_roles" /></span>
            <small>#{{ formatPilotNumber(pilot.pilot_number) }} - RER {{ formatRating(ratingForGame(pilot, game)) }}</small>
          </span>
          <Plus :size="16" />
        </button>
      </div>
    </template>

    <div class="results-form__table" :class="{ 'has-quali': withQualification, 'has-actions': isLmu }">
      <div class="results-form__row results-form__row--head">
        <span>{{ t('roles.pilot') }}</span>
        <span v-if="withQualification">{{ t('raceDetails.qualificationBestLap') }}</span>
        <span>{{ t('raceDetails.resultTime') }}</span>
        <span>{{ t('raceDetails.laps') }}</span>
        <span>{{ t('raceDetails.bestLap') }}</span>
        <span v-if="isLmu"></span>
      </div>
      <div v-for="row in rows" :key="row.user_id" class="results-form__row">
        <span class="results-form__who">
          <strong>{{ row.label }}</strong><LicenseBadge :user="row" :game="game" />
          <span v-if="hasSectors(row)" class="ui-chip results-form__sectors" :title="t('racePage.staff.acImport.hasSectors')">S1–S3</span>
        </span>
        <input
          v-if="withQualification"
          class="ui-input ui-num"
          :value="row.qualification_best_lap_time"
          placeholder="1:48.250"
          :required="qualificationRequired"
          :aria-label="`${row.label}: ${t('raceDetails.qualificationBestLap')}`"
          @input="update(row, 'qualification_best_lap_time', $event.target.value)"
        />
        <input class="ui-input ui-num" :value="row.finish_time" required placeholder="45:12.345" :aria-label="`${row.label}: ${t('raceDetails.resultTime')}`" @input="update(row, 'finish_time', $event.target.value)" />
        <input class="ui-input ui-num" :value="row.lap_count" type="number" min="0" :aria-label="`${row.label}: ${t('raceDetails.laps')}`" @input="update(row, 'lap_count', looseNumber($event.target.value))" />
        <input class="ui-input ui-num" :value="row.best_lap_time" placeholder="1:48.250" :aria-label="`${row.label}: ${t('raceDetails.bestLap')}`" @input="update(row, 'best_lap_time', $event.target.value)" />
        <button v-if="isLmu" class="ui-btn ui-btn--danger ui-btn--icon ui-btn--sm" type="button" :title="t('common.delete')" :aria-label="t('common.delete')" @click="emit('remove-row', row.user_id)">
          <Trash2 :size="15" />
        </button>
      </div>
      <p v-if="!rows.length" class="results-form__empty">{{ isLmu ? t('racePage.staff.manualEmptyLmu') : t('raceDetails.noRegisteredPilots') }}</p>
    </div>

    <div class="staff-actions">
      <button class="ui-btn ui-btn--primary" type="submit" :disabled="pending || !rows.length">
        <Save :size="16" />{{ t('raceDetails.saveManualResults') }}
      </button>
    </div>
  </form>
</template>

<style scoped>
.staff-block__head strong {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.results-form__files {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}

.results-form__file {
  display: grid;
  gap: 8px;
}

.results-form__search {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
}

.results-form__search svg {
  position: absolute;
  top: 50%;
  left: 14px;
  color: var(--c-text-3);
  transform: translateY(-50%);
}

.results-form__search .ui-input {
  padding-left: 42px;
}

.results-form__found {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 8px;
}

.results-form__pilot {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  background: var(--c-surface-solid);
  color: var(--c-text);
  cursor: pointer;
  font: inherit;
  text-align: left;
  transition: border-color var(--dur-2);
}

.results-form__pilot:hover:not(:disabled) {
  border-color: var(--c-blue-line);
}

.results-form__pilot:disabled {
  cursor: default;
  opacity: 0.45;
}

.results-form__pilot-main {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.results-form__pilot-name {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 6px;
  font-size: 13.5px;
  font-weight: 600;
}

.results-form__pilot small {
  color: var(--c-text-3);
  font-size: 12px;
}

.results-form__table {
  --cols: minmax(160px, 1.4fr) repeat(3, minmax(90px, 1fr));
  display: grid;
  gap: 6px;
  overflow-x: auto;
}

.results-form__table.has-quali {
  --cols: minmax(160px, 1.4fr) repeat(4, minmax(90px, 1fr));
}

.results-form__table.has-actions {
  --cols: minmax(160px, 1.4fr) repeat(3, minmax(90px, 1fr)) 34px;
}

.results-form__table.has-quali.has-actions {
  --cols: minmax(160px, 1.4fr) repeat(4, minmax(90px, 1fr)) 34px;
}

.results-form__row {
  display: grid;
  grid-template-columns: var(--cols);
  align-items: center;
  gap: 8px;
  min-width: 620px;
}

.results-form__row--head span {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.results-form__row .ui-input {
  min-height: 40px;
  padding: 0 10px;
  font-size: 13.5px;
}

.results-form__who {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 6px;
  min-width: 0;
  font-size: 13.5px;
}

.results-form__empty {
  margin: 0;
  color: var(--c-text-3);
  font-size: 13px;
}

.results-form__sectors {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.06em;
}

.ac-import__summary,
.ac-import__note {
  margin: 0;
  color: var(--c-text-2);
  font-size: 13px;
}

.ac-import__note {
  color: var(--c-text-3);
}

.ac-import__list {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.ac-import__row {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 1.3fr) minmax(96px, auto);
  align-items: center;
  gap: 8px 12px;
  padding: 8px 10px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  background: var(--c-surface-solid);
}

/* A driver nobody is tied to yet asks for attention. */
.ac-import__row.is-open {
  border-color: var(--c-blue-line);
}

.ac-import__driver {
  display: grid;
  gap: 2px;
  min-width: 0;
  font-size: 13.5px;
}

.ac-import__driver strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ac-import__driver small {
  color: var(--c-text-3);
  font-size: 12px;
}

.ac-import__select {
  min-height: 40px;
  padding: 0 10px;
  font-size: 13.5px;
}

.ac-import__how,
.ac-import__guess {
  justify-self: end;
}

.ac-import__guess {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 720px) {
  .ac-import__row {
    grid-template-columns: minmax(0, 1fr);
  }

  .ac-import__how,
  .ac-import__guess {
    justify-self: start;
  }
}
</style>
