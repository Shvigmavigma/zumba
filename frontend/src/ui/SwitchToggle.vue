<script setup>
// iOS-style switch built on a native checkbox, so forms and keyboards work as usual.
defineProps({
  label: { type: String, default: '' },
  hint: { type: String, default: '' },
  disabled: { type: Boolean, default: false }
})
const model = defineModel({ type: Boolean, default: false })
</script>

<template>
  <label class="switch" :class="{ 'is-disabled': disabled }">
    <input v-model="model" class="switch__input" type="checkbox" role="switch" :disabled="disabled" />
    <span class="switch__track" aria-hidden="true"><span class="switch__thumb"></span></span>
    <span v-if="label || hint" class="switch__text">
      <span class="switch__label">{{ label }}</span>
      <small v-if="hint" class="switch__hint">{{ hint }}</small>
    </span>
  </label>
</template>

<style scoped>
.switch {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.switch.is-disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.switch__input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
}

.switch__track {
  position: relative;
  flex: 0 0 auto;
  width: 46px;
  height: 28px;
  border-radius: 99px;
  background: color-mix(in srgb, var(--c-text) 16%, transparent);
  box-shadow: inset 0 0 0 1px var(--c-line);
  transition: background-color 260ms var(--ease-out);
}

.switch__thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.3), 0 0 0 0.5px rgba(0, 0, 0, 0.04);
  transition: transform 420ms var(--ease-spring), width 200ms var(--ease-out);
}

.switch:active:not(.is-disabled) .switch__thumb {
  width: 28px;
}

.switch__input:checked + .switch__track {
  background: var(--bm-blue);
}

.switch__input:checked + .switch__track .switch__thumb {
  transform: translateX(18px);
}

.switch:active:not(.is-disabled) .switch__input:checked + .switch__track .switch__thumb {
  transform: translateX(14px);
}

.switch__input:focus-visible + .switch__track {
  outline: 2px solid var(--bm-blue-bright);
  outline-offset: 2px;
}

.switch__text {
  display: grid;
  gap: 2px;
}

.switch__label {
  color: var(--c-text);
  font-size: 13.5px;
  font-weight: 550;
}

.switch__hint {
  color: var(--c-text-3);
  font-size: 12px;
}
</style>
