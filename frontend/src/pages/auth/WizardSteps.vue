<script setup>
// Step indicator for the registration wizard. Finished steps can be revisited;
// the connecting line fills as the pilot moves forward.
import { Check } from 'lucide-vue-next'

defineProps({
  /** [{ key, title, text, done }] */
  steps: { type: Array, required: true },
  current: { type: Number, required: true }
})
defineEmits(['select'])
</script>

<template>
  <ol class="steps" :style="{ '--progress': current / Math.max(1, steps.length - 1) }">
    <li v-for="(step, index) in steps" :key="step.key" class="steps__item" :class="{ 'is-current': index === current, 'is-done': step.done && index !== current }">
      <button class="steps__button" type="button" :disabled="index > current && !step.done" :aria-current="index === current ? 'step' : undefined" @click="$emit('select', index)">
        <span class="steps__dot">
          <Check v-if="step.done && index !== current" :size="15" :stroke-width="3" />
          <span v-else class="ui-num">{{ index + 1 }}</span>
        </span>
        <span class="steps__text">
          <b>{{ step.title }}</b>
          <small>{{ step.text }}</small>
        </span>
      </button>
    </li>
  </ol>
</template>

<style scoped>
.steps {
  position: relative;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.steps::before,
.steps::after {
  position: absolute;
  top: 18px;
  /* From the centre of the first dot to the centre of the last one. */
  left: calc((100% - 24px) / 8);
  height: 2px;
  border-radius: 2px;
  content: '';
}

.steps::before {
  right: calc((100% - 24px) / 8);
  background: var(--c-line-strong);
}

.steps::after {
  width: calc((75% + 6px) * var(--progress));
  background: linear-gradient(90deg, var(--bm-blue), var(--bm-cyan));
  box-shadow: 0 0 10px color-mix(in srgb, var(--bm-cyan) 60%, transparent);
  transition: width 700ms var(--ease-ios);
}

.steps__item {
  position: relative;
  z-index: 1;
  min-width: 0;
}

.steps__button {
  display: grid;
  justify-items: center;
  gap: 8px;
  width: 100%;
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  cursor: pointer;
  text-align: center;
}

.steps__button:disabled {
  cursor: default;
}

.steps__dot {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border: 1px solid var(--c-line-strong);
  border-radius: 50%;
  background: var(--c-surface-solid);
  color: var(--c-text-3);
  font-size: 13px;
  font-weight: 700;
  transition: background-color var(--dur-3), border-color var(--dur-3), color var(--dur-3), transform 420ms var(--ease-spring), box-shadow var(--dur-3);
}

.is-current .steps__dot {
  border-color: var(--bm-blue);
  background: var(--bm-blue);
  color: #fff;
  box-shadow: 0 0 0 5px color-mix(in srgb, var(--bm-blue) 22%, transparent);
  transform: scale(1.06);
}

.is-done .steps__dot {
  border-color: color-mix(in srgb, var(--bm-green) 60%, transparent);
  background: color-mix(in srgb, var(--bm-green) 18%, var(--c-surface-solid));
  color: var(--bm-green);
}

.steps__text {
  display: grid;
  justify-items: center;
  gap: 2px;
  min-width: 0;
}

.steps__text b {
  overflow: hidden;
  color: var(--c-text-2);
  font-size: 13px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.is-current .steps__text b {
  color: var(--c-text);
}

.steps__text small {
  overflow: hidden;
  color: var(--c-text-3);
  font-size: 11.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 560px) {
  .steps__text small {
    display: none;
  }

  .steps__text b {
    font-size: 11.5px;
  }
}
</style>
