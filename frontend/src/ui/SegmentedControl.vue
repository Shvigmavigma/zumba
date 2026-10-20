<script setup>
// iOS-style segmented control. The selection pill glides between options with a
// shared-layout spring from Motion (the Kokonut UI "smooth tab" idea).
import { useId } from 'vue'
import { motion } from 'motion-v'

const props = defineProps({
  modelValue: { type: [String, Number, Boolean], default: null },
  /** [{ value, label, icon?, count?, badge? }] */
  options: { type: Array, required: true },
  size: { type: String, default: 'md' },
  block: { type: Boolean, default: false },
  ariaLabel: { type: String, default: '' }
})
const emit = defineEmits(['update:modelValue'])
const pillId = `segment-${useId()}`
const spring = { type: 'spring', stiffness: 520, damping: 38, mass: 0.9 }

function select(value) {
  if (value !== props.modelValue) emit('update:modelValue', value)
}

function onKeydown(event, index) {
  const keys = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }
  if (!keys[event.key]) return
  event.preventDefault()
  const next = (index + keys[event.key] + props.options.length) % props.options.length
  select(props.options[next].value)
  event.currentTarget.parentElement?.children[next]?.focus()
}
</script>

<template>
  <div class="segmented" :class="[`segmented--${size}`, { 'segmented--block': block }]" role="tablist" :aria-label="ariaLabel">
    <button
      v-for="(option, index) in options"
      :key="String(option.value)"
      class="segmented__option"
      :class="{ 'is-active': option.value === modelValue }"
      type="button"
      role="tab"
      :aria-selected="option.value === modelValue"
      :tabindex="option.value === modelValue ? 0 : -1"
      @click="select(option.value)"
      @keydown="onKeydown($event, index)"
    >
      <motion.span v-if="option.value === modelValue" class="segmented__pill" :layoutId="pillId" :transition="spring" />
      <span class="segmented__label">
        <span v-if="option.badge" class="segmented__badge">{{ option.badge }}</span>
        <component :is="option.icon" v-if="option.icon" :size="15" aria-hidden="true" />
        {{ option.label }}
        <span v-if="option.count !== undefined && option.count !== null" class="segmented__count">{{ option.count }}</span>
      </span>
    </button>
  </div>
</template>

<style scoped>
.segmented {
  position: relative;
  display: inline-flex;
  align-items: stretch;
  gap: 2px;
  max-width: 100%;
  padding: 4px;
  overflow-x: auto;
  border: 1px solid var(--c-line);
  border-radius: var(--r-pill);
  background: var(--c-sunken);
  scrollbar-width: none;
}

.segmented::-webkit-scrollbar {
  display: none;
}

.segmented--block {
  display: flex;
  width: 100%;
}

.segmented--block .segmented__option {
  flex: 1 1 0;
}

.segmented__option {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 36px;
  padding: 0 16px;
  border: 0;
  border-radius: var(--r-pill);
  background: transparent;
  color: var(--c-text-2);
  cursor: pointer;
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  transition: color var(--dur-2) var(--ease-out);
  -webkit-tap-highlight-color: transparent;
}

.segmented--sm .segmented__option {
  min-height: 30px;
  padding: 0 12px;
  font-size: 12px;
}

.segmented__option:hover {
  color: var(--c-text);
}

.segmented__option.is-active {
  color: #fff;
}

.segmented__option:focus-visible {
  outline-offset: -2px;
}

.segmented__pill {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: var(--bm-blue);
  box-shadow: 0 6px 18px color-mix(in srgb, var(--bm-blue) 45%, transparent), inset 0 1px 0 rgba(255, 255, 255, 0.22);
}

.segmented__label {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.segmented__badge {
  padding: 2px 6px;
  border-radius: 6px;
  background: color-mix(in srgb, var(--bm-red) 85%, #000);
  color: #fff;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.segmented__count {
  min-width: 20px;
  padding: 2px 6px;
  border-radius: var(--r-pill);
  background: color-mix(in srgb, currentColor 16%, transparent);
  font-family: var(--font-mono);
  font-size: 11px;
  text-align: center;
}
</style>
