<script setup>
import { Check } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  modelValue: { type: Object, required: true },
  disabled: { type: Boolean, default: false },
  className: { type: String, default: '' }
})
const emit = defineEmits(['update:modelValue'])
const { t } = useI18n()

const groups = [
  {
    label: 'raceFilters.qualificationGroup',
    options: [
      { key: 'qualificationTrue', label: 'raceFilters.withQualification' },
      { key: 'qualificationFalse', label: 'raceFilters.withoutQualification' }
    ]
  },
  {
    label: 'raceFilters.formatGroup',
    options: [
      { key: 'teamTrue', label: 'raceFilters.teamRace' },
      { key: 'teamFalse', label: 'raceFilters.soloRace' }
    ]
  },
  {
    label: 'raceFilters.officialGroup',
    options: [
      { key: 'officialTrue', label: 'raceFilters.officialRace' },
      { key: 'officialFalse', label: 'raceFilters.unofficialRace' }
    ]
  }
]

function updateFilter(key, checked) {
  emit('update:modelValue', { ...props.modelValue, [key]: checked })
}
</script>

<template>
  <!-- Static controls have no loading or empty state. -->
  <div class="race-type-filters" :class="className">
    <fieldset v-for="group in groups" :key="group.label" class="race-type-filter-group" :disabled="disabled">
      <legend>{{ t(group.label) }}</legend>
      <div class="race-type-filter-options">
        <label v-for="option in group.options" :key="option.key" class="race-type-filter-option" :class="{ 'is-checked': modelValue[option.key] }">
          <input
            type="checkbox"
            :checked="modelValue[option.key]"
            :disabled="disabled"
            @change="updateFilter(option.key, $event.target.checked)"
          />
          <span class="race-type-filter-box" aria-hidden="true"><Check :size="12" :stroke-width="3" /></span>
          <span>{{ t(option.label) }}</span>
        </label>
      </div>
    </fieldset>
  </div>
</template>

<style scoped>
.race-type-filters {
  display: grid;
  gap: 14px;
}

.race-type-filter-group {
  display: grid;
  gap: 8px;
  min-width: 0;
  margin: 0;
  padding: 0;
  border: 0;
}

.race-type-filter-group legend {
  margin-bottom: 8px;
  padding: 0;
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.race-type-filter-options {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.race-type-filter-option {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 36px;
  padding: 0 12px 0 8px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-pill);
  background: var(--c-sunken);
  color: var(--c-text-2);
  cursor: pointer;
  font-size: 13px;
  font-weight: 550;
  transition: border-color var(--dur-2), background-color var(--dur-2), color var(--dur-2);
}

.race-type-filter-option input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.race-type-filter-box {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border: 1px solid var(--c-line-strong);
  border-radius: 50%;
  color: transparent;
  transition: background-color var(--dur-2), color var(--dur-2), border-color var(--dur-2), transform 300ms var(--ease-spring);
}

.race-type-filter-option.is-checked {
  border-color: var(--c-blue-line);
  background: var(--c-blue-soft);
  color: var(--c-text);
}

.race-type-filter-option.is-checked .race-type-filter-box {
  border-color: var(--bm-blue);
  background: var(--bm-blue);
  color: #fff;
  transform: scale(1.05);
}

.race-type-filter-option:has(input:focus-visible) {
  outline: 2px solid var(--bm-blue-bright);
  outline-offset: 2px;
}

.race-type-filter-group:disabled .race-type-filter-option {
  cursor: not-allowed;
  opacity: 0.5;
}
</style>
