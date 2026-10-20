<script setup>
// The season calendar: a vertical timeline of rounds (finished rounds lit like
// start lights) with the shared race row for each stage.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { CalendarDays } from 'lucide-vue-next'
import EmptyState from '../../ui/EmptyState.vue'
import RaceRow from '../../components/RaceRow.vue'
import { state } from '../../store'
import { pluralBucket, scoringLabel, seasonProgress } from './helpers'

const props = defineProps({
  stages: { type: Array, default: () => [] },
  assets: { type: Object, default: null }
})

const { t } = useI18n()
const season = computed(() => seasonProgress(props.stages))
const countLabel = computed(() => `${season.value.total} ${t(`championships.stageWord${pluralBucket(season.value.total, state.locale)}`)}`)
</script>

<template>
  <section class="stages ui-card" aria-labelledby="champ-stages-title">
    <header class="ui-card__head">
      <div class="ui-card__title">
        <span class="ui-eyebrow ui-eyebrow--accent">{{ t('champPage.stages.eyebrow') }}</span>
        <h3 id="champ-stages-title">{{ t('championships.stages') }}</h3>
      </div>
      <span v-if="season.total" class="ui-chip">{{ countLabel }}</span>
    </header>

    <ol v-if="season.total" class="stages__list">
      <li
        v-for="(item, index) in season.stages"
        :key="item.stage.id"
        v-reveal="{ delay: Math.min(index, 6) * 70, y: 16, blur: 4 }"
        class="stages__item"
        :class="`is-${item.phase}`"
      >
        <div class="stages__node" aria-hidden="true">
          <span class="stages__lamp"></span>
        </div>
        <div class="stages__body">
          <p class="stages__meta">
            <span class="stages__round ui-num">{{ t('championships.stageNumber', { number: item.round }) }}</span>
            <span>{{ scoringLabel(item.stage.scoring_system) }}</span>
            <span v-if="item.stage.pole_bonus_enabled">{{ t('championships.poleBonus') }}</span>
            <span v-if="item.stage.is_team_event">{{ t('champPage.teamStage') }}</span>
            <span v-if="item.phase === 'next'" class="stages__flag">{{ t('champPage.season.next') }}</span>
            <span v-if="item.phase === 'live'" class="stages__flag is-live">{{ t('champPage.season.live') }}</span>
          </p>
          <RaceRow :race="item.stage" :assets="assets" />
        </div>
      </li>
    </ol>

    <EmptyState v-else :icon="CalendarDays" :title="t('champPage.stages.emptyTitle')" :text="t('champPage.stages.emptyText')" compact />
  </section>
</template>

<style scoped>
.stages {
  min-width: 0;
}

.stages__list {
  position: relative;
  display: grid;
  gap: 14px;
  margin: 0;
  padding: 0;
  list-style: none;
}

/* Timeline spine behind the lamps. */
.stages__list::before {
  position: absolute;
  top: 14px;
  bottom: 14px;
  left: 13px;
  width: 2px;
  border-radius: 2px;
  background: linear-gradient(180deg, var(--c-line-strong), color-mix(in srgb, var(--c-line-strong) 30%, transparent));
  content: '';
}

.stages__item {
  position: relative;
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 14px;
}

.stages__node {
  display: grid;
  justify-items: center;
  padding-top: 6px;
}

.stages__lamp {
  position: relative;
  width: 16px;
  height: 16px;
  border: 3px solid var(--c-surface-solid);
  border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, #2a1418, #12080a 70%);
  box-shadow: 0 0 0 1px var(--c-line-strong);
}

.is-done .stages__lamp,
.is-live .stages__lamp {
  background: radial-gradient(circle at 38% 32%, #ffd6d9 0, #ff3347 30%, #c10016 72%, #6a000b 100%);
  box-shadow: 0 0 0 1px rgba(255, 59, 78, 0.5), 0 0 12px rgba(255, 40, 60, 0.7);
}

.is-live .stages__lamp::after {
  position: absolute;
  inset: -7px;
  border: 2px solid rgba(255, 59, 78, 0.6);
  border-radius: 50%;
  content: '';
  animation: stages-ping 1.6s var(--ease-out) infinite;
}

.is-next .stages__lamp {
  background: var(--bm-blue);
  box-shadow: 0 0 0 1px var(--bm-blue-bright), 0 0 14px color-mix(in srgb, var(--bm-blue-bright) 70%, transparent);
}

.stages__body {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.stages__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 14px;
  margin: 0;
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.stages__round {
  color: var(--c-text);
}

.stages__flag {
  color: var(--c-accent-text);
}

.stages__flag.is-live {
  color: color-mix(in srgb, var(--bm-red) 85%, var(--c-text));
}

.is-done .stages__body :deep(.row) {
  opacity: 0.88;
}

@keyframes stages-ping {
  0% {
    opacity: 0.8;
    transform: scale(0.7);
  }
  100% {
    opacity: 0;
    transform: scale(1.6);
  }
}

@media (max-width: 760px) {
  .stages__item {
    grid-template-columns: 20px minmax(0, 1fr);
    gap: 10px;
  }

  .stages__list::before {
    left: 9px;
  }

  .stages__lamp {
    width: 14px;
    height: 14px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .is-live .stages__lamp::after {
    animation: none;
  }
}
</style>
