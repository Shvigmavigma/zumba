<script setup>
// Classification card: race / qualification tabs, the podium for P1–P3 and
// the timing table from P4. Switching tabs cross-fades the whole board.
// "All information" asks the page for its whole width (the side panels leave)
// and then unfolds every column of the table.
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Flag, Maximize2, Minimize2, Timer } from 'lucide-vue-next'
import EmptyState from '../../ui/EmptyState.vue'
import SegmentedControl from '../../ui/SegmentedControl.vue'
import ResultsPodium from './ResultsPodium.vue'
import ResultsTable from './ResultsTable.vue'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  tabOptions: { type: Array, default: () => [] },
  showTabs: { type: Boolean, default: false },
  showQualiColumn: { type: Boolean, default: false },
  canOpenPenalties: { type: Boolean, default: false },
  status: { type: String, default: '' }
})
const emit = defineEmits(['open-penalty'])
const tab = defineModel('tab', { type: String, default: 'race' })
/** The card has the whole width of the page and the table every column. */
const expanded = defineModel('expanded', { type: Boolean, default: false })
const { t } = useI18n()

/** On a wide screen the card first grows into the side panels' place (RaceLayout); the columns follow once it is nearly there. */
const UNFOLD_AFTER_MS = 460
const WIDE_LAYOUT = '(min-width: 1181px)'
const hasTable = computed(() => props.rows.length > 3)
const detailed = ref(expanded.value)
let unfoldTimer = 0

function growsFirst() {
  return window.matchMedia(WIDE_LAYOUT).matches && !window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

watch(expanded, (on) => {
  window.clearTimeout(unfoldTimer)
  // Folding back, the extra columns go at once: the card is about to be narrow again.
  if (!on) detailed.value = false
  else unfoldTimer = window.setTimeout(() => { detailed.value = true }, growsFirst() ? UNFOLD_AFTER_MS : 0)
})
onBeforeUnmount(() => window.clearTimeout(unfoldTimer))

const fastest = computed(() => props.rows.find((row) => row.isFastest) || null)
const emptyTitle = computed(() => (props.status === 'finished' ? t('raceDetails.noResults') : t('racePage.results.pending')))
</script>

<template>
  <section id="race-results" class="results ui-card" aria-labelledby="race-results-title">
    <header class="ui-card__head">
      <div class="ui-card__title">
        <p class="ui-eyebrow ui-eyebrow--accent">{{ t('racePage.results.eyebrow') }}</p>
        <h2 id="race-results-title">{{ t('raceDetails.results') }}</h2>
      </div>
      <div class="results__tools">
        <SegmentedControl v-if="showTabs" v-model="tab" :options="tabOptions" size="sm" :aria-label="t('raceDetails.results')" />
        <span v-else-if="rows.length" class="ui-chip ui-num">{{ rows.length }}</span>
        <button
          v-if="hasTable || expanded"
          class="ui-btn ui-btn--sm results__all"
          :class="expanded ? 'ui-btn--outline' : 'ui-btn--primary'"
          type="button"
          :aria-pressed="expanded"
          aria-controls="race-results-table"
          @click="expanded = !expanded"
        >
          <component :is="expanded ? Minimize2 : Maximize2" :size="15" />
          {{ expanded ? t('racePage.results.lessInfo') : t('racePage.results.allInfo') }}
        </button>
      </div>
    </header>

    <Transition name="results-swap" mode="out-in">
      <div v-if="rows.length" :key="tab" class="results__board">
        <p v-if="fastest" class="results__legend">
          <span class="results__fastest"><Timer :size="13" />{{ t('racePage.results.fastestLap') }}</span>
          <strong class="ui-num">{{ fastest.bestLap }}</strong>
          <span class="ui-faint">{{ fastest.name }}</span>
        </p>
        <ResultsPodium :rows="rows.slice(0, 3)" :mode="tab" />
        <ResultsTable
          v-if="rows.length > 3"
          :rows="rows.slice(3)"
          :mode="tab"
          :show-quali-column="showQualiColumn"
          :detailed="detailed"
          :can-open-penalties="canOpenPenalties"
          @open-penalty="emit('open-penalty', $event)"
        />
      </div>
      <EmptyState v-else key="empty" :icon="Flag" :title="emptyTitle" :text="status === 'finished' ? '' : t('racePage.results.pendingText')" />
    </Transition>
  </section>
</template>

<style scoped>
.results {
  scroll-margin-top: calc(var(--header-h) + 16px);
}

.results__tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.results__all {
  flex: none;
}

.results__board {
  display: grid;
  gap: 18px;
}

.results__legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 12px;
  margin: 0;
  color: var(--c-text-2);
  font-size: 13px;
}

.results__fastest {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border: 1px solid color-mix(in srgb, #a855f7 40%, transparent);
  border-radius: var(--r-pill);
  background: color-mix(in srgb, #a855f7 12%, transparent);
  color: #c084fc;
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

:root[data-theme='light'] .results__fastest {
  color: #7e22ce;
}

.results__legend strong {
  color: var(--c-text);
  font-size: 14px;
}

.results-swap-enter-active,
.results-swap-leave-active {
  transition: opacity var(--dur-2) var(--ease-out), transform var(--dur-3) var(--ease-ios), filter var(--dur-2) var(--ease-out);
}

.results-swap-enter-from {
  opacity: 0;
  filter: blur(8px);
  transform: translateY(14px) scale(0.99);
}

.results-swap-leave-to {
  opacity: 0;
  filter: blur(4px);
  transform: translateY(-8px);
}

@media (prefers-reduced-motion: reduce) {
  .results-swap-enter-active,
  .results-swap-leave-active {
    transition: none;
  }
}
</style>
