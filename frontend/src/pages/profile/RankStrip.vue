<script setup>
// Overall rank in the profile hero: the crest, the tier name in its metal,
// the best RER, the whole ladder of tiers with this pilot's place on it and
// how far the next tier is, so the next goal is always in sight.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import RankEmblem from '../../ui/rank/RankEmblem.vue'
import { rankLadder } from '../../ranks'
import { state } from '../../store'

const props = defineProps({
  /** Result of overallRank() for the pilot. */
  rank: { type: Object, required: true },
  tiers: { type: Array, required: true }
})

const { t } = useI18n()
const ladder = computed(() => rankLadder(props.tiers))
const number = computed(() => new Intl.NumberFormat(state.locale === 'en' ? 'en-US' : 'ru-RU'))
</script>

<template>
  <div class="rstrip" :data-rank="rank.key" :title="t('profilePage.rank.hint')">
    <RankEmblem :rank="rank.key" :size="52" :label="rank.tier.name" />
    <div class="rstrip__main">
      <p class="rstrip__head">
        <span class="ui-eyebrow">{{ t('profilePage.rank.label') }}</span>
        <b class="rank-text rank-text--adaptive">{{ rank.tier.name }}</b>
        <span class="rstrip__value ui-num">{{ number.format(rank.rating) }} RER</span>
      </p>
      <ol class="rstrip__ladder" :aria-label="t('profilePage.rank.ladder')">
        <li
          v-for="step in ladder"
          :key="step.index"
          :data-rank="step.key"
          :class="{ 'is-done': step.index < rank.index, 'is-current': step.index === rank.index }"
          :title="`${step.name} · ${number.format(step.tier.min_rating)}+ RER`"
        >
          <span :style="step.index === rank.index ? { '--fill': `${Math.round(rank.progress * 100)}%` } : null"></span>
        </li>
      </ol>
      <p class="rstrip__next">
        {{ rank.next ? t('profilePage.rank.toNext', { name: rank.next.name, count: number.format(rank.toNext) }) : t('profilePage.rank.top') }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.rstrip {
  display: flex;
  align-items: center;
  gap: 14px;
  max-width: 520px;
  margin-top: 4px;
  padding: 12px 16px 12px 12px;
  border: 1px solid color-mix(in srgb, var(--rank-2) 34%, var(--c-line));
  border-radius: var(--r-lg);
  background:
    linear-gradient(100deg, color-mix(in srgb, var(--rank-2) 14%, transparent), transparent 60%),
    color-mix(in srgb, var(--c-surface-solid) 60%, transparent);
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
}

.rstrip__main {
  display: grid;
  flex: 1 1 auto;
  gap: 8px;
  min-width: 0;
}

.rstrip__head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 10px;
  margin: 0;
}

.rstrip__head b {
  font-family: var(--font-display);
  font-size: 19px;
  font-weight: 800;
  letter-spacing: 0.01em;
  text-transform: uppercase;
}

.rstrip__value {
  color: var(--c-text);
  font-size: 14px;
  font-weight: 600;
}

/* The tier ladder: earned steps in their metal, the current one filling up. */
.rstrip__ladder {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(0, 1fr);
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.rstrip__ladder li {
  height: 7px;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--rank-2) 45%, transparent);
  border-radius: 6px;
  background: color-mix(in srgb, var(--rank-2) 10%, transparent);
}

.rstrip__ladder li span {
  display: block;
  width: 0;
  height: 100%;
  background: var(--rank-metal);
}

.rstrip__ladder li.is-done span {
  width: 100%;
}

.rstrip__ladder li.is-current {
  box-shadow: 0 0 10px var(--rank-glow);
}

.rstrip__ladder li.is-current span {
  width: var(--fill, 0%);
  transition: width 1200ms var(--ease-ios);
}

.rstrip__next {
  margin: 0;
  color: var(--c-text-2);
  font-size: 12.5px;
}
</style>
