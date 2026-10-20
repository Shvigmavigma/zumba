<script setup>
// Race briefing: organiser notes, the evening's schedule (RaceSchedule),
// server, format, track statistics, mods and the cars allowed on the grid. When the race needs mods their block turns
// into a warning that pulses until the pilot has opened a link (useRaceMods).
import { computed, onBeforeUnmount, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Car, Check, Clock3, Copy, ExternalLink, Fuel, Gauge, Package, Server, Sigma, Timer, Users } from 'lucide-vue-next'
import WarningPulse from '../../ui/fx/WarningPulse.vue'
import { formatDateTime } from '../../timezone'
import { formatDuration, isLinkLike, modHref } from './raceFormat'
import { isModLink } from './raceMods'
import RaceSchedule from './RaceSchedule.vue'
import { MODS_ANCHOR_ID, useRaceMods } from './useRaceMods'

const CARS_PREVIEW = 6
const COPIED_MS = 1800

const props = defineProps({
  race: { type: Object, required: true },
  trackAverageLapMs: { type: Number, default: null },
  trackExpectedAverageLapMs: { type: Number, default: null }
})
const { t } = useI18n()
const { mods, seen: modsSeen, flashing: modsFlashing, markSeen: markModsSeen } = useRaceMods(() => props.race)

const showAllCars = ref(false)
const copyState = ref('')
let copyTimer = 0

const cars = computed(() => props.race.allowed_cars || [])
const visibleCars = computed(() => (showAllCars.value ? cars.value : cars.value.slice(0, CARS_PREVIEW)))
const serverIsLink = computed(() => isLinkLike(props.race.server_link))

async function copyServer() {
  window.clearTimeout(copyTimer)
  try {
    await navigator.clipboard.writeText(String(props.race.server_link || ''))
    copyState.value = 'done'
  } catch {
    copyState.value = 'failed'
  }
  copyTimer = window.setTimeout(() => { copyState.value = '' }, COPIED_MS)
}

onBeforeUnmount(() => window.clearTimeout(copyTimer))
</script>

<template>
  <section class="brief ui-card" aria-labelledby="race-brief-title">
    <header class="ui-card__head">
      <div class="ui-card__title">
        <p class="ui-eyebrow ui-eyebrow--accent">{{ t('racePage.brief.eyebrow') }}</p>
        <h2 id="race-brief-title">{{ t('racePage.brief.title') }}</h2>
      </div>
    </header>

    <p v-if="race.description" class="brief__desc">{{ race.description }}</p>

    <RaceSchedule :race="race" />

    <div class="brief__server">
      <span class="brief__server-icon"><Server :size="18" /></span>
      <div class="brief__server-main">
        <span class="brief__label">{{ t('fields.server') }}</span>
        <a v-if="serverIsLink" class="brief__server-value" :href="modHref(race.server_link)" target="_blank" rel="noopener noreferrer">
          {{ race.server_link }}<ExternalLink :size="13" />
        </a>
        <strong v-else class="brief__server-value">{{ race.server_link || t('common.none') }}</strong>
      </div>
      <button
        v-if="race.server_link"
        class="ui-btn ui-btn--ghost ui-btn--sm brief__copy"
        type="button"
        :aria-label="t('racePage.brief.copyServer')"
        @click="copyServer"
      >
        <Check v-if="copyState === 'done'" :size="15" />
        <Copy v-else :size="15" />
        {{ copyState === 'done' ? t('racePage.brief.copied') : copyState === 'failed' ? t('racePage.brief.copyFailed') : t('racePage.brief.copy') }}
      </button>
    </div>

    <dl class="brief__facts">
      <div>
        <dt><Timer :size="13" />{{ t('fields.qualification') }}</dt>
        <dd>{{ race.has_qualification ? t('raceDetails.withQualification') : t('raceDetails.withoutQualification') }}</dd>
      </div>
      <div>
        <dt><Sigma :size="13" />{{ t('racePage.brief.rating') }}</dt>
        <dd :class="{ 'is-on': race.is_official }">{{ race.is_official ? t('raceDetails.ratingCounted') : t('raceDetails.ratingNotCounted') }}</dd>
      </div>
      <div v-if="race.game !== 'LMU'">
        <dt><Users :size="13" />{{ t('fields.maxPilots') }}</dt>
        <dd class="ui-num">{{ race.max_pilots }}</dd>
      </div>
      <div>
        <dt><Fuel :size="13" />{{ t('raceDetails.mandatoryPitStops') }}</dt>
        <dd class="ui-num">{{ race.required_pit_stops ?? 0 }}</dd>
      </div>
      <div v-if="race.game === 'LMU' && race.lmu_results_at">
        <dt><Clock3 :size="13" />{{ t('raceDetails.infoLmuResults') }}</dt>
        <dd class="ui-num">{{ formatDateTime(race.lmu_results_at) }}</dd>
      </div>
      <div v-if="trackAverageLapMs">
        <dt><Gauge :size="13" />{{ t('tracks.averageLap') }}</dt>
        <dd class="ui-num">{{ formatDuration(trackAverageLapMs) }}</dd>
      </div>
      <div v-if="trackExpectedAverageLapMs">
        <dt><Gauge :size="13" />{{ t('tracks.expectedAverageLap') }}</dt>
        <dd class="ui-num">{{ formatDuration(trackExpectedAverageLapMs) }}</dd>
      </div>
    </dl>

    <div v-if="mods.length" :id="MODS_ANCHOR_ID" class="brief__group brief__mods" :class="{ 'is-seen': modsSeen, 'is-flashing': modsFlashing }">
      <h3 class="brief__label brief__label--alert"><WarningPulse :size="17" :calm="modsSeen" />{{ t('racePage.brief.modsRequired') }}</h3>
      <p class="brief__mods-note">{{ t('racePage.brief.modsNote') }}</p>
      <ul class="brief__links">
        <li v-for="mod in mods" :key="mod">
          <a v-if="isModLink(mod)" class="brief__mod" :href="modHref(mod)" target="_blank" rel="noopener noreferrer" @click="markModsSeen">
            <Package :size="15" />{{ mod }}<ExternalLink :size="13" />
          </a>
          <!-- Staff sometimes give a pack's name instead of a link: nothing to open. -->
          <span v-else class="brief__mod brief__mod--name"><Package :size="15" />{{ mod }}</span>
        </li>
      </ul>
      <button v-if="!modsSeen" class="ui-btn ui-btn--ghost ui-btn--sm brief__mods-ack" type="button" @click="markModsSeen">
        <Check :size="15" />{{ t('racePage.brief.modsAck') }}
      </button>
    </div>
    <div v-else class="brief__group">
      <h3 class="brief__label"><Package :size="13" />{{ t('fields.mods') }}</h3>
      <p class="brief__muted">{{ t('racePage.brief.noMods') }}</p>
    </div>

    <div class="brief__group">
      <h3 class="brief__label"><Car :size="13" />{{ t('fields.allowedCars') }} <span class="ui-num">{{ cars.length }}</span></h3>
      <TransitionGroup v-if="cars.length" tag="ul" name="ui-list" class="brief__cars">
        <li v-for="item in visibleCars" :key="item" class="ui-chip">{{ item }}</li>
      </TransitionGroup>
      <p v-else class="brief__muted">{{ t('racePage.brief.anyCar') }}</p>
      <button v-if="cars.length > CARS_PREVIEW" class="ui-btn ui-btn--ghost ui-btn--sm brief__more" type="button" @click="showAllCars = !showAllCars">
        {{ showAllCars ? t('racePage.brief.lessCars') : t('racePage.brief.moreCars', { count: cars.length - CARS_PREVIEW }) }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.brief__desc {
  margin: 0;
  color: var(--c-text-2);
  font-size: 14.5px;
  line-height: 1.6;
  white-space: pre-line;
}

.brief__server {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 12px 12px 12px 14px;
  border: 1px solid var(--c-blue-line);
  border-radius: var(--r-md);
  background: var(--c-blue-soft);
}

.brief__server-icon {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 11px;
  background: var(--bm-blue);
  color: #fff;
}

.brief__server-main {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.brief__server-value {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  overflow: hidden;
  color: var(--c-text);
  font-size: 14.5px;
  font-weight: 650;
  text-decoration: none;
  text-overflow: ellipsis;
  white-space: nowrap;
}

a.brief__server-value:hover {
  color: var(--c-accent-text);
}

.brief__label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.brief__facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px;
  margin: 0;
  overflow: hidden;
  border: 1px solid var(--c-line);
  border-radius: var(--r-lg);
  background: var(--c-line);
}

.brief__facts > div {
  display: grid;
  align-content: start;
  gap: 5px;
  padding: 12px 14px;
  background: var(--c-surface-solid);
}

/* An odd number of facts: the last one takes the whole row, no empty cell. */
.brief__facts > div:last-child:nth-child(odd) {
  grid-column: 1 / -1;
}

.brief__facts dt {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.brief__facts dd {
  margin: 0;
  color: var(--c-text);
  font-size: 14px;
  font-weight: 600;
}

.brief__facts dd.is-on {
  color: color-mix(in srgb, var(--bm-green) 80%, var(--c-text));
}

.brief__group {
  display: grid;
  gap: 10px;
}

.brief__links,
.brief__cars {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.brief__cars {
  gap: 6px;
}

.brief__cars .ui-chip {
  font-family: var(--font-body);
  font-size: 12px;
  letter-spacing: 0;
  text-transform: none;
}

/* ---------- Mods the race needs ---------- */
/* A warning plate: without the mods the pilot cannot join the server. It
   calms down once a link has been opened and lights up when the page is
   scrolled to it from the hero or the registration form. */
.brief__mods {
  padding: 14px;
  border: 1px solid color-mix(in srgb, var(--bm-red) 46%, transparent);
  border-radius: var(--r-md);
  background: color-mix(in srgb, var(--bm-red) 9%, transparent);
  transition: border-color var(--dur-3), background-color var(--dur-3), box-shadow var(--dur-3);
}

.brief__mods.is-seen {
  border-color: color-mix(in srgb, var(--bm-red) 26%, var(--c-line));
  background: color-mix(in srgb, var(--bm-red) 4%, transparent);
}

.brief__mods.is-flashing {
  border-color: var(--bm-red);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--bm-red) 22%, transparent), 0 18px 40px -18px color-mix(in srgb, var(--bm-red) 70%, transparent);
}

.brief__label--alert {
  gap: 9px;
  color: color-mix(in srgb, var(--bm-red) 78%, var(--c-text));
  font-size: 12px;
}

.brief__mods-note {
  margin: 0;
  color: var(--c-text-2);
  font-size: 13.5px;
  line-height: 1.5;
}

.brief__mod {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 38px;
  max-width: 100%;
  padding: 0 14px;
  border: 1px solid color-mix(in srgb, var(--bm-red) 50%, transparent);
  border-radius: var(--r-pill);
  background: color-mix(in srgb, var(--bm-red) 12%, var(--c-surface-solid));
  color: var(--c-text);
  font-size: 14px;
  font-weight: 600;
  overflow-wrap: anywhere;
  text-decoration: none;
  transition: background-color var(--dur-2), border-color var(--dur-2), transform var(--dur-2) var(--ease-ios);
}

a.brief__mod:hover {
  border-color: var(--bm-red);
  background: color-mix(in srgb, var(--bm-red) 24%, var(--c-surface-solid));
}

a.brief__mod:active {
  transform: scale(0.97);
}

/* Calms the warning for pilots who already have the mods. */
.brief__mods-ack {
  justify-self: start;
}

.brief__mod:focus-visible {
  outline: 2px solid var(--bm-cyan);
  outline-offset: 2px;
}

.brief__muted {
  margin: 0;
  color: var(--c-text-3);
  font-size: 13.5px;
}

.brief__more {
  justify-self: start;
}

@media (max-width: 420px) {
  .brief__server {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .brief__copy {
    grid-column: 1 / -1;
  }

  .brief__facts {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
