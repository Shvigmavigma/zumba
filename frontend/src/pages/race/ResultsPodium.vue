<script setup>
// Broadcast-style podium: P2 · P1 · P3, the winner raised on the tallest
// plinth. Steps rise in ceremony order (third, second, then the winner).
import { useI18n } from 'vue-i18n'
import { Timer } from 'lucide-vue-next'
import LicenseBadge from '../../components/LicenseBadge.vue'
import PilotRoles from '../../components/PilotRoles.vue'
import UserAvatar from '../../components/UserAvatar.vue'
import RankAura from '../../ui/rank/RankAura.vue'
import { SEASON_FINISH } from '../../ranks'
import { useRanks } from '../../useRanks'

defineProps({
  /** Display rows from useRaceResults().resultView, first three only. */
  rows: { type: Array, default: () => [] },
  mode: { type: String, default: 'race' }
})
const { t } = useI18n()
const { rankOfRating } = useRanks()
const rankOfRow = (row) => rankOfRating(row.ratingValue, row.roles)

const CEREMONY_DELAY = [320, 160, 0]
</script>

<template>
  <ol class="podium" :class="`podium--${rows.length}`">
    <li
      v-for="(row, index) in rows"
      :key="row.key"
      v-reveal="{ delay: CEREMONY_DELAY[index], y: 34, blur: 6 }"
      class="podium__slot"
      :class="[`is-p${index + 1}`, { 'is-me': row.isMe }]"
    >
      <article v-tilt="5" class="step" :class="{ 'season-plate ui-dark': rankOfRow(row) === SEASON_FINISH }" :data-rank="rankOfRow(row)">
        <span class="ui-glare" aria-hidden="true"></span>
        <RankAura :rank="rankOfRow(row)" :seed="index" />
        <header class="step__head">
          <span class="step__pos">P{{ row.position }}</span>
          <span v-if="mode === 'race'" class="step__delta ui-num" :class="`is-${row.deltaTone}`" :title="t('raceDetails.ratingDelta')">
            {{ row.delta }} <small>RER</small>
          </span>
        </header>

        <UserAvatar class="step__avatar rank-avatar" :data-rank="rankOfRow(row)" :src="row.avatar" :color="row.color" :label="row.name" />

        <div class="step__id">
          <RouterLink v-if="row.pilotId" class="step__name rank-name" :data-rank="rankOfRow(row)" :to="`/pilots/${row.pilotId}`">{{ row.name }}</RouterLink>
          <strong v-else class="step__name">{{ row.name }}</strong>
          <span class="step__badges">
            <LicenseBadge :rating="row.ratingValue" />
            <PilotRoles :roles="row.roles" />
          </span>
          <span class="step__sub">{{ row.subtitle }}</span>
        </div>

        <strong class="step__time ui-num" :class="{ 'is-dnf': row.isDnf }">{{ row.mainTime }}</strong>

        <dl v-if="mode === 'race'" class="step__laps">
          <div :class="{ 'is-fastest': row.isFastest }">
            <dt><Timer v-if="row.isFastest" :size="12" />{{ t('raceDetails.bestLap') }}</dt>
            <dd class="ui-num"><s v-if="row.lapsAnnulled" class="step__annulled" :title="t('racePage.results.lapsAnnulled')">{{ row.bestLap }}</s><template v-else>{{ row.bestLap }}</template></dd>
          </div>
          <div v-if="row.hasQualiLap">
            <dt>{{ t('raceDetails.qualificationBestLap') }}</dt>
            <dd class="ui-num">{{ row.qualiLap }}</dd>
          </div>
        </dl>
        <p v-else-if="row.gap && row.gap !== '-'" class="step__gap ui-num">{{ row.gap }}</p>

        <div class="step__plinth" aria-hidden="true"><span class="ui-num">{{ row.position }}</span></div>
      </article>
    </li>
  </ol>
</template>

<style scoped>
.podium {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  align-items: end;
  gap: clamp(10px, 1.4vw, 16px);
  margin: 0;
  padding: 12px 0 0;
  list-style: none;
}

.podium__slot {
  --medal: var(--bm-gold);
  --medal-ink: #1b1300;
  --plinth: 96px;
  min-width: 0;
}

.podium__slot.is-p1 {
  order: 2;
}

.podium__slot.is-p2 {
  --medal: var(--bm-silver);
  --medal-ink: #0e141f;
  --plinth: 64px;
  order: 1;
}

.podium__slot.is-p3 {
  --medal: var(--bm-bronze);
  --medal-ink: #1d0d02;
  --plinth: 44px;
  order: 3;
}

.step {
  position: relative;
  display: grid;
  justify-items: center;
  gap: 12px;
  padding: 18px 16px 0;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--medal) 38%, var(--c-line));
  border-radius: var(--r-xl) var(--r-xl) var(--r-md) var(--r-md);
  background:
    radial-gradient(120% 70% at 50% 0%, color-mix(in srgb, var(--medal) 22%, transparent), transparent 70%),
    var(--c-surface-solid);
  box-shadow: 0 18px 40px color-mix(in srgb, var(--medal) 12%, transparent);
  text-align: center;
}

.is-p1 .step {
  box-shadow: 0 24px 60px color-mix(in srgb, var(--bm-gold) 22%, transparent), 0 0 0 1px color-mix(in srgb, var(--bm-gold) 30%, transparent);
}

.is-me .step {
  outline: 2px solid var(--c-blue-line);
  outline-offset: 2px;
}

.step__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
}

.step__pos {
  color: var(--medal);
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 800;
  line-height: 1;
}

.step__delta {
  padding: 4px 9px;
  border-radius: var(--r-pill);
  background: var(--c-sunken);
  color: var(--c-text-2);
  font-size: 12px;
  font-weight: 700;
}

.step__delta small {
  font-size: 9.5px;
  opacity: 0.7;
}

.step__delta.is-up {
  background: color-mix(in srgb, var(--bm-green) 14%, transparent);
  color: color-mix(in srgb, var(--bm-green) 85%, var(--c-text));
}

.step__delta.is-down {
  background: color-mix(in srgb, var(--bm-red) 14%, transparent);
  color: color-mix(in srgb, var(--bm-red) 85%, var(--c-text));
}

.step__avatar {
  width: 64px;
  height: 64px;
  box-shadow: 0 0 0 3px var(--medal), 0 0 26px color-mix(in srgb, var(--medal) 45%, transparent);
}

.is-p1 .step__avatar {
  width: 78px;
  height: 78px;
}

.step__id {
  display: grid;
  justify-items: center;
  gap: 6px;
  min-width: 0;
  max-width: 100%;
}

.step__name {
  max-width: 100%;
  overflow: hidden;
  color: var(--c-text);
  font-size: 16px;
  font-weight: 700;
  text-decoration: none;
  text-overflow: ellipsis;
  white-space: nowrap;
}

a.step__name:hover {
  color: var(--c-accent-text);
}

.step__badges {
  display: inline-flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 4px;
}

.step__badges :deep(.pilot-roles) {
  margin-inline-start: 0;
}

.step__sub {
  max-width: 100%;
  overflow: hidden;
  color: var(--c-text-3);
  font-size: 12.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.step__time {
  color: var(--c-text);
  font-size: clamp(20px, 2vw, 26px);
  font-weight: 700;
}

.step__time.is-dnf {
  color: color-mix(in srgb, var(--bm-red) 80%, var(--c-text));
  font-size: 18px;
}

.step__laps {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(0, 1fr));
  gap: 6px;
  width: 100%;
  margin: 0;
}

.step__laps div {
  display: grid;
  gap: 3px;
  padding: 8px 6px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-sm);
  background: var(--c-sunken);
}

.step__laps dt {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 9.5px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.step__laps dd {
  margin: 0;
  color: var(--c-text);
  font-size: 13.5px;
  font-weight: 600;
}

.step__laps .is-fastest {
  border-color: color-mix(in srgb, #a855f7 45%, transparent);
  background: color-mix(in srgb, #a855f7 14%, transparent);
}

.step__laps .is-fastest dt,
.step__laps .is-fastest dd {
  color: #c084fc;
}

/* A best lap the stewards annulled: still in the result, no longer a lap that counts. */
.step__annulled {
  color: var(--c-text-3);
  text-decoration-color: color-mix(in srgb, var(--bm-red) 70%, transparent);
  text-decoration-thickness: 2px;
}

.step__gap {
  margin: 0;
  color: var(--c-text-2);
  font-size: 13px;
}

.step__plinth {
  display: grid;
  place-items: start center;
  width: calc(100% + 32px);
  height: var(--plinth);
  margin-top: 4px;
  padding-top: 8px;
  background: linear-gradient(180deg, color-mix(in srgb, var(--medal) 75%, transparent), color-mix(in srgb, var(--medal) 18%, transparent));
  color: var(--medal-ink);
  font-size: 22px;
  font-weight: 800;
  transition: height var(--dur-4) var(--ease-spring);
}

.step:hover .step__plinth {
  height: calc(var(--plinth) + 6px);
}

@media (max-width: 760px) {
  .podium {
    grid-template-columns: minmax(0, 1fr);
    align-items: stretch;
  }

  .podium__slot.is-p1,
  .podium__slot.is-p2,
  .podium__slot.is-p3 {
    order: 0;
  }

  .step {
    grid-template-columns: auto minmax(0, 1fr) auto;
    justify-items: start;
    align-items: center;
    gap: 6px 12px;
    padding: 14px 14px 14px 0;
    border-radius: var(--r-lg);
    text-align: left;
  }

  .step__head {
    display: contents;
  }

  .step__pos {
    display: none;
  }

  .step__plinth {
    grid-row: 1 / span 3;
    grid-column: 1;
    order: -1;
    place-items: center;
    align-self: stretch;
    width: 46px;
    height: auto;
    margin: -14px 0;
    padding: 0;
    font-size: 20px;
  }

  .step:hover .step__plinth {
    height: auto;
  }

  .step__avatar,
  .is-p1 .step__avatar {
    display: none;
  }

  .step__id {
    grid-column: 2;
    justify-items: start;
  }

  .step__badges {
    justify-content: flex-start;
  }

  .step__delta {
    grid-column: 3;
    grid-row: 1;
  }

  .step__time {
    grid-column: 2 / -1;
    font-size: 20px;
  }

  .step__laps,
  .step__gap {
    grid-column: 2 / -1;
  }
}
</style>
