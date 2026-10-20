<script setup>
// Stewards' decisions for this race: how many penalties were issued, how many
// are yours, and the way into the full list (where appeals are filed).
import { useI18n } from 'vue-i18n'
import { Gavel, Scale } from 'lucide-vue-next'
import CountUp from '../../ui/fx/CountUp.vue'

defineProps({
  count: { type: Number, default: 0 },
  ownCount: { type: Number, default: 0 },
  canIssue: { type: Boolean, default: false }
})
const emit = defineEmits(['open', 'issue'])
const { t } = useI18n()
</script>

<template>
  <section class="pen ui-card" aria-labelledby="race-pen-title">
    <header class="ui-card__head">
      <div class="ui-card__title">
        <p class="ui-eyebrow ui-eyebrow--accent">{{ t('racePage.penalties.eyebrow') }}</p>
        <h2 id="race-pen-title">{{ t('racePage.penalties.title') }}</h2>
      </div>
      <span class="pen__icon" aria-hidden="true"><Scale :size="20" /></span>
    </header>

    <div class="pen__stats">
      <div class="pen__stat">
        <CountUp class="pen__value" :value="count" />
        <span>{{ t('racePage.penalties.total') }}</span>
      </div>
      <div class="pen__stat" :class="{ 'is-alert': ownCount > 0 }">
        <CountUp class="pen__value" :value="ownCount" />
        <span>{{ t('racePage.penalties.own') }}</span>
      </div>
    </div>

    <p class="pen__text">{{ ownCount ? t('racePage.penalties.ownHint') : t('racePage.penalties.hint') }}</p>

    <div class="pen__actions">
      <button class="ui-btn ui-btn--outline" type="button" @click="emit('open')">
        <Scale :size="16" />{{ t('raceDetails.openPenalties') }}
      </button>
      <button v-if="canIssue" class="ui-btn ui-btn--danger" type="button" @click="emit('issue')">
        <Gavel :size="16" />{{ t('raceDetails.issuePenalty') }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.pen__icon {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border: 1px solid var(--c-blue-line);
  border-radius: 13px;
  background: var(--c-blue-soft);
  color: var(--c-accent-text);
}

.pen__stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.pen__stat {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  background: var(--c-sunken);
}

.pen__stat span {
  color: var(--c-text-3);
  font-size: 12.5px;
}

.pen__value {
  color: var(--c-text);
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}

.pen__stat.is-alert {
  border-color: color-mix(in srgb, var(--bm-red) 36%, transparent);
  background: color-mix(in srgb, var(--bm-red) 9%, transparent);
}

.pen__stat.is-alert .pen__value {
  color: color-mix(in srgb, var(--bm-red) 85%, var(--c-text));
}

.pen__text {
  margin: 0;
  color: var(--c-text-2);
  font-size: 13.5px;
  line-height: 1.5;
}

.pen__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pen__actions .ui-btn {
  flex: 1 1 auto;
}
</style>
