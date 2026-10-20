<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Check } from 'lucide-vue-next'
import { gameOptions } from '../i18nLabels'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue'])
const { t } = useI18n()
const options = computed(() => gameOptions(t))
const FULL_NAMES = {
  ACC: 'Assetto Corsa Competizione',
  AC: 'Assetto Corsa',
  iRacing: 'iRacing',
  LMU: 'Le Mans Ultimate'
}

function toggle(value) {
  const current = new Set(props.modelValue || [])
  if (current.has(value)) {
    if (current.size === 1) return
    current.delete(value)
  } else {
    current.add(value)
  }
  emit('update:modelValue', [...current])
}
</script>

<template>
  <div class="game-choice-group" role="group" :aria-label="t('fields.games')">
    <label v-for="option in options" :key="option.value" class="game-choice" :class="{ 'is-selected': modelValue?.includes(option.value) }">
      <input type="checkbox" :checked="modelValue?.includes(option.value)" :disabled="modelValue?.length === 1 && modelValue?.includes(option.value)" @change="toggle(option.value)" />
      <span class="game-choice-code">{{ option.label }}</span>
      <span class="game-choice-name">{{ FULL_NAMES[option.value] || option.label }}</span>
      <span class="game-choice-tick" aria-hidden="true"><Check :size="13" :stroke-width="3" /></span>
    </label>
  </div>
</template>

<style scoped>
.game-choice-group {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 8px;
}

.game-choice {
  position: relative;
  display: grid;
  gap: 4px;
  min-height: 76px;
  padding: 12px 14px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-md);
  background: var(--c-sunken);
  cursor: pointer;
  transition: border-color var(--dur-2), background-color var(--dur-2), transform var(--dur-3) var(--ease-ios);
}

.game-choice:hover {
  border-color: var(--c-blue-line);
}

.game-choice:active {
  transform: scale(0.98);
}

.game-choice input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.game-choice:has(input:focus-visible) {
  outline: 2px solid var(--bm-blue-bright);
  outline-offset: 2px;
}

.game-choice-code {
  color: var(--c-text);
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 800;
}

.game-choice-name {
  color: var(--c-text-3);
  font-size: 12px;
  line-height: 1.3;
}

.game-choice-tick {
  position: absolute;
  top: 10px;
  right: 10px;
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border: 1px solid var(--c-line-strong);
  border-radius: 50%;
  color: transparent;
  transition: background-color var(--dur-2), border-color var(--dur-2), color var(--dur-2), transform 320ms var(--ease-spring);
}

.game-choice.is-selected {
  border-color: var(--bm-blue);
  background: color-mix(in srgb, var(--bm-blue) 14%, var(--c-sunken));
  box-shadow: inset 0 0 0 1px var(--bm-blue);
}

.game-choice.is-selected .game-choice-tick {
  border-color: var(--bm-blue);
  background: var(--bm-blue);
  color: #fff;
  transform: scale(1.06);
}
</style>
