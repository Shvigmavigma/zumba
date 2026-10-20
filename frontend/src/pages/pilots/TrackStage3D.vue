<script setup>
// The track in 3D with its records on it. Each timing sector of the lap is
// painted in the colour of the site pilot who holds it and carries their
// avatar; the holder of the lap record stands by the start line, and the
// light running the lap takes their colour. Beside the model: the lap record, the three sectors, the lap they
// would make together and how many laps all of it was taken from. A sector is
// lit up from either side, the model or the list.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Sigma, Timer } from 'lucide-vue-next'
import UserAvatar from '../../components/UserAvatar.vue'
import { formatShortDate } from '../../timezone'
import TrackLayout3D from '../../ui/track/TrackLayout3D.vue'
import { formatGap, formatSectorTime, lapRecord, sectorRecords } from './trackSectors'

const props = defineProps({
  /** The track's name as the site shows it. */
  track: { type: String, default: '' },
  /** Layout data for TrackLayout3D. */
  layout: { type: Object, required: true },
  /** The track's finished races, as the races API returns them: the sector times are read from them. */
  races: { type: Array, default: () => [] },
  /** First row of the track's records table: the lap record, or null. */
  topRow: { type: Object, default: null }
})

const { t } = useI18n()
const active = ref(null)

const records = computed(() => sectorRecords(props.races))
const bestLap = computed(() => lapRecord(props.topRow, props.races))
const sectors = computed(() => records.value.sectors.map((sector, index) => ({ n: index + 1, record: sector })))
const hasSectors = computed(() => records.value.sectors.some(Boolean))
/** What TrackLayout3D paints: one colour per sector, none while nobody holds it. */
const sectorPaint = computed(() => (hasSectors.value ? records.value.sectors.map((sector) => (sector ? { color: sector.pilot.color } : null)) : []))
const holderOf = computed(() => Object.fromEntries(sectors.value.filter((sector) => sector.record).map((sector) => [sector.n, sector.record])))
/** Each sector's share of the ideal lap, for the bar under the list. */
const shares = computed(() => {
  const total = records.value.idealMs
  if (!total) return []
  return records.value.sectors.map((sector) => ({ n: sector.n, color: sector.pilot.color, width: `${(sector.ms / total) * 100}%` }))
})
/** How much the ideal lap beats the record by (negative: nobody has put it together yet). */
const idealGap = computed(() => (records.value.idealMs && bestLap.value ? records.value.idealMs - bestLap.value.ms : null))

function sessionLabel(session) {
  if (session === 'qualification') return t('tracks.lapSourceQualification')
  return session === 'race' ? t('tracks.lapSourceRace') : ''
}

function whenLabel(record) {
  return [sessionLabel(record.session), record.raceDate ? formatShortDate(record.raceDate) : ''].filter(Boolean).join(' · ')
}

function pilotLink(pilot) {
  return pilot?.userId ? `/pilots/${pilot.userId}` : ''
}

function light(n) {
  active.value = n
}

function dim(n) {
  if (active.value === n) active.value = null
}
</script>

<template>
  <div class="stage">
    <div class="stage__model">
      <TrackLayout3D
        v-model:active-sector="active"
        :track="layout"
        :sectors="sectorPaint"
        :light-color="bestLap?.pilot.color || ''"
        :show-zones="false"
        :label="t('pilotsPage.tracks.layout.figure', { track })"
        :corner-word="t('pilotsPage.tracks.layout.corner')"
        :hint="t('pilotsPage.tracks.layout.hint')"
      >
        <template #sector="{ n, active: lit, compact }">
          <span class="pin" :class="{ 'is-active': lit, 'is-compact': compact }">
            <UserAvatar mini class="pin__avatar" :src="holderOf[n].pilot.avatar" :color="holderOf[n].pilot.color" :label="holderOf[n].pilot.name" />
            <b class="pin__tag ui-num">S{{ n }}</b>
            <span v-if="lit" class="pin__info">
              <strong>{{ holderOf[n].pilot.nickname || holderOf[n].pilot.name }}</strong>
              <span class="ui-num">{{ formatSectorTime(holderOf[n].ms) }}</span>
            </span>
          </span>
        </template>
        <template v-if="bestLap" #start="{ compact }">
          <span class="pin pin--lap" :class="{ 'is-compact': compact }" :style="{ '--sector': bestLap.pilot.color }">
            <UserAvatar mini class="pin__avatar" :src="bestLap.pilot.avatar" :color="bestLap.pilot.color" :label="bestLap.pilot.name" />
            <b class="pin__tag"><Timer :size="compact ? 9 : 11" /></b>
            <span class="pin__info pin__info--hover">
              <strong>{{ bestLap.pilot.nickname || bestLap.pilot.name }}</strong>
              <span class="ui-num">{{ formatSectorTime(bestLap.ms) }}</span>
            </span>
          </span>
        </template>
      </TrackLayout3D>
    </div>

    <aside class="stage__stats" :aria-label="t('pilotsPage.tracks.layout.stats', { track })">
      <section class="lap">
        <p class="ui-eyebrow ui-eyebrow--accent"><Timer :size="14" />{{ t('pilotsPage.tracks.layout.bestLap') }}</p>
        <component :is="pilotLink(bestLap.pilot) ? 'RouterLink' : 'div'" v-if="bestLap" class="lap__row" :to="pilotLink(bestLap.pilot) || undefined" :style="{ '--pilot': bestLap.pilot.color }">
          <UserAvatar class="lap__avatar" :src="bestLap.pilot.avatar" :color="bestLap.pilot.color" :label="bestLap.pilot.name" />
          <span class="lap__who">
            <strong>{{ bestLap.pilot.name }}</strong>
            <small>{{ whenLabel(bestLap) }}</small>
          </span>
          <b class="lap__time ui-num">{{ formatSectorTime(bestLap.ms) }}</b>
        </component>
        <p v-else class="stage__note">{{ t('pilotsPage.tracks.layout.noLap') }}</p>
      </section>

      <section class="sectors">
        <p class="ui-eyebrow">{{ t('pilotsPage.tracks.layout.sectors') }}</p>
        <ol v-if="hasSectors" class="sectors__list">
          <li v-for="sector in sectors" :key="sector.n">
            <component
              :is="pilotLink(sector.record?.pilot) ? 'RouterLink' : 'div'"
              class="sector"
              :class="{ 'is-active': active === sector.n, 'is-empty': !sector.record }"
              :to="pilotLink(sector.record?.pilot) || undefined"
              :style="{ '--pilot': sector.record?.pilot.color }"
              :aria-label="sector.record ? t('pilotsPage.tracks.layout.sectorHolder', { n: sector.n, name: sector.record.pilot.name, time: formatSectorTime(sector.record.ms) }) : undefined"
              @pointerenter="light(sector.n)"
              @pointerleave="dim(sector.n)"
              @focus="light(sector.n)"
              @blur="dim(sector.n)"
            >
              <b class="sector__tag ui-num">S{{ sector.n }}</b>
              <template v-if="sector.record">
                <UserAvatar mini class="sector__avatar" :src="sector.record.pilot.avatar" :color="sector.record.pilot.color" :label="sector.record.pilot.name" />
                <span class="sector__who">
                  <strong>{{ sector.record.pilot.name }}</strong>
                  <small>{{ whenLabel(sector.record) }}</small>
                </span>
                <b class="sector__time ui-num">{{ formatSectorTime(sector.record.ms) }}</b>
              </template>
              <span v-else class="sector__none">{{ t('pilotsPage.tracks.layout.sectorFree') }}</span>
            </component>
          </li>
        </ol>
        <p v-else class="stage__note">{{ t('pilotsPage.tracks.layout.noSectors') }}</p>
        <div v-if="shares.length" class="sectors__bar" aria-hidden="true">
          <span v-for="share in shares" :key="share.n" :class="{ 'is-active': active === share.n }" :style="{ width: share.width, '--pilot': share.color }"></span>
        </div>
      </section>

      <section v-if="records.idealMs" class="ideal">
        <span class="ideal__what">
          <span class="ui-eyebrow"><Sigma :size="14" />{{ t('pilotsPage.tracks.layout.ideal') }}</span>
          <small>{{ t('pilotsPage.tracks.layout.idealNote') }}</small>
        </span>
        <span class="ideal__value">
          <b class="ui-num">{{ formatSectorTime(records.idealMs) }}</b>
          <small v-if="idealGap !== null" class="ui-num">{{ t('pilotsPage.tracks.layout.gap', { gap: formatGap(idealGap) }) }}</small>
        </span>
      </section>

      <p v-if="records.validLaps" class="stage__counts">{{ t('pilotsPage.tracks.layout.counted', { laps: records.validLaps, pilots: records.pilots }) }}</p>
    </aside>
  </div>
</template>

<style scoped>
.stage {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(290px, 1fr);
  align-items: center;
  gap: clamp(14px, 2vw, 26px);
}

.stage__model {
  position: relative;
  min-width: 0;
}

/* A soft light under the model, so it does not hang in nothing. */
.stage__model::before {
  position: absolute;
  inset: 12% 8%;
  border-radius: 50%;
  background: radial-gradient(closest-side, color-mix(in srgb, var(--bm-blue) 22%, transparent), transparent);
  content: '';
  pointer-events: none;
}

.stage__stats {
  display: grid;
  gap: 16px;
  min-width: 0;
  padding: 16px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-lg);
  background: var(--c-sunken);
}

.stage__note,
.stage__counts {
  margin: 0;
  color: var(--c-text-3);
  font-size: 12.5px;
  line-height: 1.45;
}

/* ---------- A sector's holder, pinned to the model ---------- */
.pin {
  position: relative;
  display: inline-flex;
  align-items: center;
  height: 38px;
  padding: 2px;
  border: 2px solid var(--sector);
  border-radius: 999px;
  background: var(--c-surface-solid);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.4);
  color: var(--c-text);
  white-space: nowrap;
  transition: transform var(--dur-2) var(--ease-ios), box-shadow var(--dur-2) var(--ease-out);
}

.pin.is-active {
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--sector) 30%, transparent), 0 10px 26px rgba(0, 0, 0, 0.45);
  transform: scale(1.08);
}

.pin__avatar {
  width: 30px;
  height: 30px;
  border-width: 0;
  box-shadow: none;
}

/* The sector's number rides on the avatar's edge. */
.pin__tag {
  position: absolute;
  bottom: -8px;
  left: 50%;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--sector);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  line-height: 1.3;
  /* A light profile colour still needs readable digits. */
  text-shadow: 0 0 3px rgba(0, 0, 0, 0.75);
  transform: translateX(-50%);
}

.pin.is-active .pin__tag {
  left: 17px;
}

.pin__info {
  display: grid;
  gap: 0;
  padding: 0 12px 0 8px;
  font-size: 11.5px;
  line-height: 1.25;
}

.pin__info strong {
  max-width: 150px;
  overflow: hidden;
  font-weight: 700;
  text-overflow: ellipsis;
}

.pin__info span {
  color: var(--c-text-2);
}

/* The lap record's holder: the same pin with a stopwatch, opening on hover. */
.pin--lap .pin__tag {
  display: grid;
  place-items: center;
  padding: 2px 6px;
}

.pin__info--hover {
  display: none;
}

.pin--lap:hover {
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--sector) 30%, transparent), 0 10px 26px rgba(0, 0, 0, 0.45);
}

.pin--lap:hover .pin__info--hover {
  display: grid;
}

.pin--lap:hover .pin__tag {
  left: 17px;
}

.pin.is-compact {
  height: 30px;
}

.pin.is-compact .pin__avatar {
  width: 22px;
  height: 22px;
}

.pin.is-compact .pin__tag {
  bottom: -7px;
  padding: 0 4px;
  font-size: 9px;
}

.pin.is-compact.is-active .pin__tag,
.pin--lap.is-compact:hover .pin__tag {
  left: 13px;
}

/* ---------- The lap record ---------- */
.lap {
  display: grid;
  gap: 10px;
}

.lap__row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  color: var(--c-text);
  text-decoration: none;
}

.lap__avatar {
  width: 48px;
  height: 48px;
  border-color: var(--pilot);
}

.lap__who,
.sector__who {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.lap__who strong,
.sector__who strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lap__who strong {
  font-size: 15.5px;
}

.lap__who small,
.sector__who small {
  overflow: hidden;
  color: var(--c-text-3);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lap__time {
  color: var(--c-text);
  font-size: clamp(22px, 2.2vw, 28px);
  font-weight: 700;
  letter-spacing: -0.01em;
}

a.lap__row:hover strong,
a.sector:hover .sector__who strong {
  color: var(--c-accent-text);
}

/* ---------- The three sectors ---------- */
.sectors {
  display: grid;
  gap: 10px;
  padding-top: 14px;
  border-top: 1px solid var(--c-line);
}

.sectors__list {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.sector {
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid transparent;
  border-radius: var(--r-sm);
  color: var(--c-text);
  text-decoration: none;
  transition: background var(--dur-1), border-color var(--dur-1);
}

.sector.is-active {
  border-color: color-mix(in srgb, var(--pilot) 55%, transparent);
  background: color-mix(in srgb, var(--pilot) 14%, transparent);
}

.sector__tag {
  display: grid;
  min-width: 30px;
  height: 22px;
  padding: 0 6px;
  place-items: center;
  border-radius: 999px;
  background: var(--pilot, var(--c-line-strong));
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  text-shadow: 0 0 3px rgba(0, 0, 0, 0.75);
}

.sector__avatar {
  width: 30px;
  height: 30px;
  border-color: var(--pilot);
}

.sector__time {
  font-size: 16px;
  font-weight: 700;
}

.sector.is-empty {
  grid-template-columns: auto minmax(0, 1fr);
}

.sector__none {
  color: var(--c-text-3);
  font-size: 13px;
}

/* How the ideal lap divides between the sectors, in their holders' colours. */
.sectors__bar {
  display: flex;
  gap: 3px;
  height: 6px;
}

.sectors__bar span {
  border-radius: 999px;
  background: var(--pilot);
  opacity: 0.85;
  transition: opacity var(--dur-1);
}

.sectors__bar span.is-active {
  opacity: 1;
  box-shadow: 0 0 10px var(--pilot);
}

/* ---------- The lap the best sectors would make ---------- */
.ideal {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 14px;
  border-top: 1px solid var(--c-line);
}

.ideal__what,
.ideal__value {
  display: grid;
  gap: 3px;
}

.ideal__what small,
.ideal__value small {
  color: var(--c-text-3);
  font-size: 12px;
}

.ideal__value {
  justify-items: end;
}

.ideal__value b {
  font-size: 18px;
  font-weight: 700;
}

@media (max-width: 1000px) {
  .stage {
    grid-template-columns: minmax(0, 1fr);
  }

  /* Pins on the outer edge of the model reach past its box: keep them off the text above. */
  .stage__model {
    padding-block: 14px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .pin,
  .sector,
  .sectors__bar span {
    transition: none;
  }
}
</style>
