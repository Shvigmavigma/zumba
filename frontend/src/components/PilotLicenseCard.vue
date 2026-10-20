<script setup>
// A pilot's licence for one simulator, built like the registration licence and
// finished in the material of its RER tier: matte rookie, bronze, brushed
// silver, gold, pearl platinum, prismatic diamond and a champion card. The
// security foil grows brighter and the rim livelier with every tier.
// The season champion's licences (seasonChampion.js) are printed on the title
// plate instead; the RER tier at the bottom stays, it is a different thing.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Crown } from 'lucide-vue-next'
import { brandingSettings } from '../brandingSettings'
import LicenceFoil from './licence/LicenceFoil.vue'
import UserAvatar from './UserAvatar.vue'
import RankAura from '../ui/rank/RankAura.vue'
import RankEmblem from '../ui/rank/RankEmblem.vue'
import RankScene from '../ui/rank/RankScene.vue'
import SeasonChampionBackdrop from '../ui/rank/SeasonChampionBackdrop.vue'
import { DEFAULT_LICENSE_TIERS, formatPilotNumber, formatRating, pilotName } from '../pilotDisplay'
import { rankFor } from '../ranks'
import { seasonTitleRole } from '../seasonChampion'
import { state } from '../store'
import { formatShortDate } from '../timezone'

const props = defineProps({
  pilot: { type: Object, required: true },
  game: { type: String, required: true },
  rating: { type: [Number, String], default: null },
  /** Kept for callers that already resolved the tier; the rank is derived from the rating. */
  tier: { type: Object, default: null }
})

const { t } = useI18n()
const GAME_NAMES = { ACC: 'Assetto Corsa Competizione', AC: 'Assetto Corsa', iRacing: 'iRacing', LMU: 'Le Mans Ultimate' }
const name = computed(() => pilotName(props.pilot, props.pilot.login))
const rank = computed(() => rankFor(props.rating, state.licenseTiers || DEFAULT_LICENSE_TIERS))
const seed = computed(() => [...props.game].reduce((sum, char) => sum + char.charCodeAt(0), 0))
const seasonTitle = computed(() => seasonTitleRole(props.pilot))
</script>

<template>
  <article v-tilt="8" class="lic" :class="{ 'lic--season': seasonTitle }" :data-rank="rank.key">
    <span class="ui-glare" aria-hidden="true"></span>
    <SeasonChampionBackdrop v-if="seasonTitle" class="lic__scene" size="card" cx="48px" cy="50%" />
    <template v-else>
      <span class="lic__material" aria-hidden="true"></span>
      <RankScene class="lic__scene" :rank="rank.key" size="card" :seed="seed" cx="48px" cy="50%" on-dark />
      <LicenceFoil :rank="rank.key" />
      <RankAura :rank="rank.key" :seed="seed" glint on-dark />
    </template>

    <header class="lic__head">
      <img class="lic__logo" :src="brandingSettings.dark_logo_url" alt="BMRL" />
      <span v-if="seasonTitle" class="lic__season"><Crown :size="12" />{{ t('profilePage.seasonTitle.pill') }}</span>
      <span class="lic__kind">{{ t('profilePage.licences.card', { game }) }}</span>
    </header>

    <div class="lic__body">
      <UserAvatar class="lic__avatar" :src="pilot.avatar_url" :color="pilot.avatar_color" :label="name" />
      <div class="lic__who">
        <strong>{{ name }}</strong>
        <span>{{ GAME_NAMES[game] || game }}</span>
        <small class="ui-mono">{{ t('profilePage.licences.issued', { date: formatShortDate(pilot.created_at) }) }}</small>
      </div>
      <div class="lic__plate">
        <small>{{ t('profilePage.licences.number') }}</small>
        <b class="ui-num">#{{ formatPilotNumber(pilot.pilot_number) }}</b>
      </div>
    </div>

    <footer class="lic__foot">
      <span class="lic__tier">
        <RankEmblem :rank="rank.key" :size="30" />
        <b class="rank-text">{{ rank.tier.name }}</b>
      </span>
      <span class="lic__rating"><small>{{ t('profilePage.licences.rating') }}</small><b class="ui-num">{{ formatRating(rating) }}</b></span>
      <span class="lic__next">
        <span class="lic__meter"><span :style="{ '--value': `${Math.round(rank.progress * 100)}%` }"></span></span>
        <small>{{ rank.next ? t('profilePage.licences.toNext', { name: rank.next.name, count: rank.toNext }) : t('profilePage.licences.top') }}</small>
      </span>
    </footer>
  </article>
</template>

<style scoped>
.lic {
  position: relative;
  display: grid;
  gap: 18px;
  padding: 20px;
  overflow: hidden;
  isolation: isolate;
  /* The card is laid out by its own width (see the narrow layout below):
     it sits in wide grids, in the home sidebar and on phones. */
  container-type: inline-size;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 22px;
  background: linear-gradient(140deg, color-mix(in srgb, var(--rank-3) 55%, #0b1324), #05070d 68%);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.42), inset 0 1px 0 rgba(255, 255, 255, 0.1);
  color: #fff;
}

.lic[data-rank='gold'],
.lic[data-rank='platinum'],
.lic[data-rank='diamond'],
.lic[data-rank='champ'] {
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.42), 0 0 44px -14px var(--rank-glow), inset 0 1px 0 rgba(255, 255, 255, 0.14);
}

/* The tier's metal along the top edge. */
.lic::after {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  height: 4px;
  background: var(--rank-metal);
  content: '';
}

/* ---------- Materials ---------- */
.lic__material {
  position: absolute;
  inset: 0;
  z-index: -2;
  background: radial-gradient(110% 90% at 100% 0%, color-mix(in srgb, var(--rank-2) 34%, transparent), transparent 62%);
}

.lic[data-rank='gold'] .lic__material {
  background:
    radial-gradient(90% 80% at 100% 0%, color-mix(in srgb, var(--rank-2) 40%, transparent), transparent 62%),
    radial-gradient(70% 70% at 0% 100%, color-mix(in srgb, var(--rank-3) 70%, transparent), transparent 70%);
}

.lic[data-rank='platinum'] .lic__material {
  background:
    conic-gradient(from 200deg at 80% 10%, rgba(165, 243, 252, 0.22), rgba(196, 181, 253, 0.18), rgba(110, 231, 183, 0.14), rgba(165, 243, 252, 0.22)),
    radial-gradient(100% 80% at 100% 0%, color-mix(in srgb, var(--rank-2) 30%, transparent), transparent 62%);
}

.lic[data-rank='champ'] .lic__material {
  background:
    radial-gradient(80% 70% at 100% 0%, rgba(176, 92, 255, 0.42), transparent 62%),
    radial-gradient(70% 70% at 0% 100%, rgba(255, 224, 138, 0.2), transparent 66%),
    conic-gradient(from 0deg at 50% 50%, rgba(255, 122, 217, 0.08), rgba(79, 216, 234, 0.08), rgba(255, 224, 138, 0.08), rgba(255, 122, 217, 0.08));
}

/* The tier's living scene sits on the material, under the security foil. */
.lic__scene {
  z-index: -2;
}

/* ---------- Season champion ---------- */
.lic--season {
  border-color: transparent;
  background: #06070a;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.5), 0 0 50px -18px rgba(245, 200, 76, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.lic--season::after {
  background: linear-gradient(90deg, #8a6614, #f5c84c 30%, #fff3c4 50%, #f5c84c 70%, #8a6614);
}

.lic--season .lic__avatar {
  border-color: #f5c84c;
  box-shadow: 0 0 0 4px rgba(245, 200, 76, 0.14), 0 0 26px rgba(245, 200, 76, 0.45);
}

/* Outranks the tier's metal plate: the title's gold, whatever the RER tier. */
.lic.lic--season[data-rank] .lic__plate.lic__plate {
  background: linear-gradient(135deg, #fff3c4, #f5c84c 50%, #b88a1e);
  color: #1a1304;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.5), 0 6px 18px -6px rgba(245, 200, 76, 0.7);
}

.lic__season {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-right: auto;
  padding: 3px 8px;
  border-radius: var(--r-pill);
  background: linear-gradient(120deg, #fff3c4, #f5c84c 45%, #c9971c);
  color: #1a1304;
  font-family: var(--font-mono);
  font-size: 8.5px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  white-space: nowrap;
}

/* ---------- Content ---------- */
.lic__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.lic__logo {
  width: auto;
  height: 20px;
}

.lic__kind {
  color: rgba(255, 255, 255, 0.6);
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.16em;
  text-align: right;
  text-transform: uppercase;
}

.lic__body {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
}

.lic__avatar {
  width: 56px;
  height: 56px;
  border: 2px solid rgba(255, 255, 255, 0.85);
  box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.08), 0 0 26px var(--rank-glow);
}

.lic__who {
  display: grid;
  gap: 3px;
  min-width: 0;
}

/* A long name takes a second line instead of being cut off. */
.lic__who strong {
  display: -webkit-box;
  overflow: hidden;
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 800;
  line-height: 1.15;
  overflow-wrap: anywhere;
  text-transform: uppercase;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.lic__who span {
  overflow: hidden;
  color: rgba(255, 255, 255, 0.72);
  font-size: 12.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lic__who small {
  color: rgba(255, 255, 255, 0.45);
  font-size: 10.5px;
  letter-spacing: 0.04em;
}

.lic__plate {
  display: grid;
  justify-items: center;
  gap: 2px;
  padding: 7px 11px;
  border-radius: 12px;
  background: #fff;
  color: #05070d;
}

/* From silver upwards the number plate is struck in the tier's metal. */
.lic:not([data-rank='rookie']):not([data-rank='bronze']) .lic__plate {
  background: var(--rank-metal);
  color: var(--rank-ink);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.5), 0 6px 18px -6px var(--rank-glow);
}

.lic__plate small {
  font-family: var(--font-mono);
  font-size: 8px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.lic__plate b {
  font-size: 21px;
  font-weight: 700;
  line-height: 1;
}

.lic__foot {
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr);
  align-items: center;
  gap: 14px;
  padding-top: 14px;
  border-top: 1px dashed rgba(255, 255, 255, 0.16);
}

.lic__tier {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.lic__tier b {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.lic__rating {
  display: grid;
  gap: 2px;
}

.lic__rating small {
  color: rgba(255, 255, 255, 0.5);
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.14em;
}

.lic__rating b {
  font-size: 18px;
  font-weight: 700;
  line-height: 1;
}

.lic__next {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.lic__next small {
  overflow: hidden;
  color: rgba(255, 255, 255, 0.55);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lic__meter {
  display: block;
  height: 5px;
  overflow: hidden;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.12);
}

.lic__meter span {
  display: block;
  width: var(--value, 0%);
  height: 100%;
  border-radius: inherit;
  background: var(--rank-metal);
  box-shadow: 0 0 10px var(--rank-glow);
  transition: width 900ms var(--ease-ios);
}

/* Narrow card: a smaller portrait, no issue date, and the way to the next
   tier on a line of its own. */
@container (max-width: 360px) {
  .lic__body {
    gap: 10px;
  }

  .lic__avatar {
    width: 46px;
    height: 46px;
  }

  .lic__who small {
    display: none;
  }

  .lic__foot {
    grid-template-columns: auto auto;
    justify-content: space-between;
  }

  .lic__next {
    grid-column: 1 / -1;
  }
}
</style>
