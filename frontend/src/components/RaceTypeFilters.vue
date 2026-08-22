<script setup>
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
        <label v-for="option in group.options" :key="option.key" class="race-type-filter-option">
          <input
            type="checkbox"
            :checked="modelValue[option.key]"
            :disabled="disabled"
            @change="updateFilter(option.key, $event.target.checked)"
          />
          <span>{{ t(option.label) }}</span>
        </label>
      </div>
    </fieldset>
  </div>
</template>
