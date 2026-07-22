<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
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
      <span>{{ option.label }}</span>
    </label>
  </div>
</template>
