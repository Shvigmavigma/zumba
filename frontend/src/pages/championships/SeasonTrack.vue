<script setup>
// The season as a start gantry: one lamp per stage. Finished stages light up
// red one after another (like the start procedure) when the track scrolls into
// view, the live stage pulses and the next stage carries a blue ring. A line
// runs through the lamps: striped red as far as the season has come (into the
// stretch ahead by the days already passed), dashed beyond.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { onceInView, prefersReducedMotion } from '../../ui/motion/env'
import { formatInTimeZone } from '../../timezone'
import { seasonProgress, seasonRailFill } from './helpers'

const props = defineProps({
  stages: { type: Array, default: () => [] }
})

const { t } = useI18n()
const root = ref(null)
const armed = ref(false)
let stopObserving = null

const season = computed(() => seasonProgress(props.stages))
const current = computed(() => season.value.stages.find((item) => item.stage.id === season.value.current?.id) || null)
// How much of each stretch between two lamps is driven (0 to 1).
const fills = computed(() => seasonRailFill(season.value.stages))

function shortDate(value) {
  return formatInTimeZone(value, { day: '2-digit', month: '2-digit' })
}

function stageTitle(item) {
  const parts = [`R${item.round}`, item.stage.name, item.stage.track, formatInTimeZone(item.stage.datetime_start, { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })]
  return parts.filter(Boolean).join(' · ')
}

onMounted(() => {
  if (prefersReducedMotion() || !root.value) {
    armed.value = true
    return
  }
  stopObserving = onceInView(root.value, () => {
    armed.value = true
  })
})

onBeforeUnmount(() => stopObserving?.())
</script>

<template>
  <section ref="root" class="season" :class="{ 'is-armed': armed }" :aria-label="t('champPage.season.aria')">
    <header class="season__head">
      <span class="ui-eyebrow">{{ t('champPage.season.title') }}</span>
      <span v-if="season.total" class="season__count ui-num">{{ t('champPage.season.done', { done: season.finished, total: season.total }) }}</span>
    </header>

    <p v-if="!season.total" class="season__empty">{{ t('champPage.season.empty') }}</p>

    <template v-else>
      <ol class="season__rail" :style="{ '--n': season.total }">
        <li
          v-for="(item, index) in season.stages"
          :key="item.stage.id"
          class="season__stop"
          :class="[`is-${item.phase}`, { 'has-stretch': index < fills.length }]"
          :style="{ '--i': index, '--fill': fills[index] ?? 0 }"
        >
          <RouterLink class="season__lamp-link" :to="`/races/${item.stage.id}`" :title="stageTitle(item)" :aria-label="stageTitle(item)">
            <span class="season__lamp"></span>
          </RouterLink>
          <span class="season__round ui-num">R{{ item.round }}</span>
          <span class="season__date ui-num">{{ shortDate(item.stage.datetime_start) }}</span>
        </li>
      </ol>

      <p v-if="current" class="season__next">
        <span class="season__next-label">{{ current.phase === 'live' ? t('champPage.season.live') : t('champPage.season.next') }}</span>
        <RouterLink :to="`/races/${current.stage.id}`">R{{ current.round }} · {{ current.stage.name }}</RouterLink>
        <span class="season__next-meta">{{ [current.stage.track, formatInTimeZone(current.stage.datetime_start, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })].filter(Boolean).join(' · ') }}</span>
      </p>
      <p v-else class="season__next"><span class="season__next-label">{{ t('champPage.season.complete') }}</span></p>
    </template>
  </section>
</template>

<style scoped>
.season {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.season__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.season__count {
  color: var(--c-text-2);
  font-size: 12px;
}

.season__empty {
  margin: 0;
  color: var(--c-text-3);
  font-size: 13.5px;
}

.season__rail {
  --lamp: 18px;
  position: relative;
  display: grid;
  grid-template-columns: repeat(var(--n), minmax(40px, 1fr));
  gap: 0;
  margin: 0;
  padding: 0;
  overflow-x: auto;
  list-style: none;
  scrollbar-width: none;
}

.season__rail::-webkit-scrollbar {
  display: none;
}

/* The gantry: a dark housing behind the lamp row, dark in both themes. */
.season__rail::before {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  height: calc(var(--lamp) + 16px);
  min-width: calc(var(--n) * 40px);
  border: 1px solid var(--c-line);
  border-radius: var(--r-pill);
  background: color-mix(in srgb, #000 58%, transparent);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05), inset 0 -8px 18px rgba(0, 0, 0, 0.35);
  content: '';
}

:root[data-theme='light'] .season__rail::before {
  background: #0b111d;
}

.season__stop {
  position: relative;
  display: grid;
  justify-items: center;
  gap: 4px;
  min-width: 0;
}

.season__lamp-link {
  position: relative;
  /* Above the line, which runs from lamp centre to lamp centre. */
  z-index: 1;
  display: grid;
  place-items: center;
  width: 100%;
  height: calc(var(--lamp) + 16px);
  border-radius: var(--r-pill);
  -webkit-tap-highlight-color: transparent;
}

.season__lamp-link:focus-visible {
  outline-offset: -2px;
}

/* ---------- The line between the lamps ---------- */
/* Each stop draws the stretch from its lamp to the next one; the lamps cover the joints. */
.season__stop.has-stretch::before,
.season__stop.has-stretch::after {
  position: absolute;
  top: calc((var(--lamp) + 16px) / 2);
  left: 50%;
  width: 100%;
  content: '';
  pointer-events: none;
}

/* Ahead: a dashed line. */
.season__stop.has-stretch::before {
  height: 2px;
  margin-top: -1px;
  background: repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.24) 0 6px, transparent 6px 12px);
}

/* Driven: a red bar with stripes at 45°, the podium steps' pattern. It fills
   from lamp to lamp in step with the lamps lighting up. */
.season__stop.has-stretch::after {
  height: 6px;
  margin-top: -3px;
  border-radius: var(--r-pill);
  background:
    repeating-linear-gradient(135deg, rgba(255, 255, 255, 0.28) 0 3px, transparent 3px 7px),
    linear-gradient(90deg, #c10016, #ff3347);
  box-shadow: 0 0 10px rgba(255, 40, 60, 0.45);
  clip-path: inset(0 100% 0 0 round 3px);
  transition: clip-path 150ms linear calc(var(--i) * 150ms);
}

.season.is-armed .season__stop.has-stretch::after {
  clip-path: inset(0 calc(100% - var(--fill) * 100%) 0 0 round 3px);
}

.season__lamp {
  position: relative;
  width: var(--lamp);
  height: var(--lamp);
  border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, #2a1418, #12080a 70%);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.06), inset 0 -2px 4px rgba(0, 0, 0, 0.6);
  transition:
    background 140ms linear calc(var(--i) * 150ms),
    box-shadow 200ms linear calc(var(--i) * 150ms),
    transform 360ms var(--ease-spring) calc(var(--i) * 150ms);
}

.season__lamp-link:hover .season__lamp {
  transform: scale(1.18);
  transition-delay: 0ms;
}

.season.is-armed .is-done .season__lamp,
.season.is-armed .is-live .season__lamp {
  background: radial-gradient(circle at 38% 32%, #ffd6d9 0, #ff3347 28%, #c10016 70%, #6a000b 100%);
  box-shadow:
    0 0 12px rgba(255, 40, 60, 0.85),
    0 0 30px rgba(255, 30, 50, 0.4),
    inset 0 0 0 1px rgba(255, 255, 255, 0.25);
}

.season.is-armed .is-live .season__lamp::after {
  position: absolute;
  inset: -6px;
  border: 2px solid rgba(255, 59, 78, 0.7);
  border-radius: 50%;
  content: '';
  animation: season-ping 1.6s var(--ease-out) infinite;
}

.is-next .season__lamp {
  background: radial-gradient(circle at 35% 30%, #13244d, #070d1d 70%);
  box-shadow:
    0 0 0 2px var(--bm-blue-bright),
    0 0 16px color-mix(in srgb, var(--bm-blue-bright) 60%, transparent);
}

.season__round {
  color: var(--c-text-2);
  font-size: 11px;
  font-weight: 700;
}

.is-next .season__round,
.is-live .season__round {
  color: var(--c-accent-text);
}

.season__date {
  color: var(--c-text-3);
  font-size: 10.5px;
}

.season__next {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 10px;
  margin: 0;
  font-size: 13.5px;
}

.season__next-label {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.season__next a {
  color: var(--c-text);
  font-weight: 650;
  text-decoration: none;
}

.season__next a:hover {
  color: var(--c-accent-text);
}

.season__next-meta {
  color: var(--c-text-2);
}

@keyframes season-ping {
  0% {
    opacity: 0.8;
    transform: scale(0.7);
  }
  100% {
    opacity: 0;
    transform: scale(1.7);
  }
}

@media (max-width: 520px) {
  .season__rail {
    --lamp: 14px;
  }

  .season__date {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .season__lamp,
  .season__stop.has-stretch::after {
    transition: none;
  }

  .season.is-armed .is-live .season__lamp::after {
    animation: none;
  }
}
</style>
