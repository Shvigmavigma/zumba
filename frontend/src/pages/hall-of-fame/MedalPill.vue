<script setup>
// One medal count as a small coloured pill: gold, silver or bronze.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  tone: { type: String, required: true, validator: (value) => ['gold', 'silver', 'bronze'].includes(value) },
  value: { type: Number, default: 0 },
  size: { type: String, default: 'sm' }
})

const { t } = useI18n()
const label = computed(() => t(`hallPage.medals.${props.tone}`, { count: props.value }))
</script>

<template>
  <span class="medal ui-num" :class="[`is-${tone}`, `medal--${size}`, { 'is-zero': !value }]" :title="label" :aria-label="label">
    <i class="medal__disc" aria-hidden="true"></i>{{ value }}
  </span>
</template>

<style scoped>
.medal {
  --tone: var(--bm-gold);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-width: 46px;
  height: 26px;
  padding: 0 10px 0 7px;
  border: 1px solid color-mix(in srgb, var(--tone) 42%, transparent);
  border-radius: var(--r-pill);
  background: color-mix(in srgb, var(--tone) 14%, transparent);
  color: color-mix(in srgb, var(--tone) 72%, var(--c-text));
  font-size: 12.5px;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
  transition: transform var(--dur-2) var(--ease-spring), background-color var(--dur-2);
}

.medal--md {
  height: 30px;
  min-width: 52px;
  font-size: 13.5px;
}

.is-silver {
  --tone: var(--bm-silver);
}

.is-bronze {
  --tone: var(--bm-bronze);
}

.medal__disc {
  width: 10px;
  height: 10px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, #fff 0 12%, var(--tone) 46%, color-mix(in srgb, var(--tone) 60%, #000) 100%);
  box-shadow: 0 0 8px color-mix(in srgb, var(--tone) 60%, transparent);
}

.medal.is-zero {
  border-color: var(--c-line);
  background: transparent;
  color: var(--c-text-3);
}

.medal.is-zero .medal__disc {
  opacity: 0.35;
  box-shadow: none;
}

:root[data-theme='light'] .medal:not(.is-zero) {
  color: color-mix(in srgb, var(--tone) 45%, #1b1300);
}
</style>
