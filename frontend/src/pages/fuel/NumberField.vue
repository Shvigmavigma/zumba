<script setup>
// Numeric input for the fuel calculator: label and hint via FormField, the unit
// inside the field and iOS-style −/+ steppers that are easy to hit on a phone.
// The inner input is type="number", so v-model casts to a number exactly like
// v-model.number and keeps '' for an empty field.
import { useI18n } from 'vue-i18n'
import { Minus, Plus } from 'lucide-vue-next'
import FormField from '../../ui/FormField.vue'

const props = defineProps({
  label: { type: String, required: true },
  hint: { type: String, default: '' },
  unit: { type: String, default: '' },
  min: { type: [Number, String], default: null },
  max: { type: [Number, String], default: null },
  step: { type: [Number, String], default: 1 },
  /** Amount one stepper tap adds or removes. */
  nudge: { type: Number, default: 1 },
  placeholder: { type: String, default: '' },
  inputmode: { type: String, default: 'decimal' }
})
const model = defineModel({ type: [Number, String], default: '' })
const { t } = useI18n()

function bounded(value) {
  const low = props.min === null ? -Infinity : Number(props.min)
  const high = props.max === null ? Infinity : Number(props.max)
  return Math.min(high, Math.max(low, value))
}

function nudgeBy(direction) {
  const current = Number(model.value) || 0
  model.value = Number(bounded(current + direction * props.nudge).toFixed(3))
}
</script>

<template>
  <FormField :label="label" :hint="hint" v-slot="{ id, describedBy }">
    <span class="num">
      <input
        :id="id"
        v-model="model"
        class="ui-input num__input"
        type="number"
        :inputmode="inputmode"
        :min="min"
        :max="max"
        :step="step"
        :placeholder="placeholder"
        :aria-describedby="describedBy"
      />
      <span v-if="unit" class="num__unit" aria-hidden="true">{{ unit }}</span>
      <span class="num__steps">
        <button class="num__step" type="button" :aria-label="t('fuelPage.decrease', { label })" @click="nudgeBy(-1)"><Minus :size="15" /></button>
        <button class="num__step" type="button" :aria-label="t('fuelPage.increase', { label })" @click="nudgeBy(1)"><Plus :size="15" /></button>
      </span>
    </span>
  </FormField>
</template>

<style scoped>
.num {
  position: relative;
  display: flex;
  align-items: center;
  min-width: 0;
}

.num__input {
  padding-right: 118px;
  font-family: var(--font-mono);
  font-size: 16px;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  -moz-appearance: textfield;
  appearance: textfield;
}

.num__input::-webkit-inner-spin-button,
.num__input::-webkit-outer-spin-button {
  margin: 0;
  -webkit-appearance: none;
  appearance: none;
}

.num__input::placeholder {
  color: var(--c-text-3);
  font-weight: 500;
}

.num__unit {
  position: absolute;
  right: 82px;
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  pointer-events: none;
}

.num__steps {
  position: absolute;
  top: 6px;
  right: 6px;
  bottom: 6px;
  display: flex;
  overflow: hidden;
  border: 1px solid var(--c-line);
  border-radius: 11px;
  background: var(--c-surface-2);
}

.num__step {
  display: grid;
  place-items: center;
  width: 34px;
  min-height: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--c-text-2);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: background-color var(--dur-1), color var(--dur-1), transform var(--dur-2) var(--ease-spring);
}

.num__step + .num__step {
  border-left: 1px solid var(--c-line);
}

.num__step:hover {
  background: var(--c-blue-soft);
  color: var(--c-text);
}

.num__step:active {
  background: color-mix(in srgb, var(--bm-blue) 28%, transparent);
  color: #fff;
}

.num__step:active svg {
  transform: scale(0.85);
}

.num__step:focus-visible {
  outline-offset: -2px;
}
</style>
