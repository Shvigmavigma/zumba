<script setup>
// Timing screen from P4 down: mono times, gaps, the fastest lap in purple,
// rating change in green/red and penalty markers that open the penalty list.
// At a glance it shows the columns that fit beside the side panels; unfolded
// ("all information") it has them all, the extra ones sliding in from the
// right. On phones every row becomes a labelled card.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Timer, TrendingDown, TrendingUp } from 'lucide-vue-next'
import LicenseBadge from '../../components/LicenseBadge.vue'
import PilotRoles from '../../components/PilotRoles.vue'
import UserAvatar from '../../components/UserAvatar.vue'
import { teamHref } from '../../pilotDisplay'
import { useRanks } from '../../useRanks'
import RankAura from '../../ui/rank/RankAura.vue'
import { isExtraColumn, resultColumns } from './resultColumns'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  mode: { type: String, default: 'race' },
  showQualiColumn: { type: Boolean, default: false },
  /** Every column the table has, not only the ones that fit at a glance. */
  detailed: { type: Boolean, default: false },
  /** Penalty markers only open the list for signed-in users (as before). */
  canOpenPenalties: { type: Boolean, default: false }
})
const emit = defineEmits(['open-penalty'])
const { t } = useI18n()
const { rankOfRating } = useRanks()
const rankOfRow = (row) => rankOfRating(row.ratingValue, row.roles)

const columns = computed(() => resultColumns(props.mode, { detailed: props.detailed, hasQuali: props.showQualiColumn }))
const shown = computed(() => new Set(columns.value))
/** The extra columns come in one after another, left to right. */
const extraOrder = computed(() => new Map(columns.value.filter((key) => isExtraColumn(props.mode, key)).map((key, index) => [key, index])))

function extra(key) {
  return { '--col': extraOrder.value.get(key) ?? 0 }
}

/** At a glance the penalties have no columns of their own: they are noted under the time. */
function penaltyNotes(row) {
  return [row.hasTimePenalty ? row.timePenalty : '', row.hasSrPenalty ? row.srPenalty : ''].filter(Boolean)
}
</script>

<template>
  <div id="race-results-table" class="ui-table-wrap timing" :class="{ 'is-detailed': detailed }">
    <table class="ui-table timing__table" :class="[`timing__table--${mode}`, { 'is-detailed': detailed }]">
      <thead>
        <tr>
          <th class="is-center">#</th>
          <th>{{ t('roles.pilot') }}</th>
          <th v-if="shown.has('car')" class="is-extra" :style="extra('car')"><span class="timing__in">{{ t('common.car') }}</span></th>
          <th v-if="shown.has('laps')" class="is-num is-extra" :style="extra('laps')"><span class="timing__in">{{ t('raceDetails.laps') }}</span></th>
          <th class="is-num">{{ t('raceDetails.bestLap') }}</th>
          <th v-if="shown.has('qualiLap')" class="is-num is-extra" :style="extra('qualiLap')" :title="t('raceDetails.qualificationBestLap')"><span class="timing__in">{{ t('racePage.results.cols.qualiLap') }}</span></th>
          <th v-if="shown.has('finish')" class="is-num is-extra" :style="extra('finish')"><span class="timing__in">{{ t('raceDetails.resultTime') }}</span></th>
          <th v-if="shown.has('timePenalty')" class="is-num is-extra" :style="extra('timePenalty')" :title="t('raceDetails.timePenalty')"><span class="timing__in">{{ t('racePage.results.cols.timePenalty') }}</span></th>
          <th v-if="shown.has('srPenalty')" class="is-num is-extra" :style="extra('srPenalty')" :title="t('raceDetails.srPenalty')"><span class="timing__in">{{ t('racePage.results.cols.srPenalty') }}</span></th>
          <th v-if="shown.has('adjusted')" class="is-num" :title="detailed ? t('raceDetails.adjustedTime') : undefined">{{ detailed ? t('racePage.results.cols.adjusted') : t('raceDetails.resultTime') }}</th>
          <th v-if="shown.has('delta')" class="is-num" :title="t('raceDetails.ratingDelta')">{{ t('racePage.results.cols.delta') }}</th>
          <th class="is-num">{{ t('raceDetails.gap') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, index) in rows" :key="row.key" class="timing__row rank-surface" :class="{ 'is-me': row.isMe, 'is-dnf': row.isDnf }" :data-rank="rankOfRow(row)" :style="{ '--i': Math.min(index, 14) }">
          <td class="is-center timing__pos" data-label="#"><RankAura :rank="rankOfRow(row)" :seed="index" /><span class="ui-pos">{{ row.position }}</span></td>
          <td class="timing__pilot" :data-label="t('roles.pilot')">
            <div class="timing__driver">
              <UserAvatar mini class="rank-avatar" :data-rank="rankOfRow(row)" :src="row.avatar" :color="row.color" :label="row.name" />
              <div class="timing__driver-main">
                <span class="timing__name-line">
                  <RouterLink v-if="row.pilotId" class="timing__name rank-name" :data-rank="rankOfRow(row)" :to="`/pilots/${row.pilotId}`">{{ row.name }}</RouterLink>
                  <strong v-else class="timing__name">{{ row.name }}</strong>
                  <LicenseBadge :rating="row.ratingValue" />
                  <PilotRoles :roles="row.roles" />
                </span>
                <span class="timing__meta">
                  <span>{{ row.subtitle }}</span>
                  <span class="ui-num">RER {{ row.rating }}</span>
                  <RouterLink v-if="row.teamId" class="timing__team" :to="teamHref(row.teamId)">{{ row.team }}</RouterLink>
                  <span v-else class="timing__team">{{ row.team }}</span>
                </span>
              </div>
            </div>
          </td>
          <td v-if="shown.has('car')" class="timing__car is-extra" :style="extra('car')" :data-label="t('common.car')"><span class="timing__in">{{ row.car }}</span></td>
          <td v-if="shown.has('laps')" class="is-num is-extra" :style="extra('laps')" :data-label="t('raceDetails.laps')"><span class="timing__in">{{ row.laps }}</span></td>
          <td class="is-num" :data-label="t('raceDetails.bestLap')">
            <span v-if="row.isFastest" class="timing__fastest" :title="t('racePage.results.fastestLap')"><Timer :size="12" />{{ row.bestLap }}</span>
            <s v-else-if="row.lapsAnnulled" class="timing__annulled" :title="t('racePage.results.lapsAnnulled')">{{ row.bestLap }}</s>
            <template v-else>{{ row.bestLap }}</template>
          </td>
          <td v-if="shown.has('qualiLap')" class="is-num is-extra" :style="extra('qualiLap')" :data-label="t('raceDetails.qualificationBestLap')"><span class="timing__in">{{ row.qualiLap }}</span></td>
          <td v-if="shown.has('finish')" class="is-num timing__time is-extra" :style="extra('finish')" :data-label="t('raceDetails.resultTime')"><span class="timing__in">{{ row.finish }}</span></td>
          <td v-if="shown.has('timePenalty')" class="is-num is-extra" :style="extra('timePenalty')" :data-label="t('raceDetails.timePenalty')"><span class="timing__in">
            <button
              v-if="row.hasTimePenalty && canOpenPenalties"
              class="timing__penalty"
              type="button"
              :aria-label="`${t('raceDetails.timePenalty')}: ${row.timePenalty}`"
              @click="emit('open-penalty', row.raw)"
            >
              {{ row.timePenalty }}
            </button>
            <strong v-else-if="row.hasTimePenalty" class="timing__penalty-value">{{ row.timePenalty }}</strong>
            <span v-else class="timing__none">-</span>
          </span></td>
          <td v-if="shown.has('srPenalty')" class="is-num is-extra" :style="extra('srPenalty')" :data-label="t('raceDetails.srPenalty')"><span class="timing__in">
            <button
              v-if="row.hasSrPenalty && canOpenPenalties"
              class="timing__penalty"
              type="button"
              :aria-label="`${t('raceDetails.srPenalty')}: ${row.srPenalty}`"
              @click="emit('open-penalty', row.raw)"
            >
              {{ row.srPenalty }}
            </button>
            <strong v-else-if="row.hasSrPenalty" class="timing__penalty-value">{{ row.srPenalty }}</strong>
            <span v-else class="timing__none">-</span>
          </span></td>
          <td v-if="shown.has('adjusted')" class="is-num timing__time" :data-label="detailed ? t('raceDetails.adjustedTime') : t('raceDetails.resultTime')">
            <span class="timing__result">
              {{ row.adjusted }}
              <template v-if="!detailed && penaltyNotes(row).length">
                <button
                  v-if="canOpenPenalties"
                  class="timing__penalty timing__penalty--note"
                  type="button"
                  :aria-label="`${t('raceDetails.penalties')}: ${penaltyNotes(row).join(', ')}`"
                  @click="emit('open-penalty', row.raw)"
                >
                  {{ penaltyNotes(row).join(' · ') }}
                </button>
                <strong v-else class="timing__penalty-value timing__penalty--note">{{ penaltyNotes(row).join(' · ') }}</strong>
              </template>
            </span>
          </td>
          <td v-if="shown.has('delta')" class="is-num" :data-label="t('raceDetails.ratingDelta')">
            <span class="timing__delta" :class="`is-${row.deltaTone}`">
              <TrendingUp v-if="row.deltaTone === 'up'" :size="13" />
              <TrendingDown v-else-if="row.deltaTone === 'down'" :size="13" />
              {{ row.delta }}
            </span>
          </td>
          <td class="is-num timing__gap" :data-label="t('raceDetails.gap')">{{ row.gap }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
/* At a glance the table fits its card: the pilot's cell gives way, the numbers do not wrap. */
.timing__table {
  min-width: 0;
}

/* A card that is short of room gives up the avatars and some air before the table has to scroll in its frame:
   at a glance beside the side panels on a small laptop, unfolded on anything narrower than a wide desktop. */
.timing {
  container: timing / inline-size;
}

@media (min-width: 761px) {
  @container timing (max-width: 800px) {
    .timing__table:not(.is-detailed) :is(th, td) {
      padding-inline: 9px;
    }

    .timing__table:not(.is-detailed) .timing__driver {
      min-width: 132px;
    }

    .timing__table:not(.is-detailed) .timing__driver :deep(.user-avatar) {
      display: none;
    }
  }

  @container timing (max-width: 1280px) {
    .timing__table.is-detailed :is(th, td) {
      padding-inline: 9px;
    }

    .timing__table.is-detailed .timing__driver {
      min-width: 170px;
    }

    .timing__table.is-detailed .timing__driver :deep(.user-avatar) {
      display: none;
    }

    .timing__table.is-detailed .timing__car {
      min-width: 96px;
    }
  }
}

.timing__table :is(th, td).is-num {
  white-space: nowrap;
}

/* The columns of the whole table arrive from the right, one after another. What moves is the content of
   the cells, never the cells: table cells must not become layers (see the rows above). */
.timing__table .is-extra > .timing__in {
  display: inline-block;
  animation: timing-col-in var(--dur-3) var(--ease-ios) backwards;
  animation-delay: calc(var(--col, 0) * 45ms);
}

@keyframes timing-col-in {
  from {
    opacity: 0;
    transform: translateX(28px);
  }
}

/* Rows fade in once, in order. Only opacity, and nothing left on the row once it is in ('backwards'):
   a row holding an animated transform became a layer of its own, and Chrome could leave such a row
   unpainted after the table laid itself out again, until a hover repainted it. */
.timing__row {
  animation: timing-in var(--dur-4) var(--ease-out) backwards;
  animation-delay: calc(var(--i, 0) * 28ms);
}

@keyframes timing-in {
  from {
    opacity: 0;
  }
}

.timing__row.is-me {
  background: var(--c-blue-soft);
}

.timing__row.is-me .timing__pos .ui-pos {
  background: var(--bm-blue);
  color: #fff;
}

.timing__row.is-dnf .timing__time,
.timing__row.is-dnf .timing__gap {
  color: color-mix(in srgb, var(--bm-red) 75%, var(--c-text));
  font-family: var(--font-body);
  font-weight: 600;
}

.timing__driver {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 170px;
}

.is-detailed .timing__driver {
  min-width: 240px;
}

.timing__result {
  display: inline-grid;
  justify-items: end;
  gap: 4px;
}

/* A best lap the stewards annulled: still in the result, no longer a lap that counts. */
.timing__annulled {
  color: var(--c-text-3);
  text-decoration-color: color-mix(in srgb, var(--bm-red) 70%, transparent);
  text-decoration-thickness: 2px;
}

.timing__penalty--note {
  padding: 1px 7px;
  font-size: 11px;
}

.timing__driver-main {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.timing__name-line {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 8px;
}

.timing__name-line :deep(.pilot-roles) {
  margin-inline-start: 0;
}

.timing__name {
  color: var(--c-text);
  font-weight: 700;
  text-decoration: none;
}

a.timing__name:hover {
  color: var(--c-accent-text);
}

.timing__meta {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 10px;
  color: var(--c-text-3);
  font-size: 12px;
}

.timing__team {
  padding: 1px 7px;
  border: 1px solid var(--c-line-strong);
  border-radius: 6px;
  color: var(--c-text-2);
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 700;
  text-decoration: none;
}

a.timing__team:hover {
  border-color: var(--c-blue-line);
  color: var(--c-accent-text);
}

.timing__car {
  min-width: 132px;
  max-width: 220px;
  color: var(--c-text-2);
  font-size: 13px;
}

.timing__fastest {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: 7px;
  background: color-mix(in srgb, #a855f7 18%, transparent);
  color: #c084fc;
  font-weight: 700;
}

:root[data-theme='light'] .timing__fastest {
  color: #7e22ce;
}

.timing__penalty {
  padding: 3px 9px;
  border: 1px solid color-mix(in srgb, var(--bm-red) 40%, transparent);
  border-radius: 7px;
  background: color-mix(in srgb, var(--bm-red) 12%, transparent);
  color: color-mix(in srgb, var(--bm-red) 85%, var(--c-text));
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 12.5px;
  font-weight: 800;
  transition: background-color var(--dur-2), transform var(--dur-2) var(--ease-ios);
}

.timing__penalty:hover {
  background: color-mix(in srgb, var(--bm-red) 24%, transparent);
}

.timing__penalty:active {
  transform: scale(0.95);
}

.timing__penalty-value {
  color: color-mix(in srgb, var(--bm-red) 85%, var(--c-text));
  font-weight: 800;
}

.timing__none {
  color: var(--c-text-3);
}

.timing__delta {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--c-text-2);
  font-weight: 700;
}

.timing__delta.is-up {
  color: color-mix(in srgb, var(--bm-green) 85%, var(--c-text));
}

.timing__delta.is-down {
  color: color-mix(in srgb, var(--bm-red) 85%, var(--c-text));
}

@media (max-width: 760px) {
  .timing {
    overflow: visible;
    border: 0;
    background: transparent;
  }

  .timing__table {
    min-width: 0;
  }

  .timing__car {
    min-width: 0;
  }

  .timing__result {
    justify-items: start;
  }

  .timing__table thead {
    display: none;
  }

  .timing__table,
  .timing__table tbody {
    display: block;
  }

  .timing__table tbody {
    display: grid;
    gap: 10px;
  }

  .timing__row {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0;
    overflow: hidden;
    border: 1px solid var(--c-line);
    border-radius: var(--r-lg);
    background: var(--c-surface-solid);
  }

  .timing__row td {
    display: grid;
    gap: 3px;
    padding: 9px 12px;
    border-bottom: 1px solid var(--c-line);
    text-align: left;
  }

  .timing__row td::before {
    color: var(--c-text-3);
    content: attr(data-label);
    font-family: var(--font-mono);
    font-size: 9.5px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }

  .timing__row td.timing__pos {
    position: absolute;
    padding: 0;
    border: 0;
  }

  .timing__row td.timing__pos::before {
    display: none;
  }

  .timing__row {
    position: relative;
  }

  .timing__row td.timing__pilot {
    grid-column: 1 / -1;
    padding: 12px 12px 12px 54px;
    background: var(--c-sunken);
  }

  .timing__row td.timing__pilot::before {
    display: none;
  }

  .timing__row td.timing__pos {
    top: 14px;
    left: 12px;
    z-index: 1;
  }

  .timing__driver {
    min-width: 0;
  }

  .timing__driver :deep(.user-avatar) {
    display: none;
  }

  .timing__car {
    max-width: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .timing__row,
  .timing__table .is-extra > .timing__in {
    animation: none;
  }
}
</style>
