<script setup>
import { Check, ChevronDown, Search, SearchX } from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  options: {
    type: Array,
    default: () => []
  },
  placeholder: {
    type: String,
    default: ''
  },
  searchPlaceholder: {
    type: String,
    default: ''
  },
  clearLabel: {
    type: String,
    default: ''
  },
  clearable: {
    type: Boolean,
    default: true
  },
  emptyLabel: {
    type: String,
    default: ''
  },
  leadingIcon: {
    type: Object,
    default: null
  },
  panelWidth: {
    type: Number,
    default: null
  },
  panelClass: {
    type: String,
    default: ''
  },
  triggerAriaLabel: {
    type: String,
    default: ''
  },
  // Lets a surrounding <label for> and field hint point at the trigger button.
  triggerId: {
    type: String,
    default: ''
  },
  describedBy: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue'])
const { t } = useI18n()

const root = ref(null)
const panel = ref(null)
const searchInput = ref(null)
const isOpen = ref(false)
const query = ref('')
const activeIndex = ref(0)
const panelStyle = ref({})
const listId = `country-list-${Math.random().toString(36).slice(2)}`

const selectedOption = computed(() => props.options.find((option) => option.value === props.modelValue))
const selectedLabel = computed(() => selectedOption.value?.label || props.modelValue || '')
const placeholderText = computed(() => props.placeholder || t('country.placeholder'))
const searchPlaceholderText = computed(() => props.searchPlaceholder || t('country.searchPlaceholder'))
const clearLabelText = computed(() => props.clearLabel || t('country.clearLabel'))
const emptyLabelText = computed(() => props.emptyLabel || t('country.emptyLabel'))

function normalizeSearch(value) {
  return String(value || '')
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase()
}

function matchScore(option, needle) {
  const label = normalizeSearch(option.label)
  const value = normalizeSearch(option.value)
  const code = normalizeSearch(option.code)
  if (code === needle) return 0
  if (label.startsWith(needle)) return 1
  if (value.startsWith(needle)) return 2
  if (label.includes(` ${needle}`)) return 3
  if (value.includes(` ${needle}`)) return 4
  if (label.includes(needle)) return 5
  if (value.includes(needle)) return 6
  if (code.includes(needle)) return 7
  return Number.POSITIVE_INFINITY
}

const filteredOptions = computed(() => {
  const needle = normalizeSearch(query.value.trim())
  if (!needle) return props.options

  return props.options
    .map((option) => ({ option, score: matchScore(option, needle) }))
    .filter((item) => Number.isFinite(item.score))
    .sort((a, b) => a.score - b.score || a.option.label.localeCompare(b.option.label, undefined, { sensitivity: 'base' }))
    .map((item) => item.option)
})

function optionId(index) {
  return `${listId}-option-${index}`
}

function updatePanelPosition() {
  const rect = root.value?.getBoundingClientRect()
  if (!rect) return

  const gap = 6
  const top = rect.bottom + gap
  const width = Math.min(props.panelWidth || rect.width, window.innerWidth - 24)
  const left = Math.max(12, Math.min(rect.right - width, window.innerWidth - width - 12))
  const maxHeight = Math.max(180, Math.min(320, window.innerHeight - top - 12))
  panelStyle.value = {
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    maxHeight: `${maxHeight}px`
  }
}

function focusSearch() {
  nextTick(() => {
    updatePanelPosition()
    searchInput.value?.focus()
  })
}

function selectedIndexInFiltered() {
  const index = filteredOptions.value.findIndex((option) => option.value === props.modelValue)
  return index >= 0 ? index : 0
}

function openDropdown() {
  if (isOpen.value) {
    focusSearch()
    return
  }
  query.value = ''
  activeIndex.value = selectedIndexInFiltered()
  isOpen.value = true
  focusSearch()
}

function closeDropdown(restoreFocus = false) {
  isOpen.value = false
  if (restoreFocus) nextTick(() => root.value?.querySelector('button')?.focus())
}

function toggleDropdown() {
  if (isOpen.value) {
    closeDropdown()
  } else {
    openDropdown()
  }
}

function choose(option) {
  if (!option) return
  emit('update:modelValue', option.value)
  closeDropdown()
  nextTick(() => root.value?.querySelector('button')?.focus())
}

function clearCountry() {
  emit('update:modelValue', '')
  closeDropdown()
  nextTick(() => root.value?.querySelector('button')?.focus())
}

function moveActive(step) {
  if (!isOpen.value) {
    openDropdown()
    return
  }
  const count = filteredOptions.value.length
  if (!count) return
  activeIndex.value = (activeIndex.value + step + count) % count
  nextTick(() => {
    const active = panel.value?.querySelector(`#${CSS.escape(optionId(activeIndex.value))}`)
    active?.scrollIntoView({ block: 'nearest' })
    if (document.activeElement?.classList.contains('country-combobox-option')) active?.focus()
  })
}

function handleKeydown(event) {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    moveActive(1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    moveActive(-1)
  } else if (event.key === 'Enter' && isOpen.value) {
    event.preventDefault()
    choose(filteredOptions.value[activeIndex.value])
  } else if (event.key === 'Escape') {
    event.preventDefault()
    closeDropdown(true)
  }
}

function handleDocumentPointerDown(event) {
  const target = event.target
  if (root.value?.contains(target) || panel.value?.contains(target)) return
  closeDropdown()
}

function addListeners() {
  document.addEventListener('pointerdown', handleDocumentPointerDown, true)
  window.addEventListener('resize', updatePanelPosition)
  document.addEventListener('scroll', updatePanelPosition, true)
}

function removeListeners() {
  document.removeEventListener('pointerdown', handleDocumentPointerDown, true)
  window.removeEventListener('resize', updatePanelPosition)
  document.removeEventListener('scroll', updatePanelPosition, true)
}

watch(isOpen, (open) => {
  if (open) {
    addListeners()
    updatePanelPosition()
  } else {
    removeListeners()
  }
})

watch(filteredOptions, () => {
  activeIndex.value = Math.min(activeIndex.value, Math.max(filteredOptions.value.length - 1, 0))
})

onBeforeUnmount(removeListeners)
</script>

<template>
  <div ref="root" class="country-combobox" :class="{ 'is-open': isOpen }" @keydown="handleKeydown">
    <button
      :id="triggerId || undefined"
      class="country-combobox-trigger"
      type="button"
      :aria-describedby="describedBy || undefined"
      :aria-label="triggerAriaLabel || selectedLabel"
      aria-haspopup="dialog"
      :aria-expanded="isOpen"
      :aria-controls="listId"
      @click="toggleDropdown"
    >
      <component :is="leadingIcon" v-if="leadingIcon" class="country-combobox-leading" :size="16" aria-hidden="true" />
      <span class="country-combobox-value" :class="{ 'is-placeholder': !selectedLabel }">
        {{ selectedLabel || placeholderText }}
      </span>
      <ChevronDown class="country-combobox-chevron" :size="18" />
    </button>

    <Teleport to="body">
      <div v-if="isOpen" ref="panel" class="country-combobox-panel" :class="[panelClass, { 'has-clear': clearable && modelValue }]" :style="panelStyle" role="dialog" :aria-label="triggerAriaLabel || selectedLabel" @keydown="handleKeydown">
        <div class="country-combobox-search">
          <Search :size="16" />
          <input
            ref="searchInput"
            v-model="query"
            type="search"
            autocomplete="off"
            role="combobox"
            aria-autocomplete="list"
            :aria-label="searchPlaceholderText"
            :aria-expanded="isOpen"
            :aria-controls="listId"
            :aria-activedescendant="filteredOptions.length ? optionId(activeIndex) : undefined"
            :placeholder="searchPlaceholderText"
          />
        </div>
        <button
          v-if="clearable && modelValue"
          class="country-combobox-clear"
          type="button"
          @click="clearCountry"
        >
          {{ clearLabelText }}
        </button>
        <div :id="listId" class="country-combobox-list" role="listbox">
          <button
            v-for="(option, index) in filteredOptions"
            :id="optionId(index)"
            :key="option.value"
            class="country-combobox-option"
            :class="{ 'is-active': index === activeIndex, 'is-selected': option.value === modelValue }"
            type="button"
            role="option"
            :aria-selected="option.value === modelValue"
            @mouseenter="activeIndex = index"
            @focus="activeIndex = index"
            @click="choose(option)"
          >
            <span class="country-combobox-option-main">{{ option.label }}</span>
            <span class="country-combobox-option-code">{{ option.code?.length === 2 ? option.code : '' }}</span>
            <Check v-if="option.value === modelValue" :size="16" />
          </button>
          <div v-if="!filteredOptions.length" class="country-combobox-empty" role="status">
            <SearchX :size="18" aria-hidden="true" />
            <span>{{ emptyLabelText }}</span>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.country-combobox {
  position: relative;
  min-width: 0;
}

.country-combobox-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
  min-height: 48px;
  padding: 0 14px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-md);
  background: var(--c-sunken);
  color: var(--c-text);
  cursor: pointer;
  font-family: var(--font-body);
  font-size: 15px;
  text-align: left;
  transition: border-color var(--dur-2), box-shadow var(--dur-2);
}

.country-combobox-trigger:hover {
  border-color: color-mix(in srgb, var(--bm-blue) 30%, var(--c-line-strong));
}

.country-combobox.is-open .country-combobox-trigger,
.country-combobox-trigger:focus-visible {
  border-color: var(--bm-blue-bright);
  outline: none;
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--bm-blue) 22%, transparent);
}

.country-combobox-value {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.country-combobox-value.is-placeholder {
  color: var(--c-text-3);
}

.country-combobox-chevron {
  flex: 0 0 auto;
  color: var(--c-text-3);
  transition: transform var(--dur-3) var(--ease-ios);
}

.country-combobox.is-open .country-combobox-chevron {
  transform: rotate(180deg);
}

.country-combobox-panel {
  position: fixed;
  z-index: 130;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  gap: 6px;
  min-width: 240px;
  padding: 8px;
  overflow: hidden;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-lg);
  background: var(--c-surface-2);
  box-shadow: var(--shadow-2);
  -webkit-backdrop-filter: var(--glass-filter);
  backdrop-filter: var(--glass-filter);
  animation: country-pop 280ms var(--ease-ios);
}

@keyframes country-pop {
  from {
    opacity: 0;
    transform: translateY(-6px) scale(0.98);
  }
}

.country-combobox-search {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-sm);
  background: var(--c-sunken);
  color: var(--c-text-3);
}

/* The legacy sheet pins the icon absolutely over the input; here it is a flex item. */
.country-combobox-search svg {
  position: static;
  flex: none;
}

.country-combobox-search input {
  flex: 1 1 auto;
  min-width: 0;
  height: 38px;
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
  color: var(--c-text);
  font-size: 14px;
  outline: none;
}

.country-combobox-search input:focus {
  box-shadow: none;
}

.country-combobox-clear {
  min-height: 34px;
  padding: 0 10px;
  border: 0;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--c-accent-text);
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  text-align: left;
}

.country-combobox-clear:hover {
  background: var(--c-blue-soft);
}

.country-combobox-list {
  display: grid;
  align-content: start;
  gap: 2px;
  overflow-y: auto;
}

.country-combobox-option {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto 16px;
  align-items: center;
  gap: 8px;
  min-height: 38px;
  padding: 0 10px;
  border: 0;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--c-text);
  cursor: pointer;
  font-size: 14px;
  text-align: left;
}

.country-combobox-option.is-active {
  background: var(--c-blue-soft);
}

.country-combobox-option.is-selected {
  color: var(--c-accent-text);
  font-weight: 600;
}

.country-combobox-option-code {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 11px;
}

.country-combobox-leading {
  flex: none;
  color: var(--c-text-3);
}

.country-combobox-empty {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  padding: 12px 10px;
  color: var(--c-text-3);
  font-size: 13px;
}
</style>
