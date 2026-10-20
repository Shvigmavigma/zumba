<script setup>
// Filter (active / inactive / all) and the championships as glass cards. The
// blue selection glow glides between cards with a shared-layout spring.
import { computed, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import { motion } from 'motion-v'
import SegmentedControl from '../../ui/SegmentedControl.vue'
import { state } from '../../store'
import { formatInTimeZone } from '../../timezone'
import { pluralBucket, seasonProgress, statusKey, statusTone } from './helpers'

const props = defineProps({
  championships: { type: Array, default: () => [] },
  selected: { type: Object, default: null },
  /** Changes after every list load so the strip animates in afresh. */
  listKey: { type: Number, default: 0 }
})
const filter = defineModel('filter', { type: String, default: 'active' })
const selectedId = defineModel('selectedId', { type: Number, default: null })

const { t } = useI18n()
const glowId = `champ-glow-${useId()}`
const spring = { type: 'spring', stiffness: 420, damping: 36, mass: 0.9 }

const filterOptions = computed(() => [
  { value: 'active', label: t('championships.active') },
  { value: 'inactive', label: t('championships.inactive') },
  { value: 'all', label: t('championships.all') }
])

const MINE = {
  approved: { tone: 'green', key: 'champPage.picker.mineApproved' },
  pending: { tone: 'amber', key: 'champPage.picker.minePending' },
  rejected: { tone: 'red', key: 'champPage.picker.mineRejected' }
}

const cards = computed(() => props.championships.map((item) => {
  const season = seasonProgress(item.stages || [])
  const stageWord = t(`championships.stageWord${pluralBucket(season.total, state.locale)}`)
  return {
    id: item.id,
    name: item.name,
    game: item.game,
    tone: statusTone(item.status),
    live: item.status === 'registration_open' || item.status === 'active',
    status: statusKey(item.status) ? t(statusKey(item.status)) : item.status,
    meta: [(item.classes || []).join(' / '), `${season.total} ${stageWord}`, item.is_team_event ? t('champPage.team') : ''].filter(Boolean).join(' · '),
    dates: `${shortDay(item.championship_start)} — ${shortDay(item.championship_end)}`,
    finished: season.finished,
    total: season.total,
    percent: season.percent,
    mine: MINE[item.my_registration_status] || null,
    draft: !item.is_published
  }
}))

function shortDay(value) {
  return formatInTimeZone(value, { day: 'numeric', month: 'short' }).replace('.', '')
}
</script>

<template>
  <section class="picker" :aria-label="t('champPage.picker.aria')">
    <div class="picker__bar">
      <SegmentedControl v-model="filter" :options="filterOptions" :aria-label="t('championships.filterAria')" />
    </div>

    <Transition name="picker-swap" mode="out-in">
      <div v-if="cards.length" :key="listKey" class="picker__strip">
        <button
          v-for="(card, index) in cards"
          :key="card.id"
          v-reveal="{ delay: index * 60, y: 14, blur: 4, duration: 700 }"
          class="pick"
          :class="{ 'is-active': card.id === selected?.id }"
          type="button"
          :aria-pressed="card.id === selected?.id"
          @click="selectedId = card.id"
        >
          <motion.span v-if="card.id === selected?.id" class="pick__glow" :layoutId="glowId" :transition="spring" />
          <span class="pick__top">
            <span class="ui-chip ui-chip--solid">{{ card.game }}</span>
            <span class="pick__status">
              <span class="ui-dot" :class="[card.tone ? `ui-dot--${card.tone}` : '', { 'ui-dot--live': card.live }]"></span>
              <span class="pick__status-text">{{ card.status }}</span>
            </span>
          </span>
          <strong class="pick__name">{{ card.name }}</strong>
          <span class="pick__meta">{{ card.meta }}</span>
          <span class="pick__foot">
            <span class="pick__dates ui-num">{{ card.dates }}</span>
            <span class="pick__progress" :title="t('champPage.season.done', { done: card.finished, total: card.total })">
              <span class="ui-meter"><span :style="{ '--value': `${card.percent}%` }"></span></span>
              <span class="ui-num">{{ card.finished }}/{{ card.total }}</span>
            </span>
          </span>
          <span v-if="card.mine || card.draft" class="pick__badges">
            <span v-if="card.mine" class="ui-chip" :class="`ui-chip--${card.mine.tone}`">{{ t(card.mine.key) }}</span>
            <span v-if="card.draft" class="ui-chip ui-chip--amber">{{ t('champPage.unpublished') }}</span>
          </span>
        </button>
      </div>
    </Transition>
  </section>
</template>

<style scoped>
.picker {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.picker__bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.picker__strip {
  display: grid;
  grid-auto-columns: minmax(270px, 340px);
  grid-auto-flow: column;
  gap: 12px;
  margin: -6px calc(var(--gutter) * -1) 0;
  padding: 6px var(--gutter) 10px;
  overflow-x: auto;
  scroll-padding-inline: var(--gutter);
  scroll-snap-type: x mandatory;
  scrollbar-width: none;
}

.picker__strip::-webkit-scrollbar {
  display: none;
}

.pick {
  position: relative;
  display: grid;
  align-content: start;
  gap: 10px;
  min-width: 0;
  padding: 16px 18px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-lg);
  background: var(--c-surface);
  box-shadow: var(--shadow-1);
  color: var(--c-text);
  cursor: pointer;
  font: inherit;
  text-align: left;
  scroll-snap-align: start;
  isolation: isolate;
  -webkit-backdrop-filter: var(--glass-filter);
  backdrop-filter: var(--glass-filter);
  -webkit-tap-highlight-color: transparent;
  transition:
    transform var(--dur-3) var(--ease-ios),
    border-color var(--dur-2) var(--ease-out);
}

.pick:hover {
  border-color: var(--c-blue-line);
  transform: translateY(-3px);
}

.pick:active {
  transform: scale(0.985);
}

.pick.is-active {
  border-color: color-mix(in srgb, var(--bm-blue-bright) 70%, transparent);
}

.pick__glow {
  position: absolute;
  inset: -1px;
  z-index: -1;
  border-radius: inherit;
  background:
    radial-gradient(120% 90% at 0% 0%, color-mix(in srgb, var(--bm-blue) 34%, transparent), transparent 62%),
    color-mix(in srgb, var(--bm-blue) 10%, var(--c-surface-solid));
  box-shadow: 0 16px 40px color-mix(in srgb, var(--bm-blue) 30%, transparent), inset 0 1px 0 rgba(255, 255, 255, 0.12);
}

.pick__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

/* Only the words are cut short: the live dot's ring grows past the dot and must not be clipped. */
.pick__status {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
  color: var(--c-text-2);
  font-size: 12.5px;
}

.pick__status-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pick__name {
  display: -webkit-box;
  overflow: hidden;
  min-height: 2.5em;
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 700;
  line-height: 1.25;
  text-transform: uppercase;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

.pick__meta {
  overflow: hidden;
  color: var(--c-text-2);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pick__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.pick__dates {
  color: var(--c-text-3);
  font-size: 12px;
  white-space: nowrap;
}

.pick__progress {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--c-text-2);
  font-size: 12px;
}

.pick__progress .ui-meter {
  width: 64px;
}

.pick__badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.picker-swap-enter-active,
.picker-swap-leave-active {
  transition: opacity var(--dur-2) var(--ease-out), transform var(--dur-3) var(--ease-ios);
}

.picker-swap-enter-from {
  opacity: 0;
  transform: translateX(14px);
}

.picker-swap-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}

@media (max-width: 520px) {
  .picker__strip {
    grid-auto-columns: minmax(250px, 82vw);
  }
}

@media (prefers-reduced-motion: reduce) {
  .picker-swap-enter-active,
  .picker-swap-leave-active {
    transition: none;
  }
}
</style>
