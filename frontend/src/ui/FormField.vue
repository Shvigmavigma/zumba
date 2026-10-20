<script setup>
// Labelled form field: says what the field is for (hint), whether it is
// required, and shows validation feedback in place. The input itself is
// passed in through the default slot, which receives the ids to bind.
import { computed, useId } from 'vue'
import { AlertCircle, CheckCircle2 } from 'lucide-vue-next'

const props = defineProps({
  label: { type: String, required: true },
  hint: { type: String, default: '' },
  error: { type: String, default: '' },
  success: { type: String, default: '' },
  required: { type: Boolean, default: false },
  optionalLabel: { type: String, default: '' },
  icon: { type: [Object, Function], default: null },
  count: { type: Number, default: null },
  max: { type: Number, default: null }
})

const id = `field-${useId()}`
const hintId = `${id}-hint`
const messageId = `${id}-msg`
const describedBy = computed(() => [props.hint ? hintId : '', props.error || props.success ? messageId : ''].filter(Boolean).join(' ') || undefined)
</script>

<template>
  <div class="field" :class="{ 'has-error': error, 'has-success': success && !error, 'has-icon': icon }">
    <div class="field__top">
      <label class="field__label" :for="id">
        {{ label }}
        <span v-if="required" class="field__req" aria-hidden="true">*</span>
        <span v-else-if="optionalLabel" class="field__opt">{{ optionalLabel }}</span>
      </label>
      <span v-if="max" class="field__count ui-num" :class="{ 'is-near': count >= max * 0.9 }">{{ count ?? 0 }}/{{ max }}</span>
    </div>
    <div class="field__control">
      <component :is="icon" v-if="icon" class="field__icon" :size="18" aria-hidden="true" />
      <slot :id="id" :describedBy="describedBy" :invalid="Boolean(error)" />
    </div>
    <Transition name="ui-fade" mode="out-in">
      <p v-if="error" :id="messageId" :key="`e-${error}`" class="field__msg field__msg--error" role="alert"><AlertCircle :size="14" />{{ error }}</p>
      <p v-else-if="success" :id="messageId" :key="`s-${success}`" class="field__msg field__msg--ok"><CheckCircle2 :size="14" />{{ success }}</p>
    </Transition>
    <p v-if="hint" :id="hintId" class="field__hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.field {
  display: grid;
  align-content: start;
  gap: 8px;
  min-width: 0;
}

.field__top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.field__label {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  color: var(--c-text);
  font-size: 13.5px;
  font-weight: 600;
}

.field__req {
  color: var(--bm-blue-bright);
  font-weight: 700;
}

.field__opt {
  color: var(--c-text-3);
  font-size: 12px;
  font-weight: 500;
}

.field__count {
  color: var(--c-text-3);
  font-size: 11px;
}

.field__count.is-near {
  color: var(--bm-amber);
}

.field__control {
  position: relative;
  display: grid;
}

.field__icon {
  position: absolute;
  top: 50%;
  left: 14px;
  z-index: 1;
  color: var(--c-text-3);
  pointer-events: none;
  transform: translateY(-50%);
  transition: color var(--dur-2);
}

.field.has-icon :slotted(.ui-input),
.field.has-icon :slotted(.ui-select) {
  padding-left: 44px;
}

.field:focus-within .field__icon {
  color: var(--c-accent-text);
}

.field.has-success :slotted(.ui-input) {
  border-color: color-mix(in srgb, var(--bm-green) 55%, transparent);
}

.field__hint {
  margin: 0;
  color: var(--c-text-3);
  font-size: 12.5px;
  line-height: 1.45;
}

.field__msg {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  font-size: 12.5px;
  font-weight: 550;
}

.field__msg--error {
  color: color-mix(in srgb, var(--bm-red) 85%, var(--c-text));
}

.field__msg--ok {
  color: color-mix(in srgb, var(--bm-green) 85%, var(--c-text));
}
</style>
