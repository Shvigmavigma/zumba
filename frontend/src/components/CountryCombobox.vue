<script setup>
import { Check, ChevronDown, Search } from 'lucide-vue-next'
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
  emptyLabel: {
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
  const maxHeight = Math.max(180, Math.min(320, window.innerHeight - top - 12))
  panelStyle.value = {
    left: `${rect.left}px`,
    top: `${top}px`,
    width: `${rect.width}px`,
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

function closeDropdown() {
  isOpen.value = false
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
    closeDropdown()
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
      class="country-combobox-trigger"
      type="button"
      :aria-expanded="isOpen"
      :aria-controls="listId"
      @click="toggleDropdown"
    >
      <span class="country-combobox-value" :class="{ 'is-placeholder': !selectedLabel }">
        {{ selectedLabel || placeholderText }}
      </span>
      <ChevronDown class="country-combobox-chevron" :size="18" />
    </button>

    <Teleport to="body">
      <div v-if="isOpen" ref="panel" class="country-combobox-panel" :style="panelStyle">
        <div class="country-combobox-search">
          <Search :size="16" />
          <input
            ref="searchInput"
            v-model="query"
            type="search"
            autocomplete="off"
            :placeholder="searchPlaceholderText"
          />
        </div>
        <button
          v-if="modelValue"
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
            :key="option.code"
            class="country-combobox-option"
            :class="{ 'is-active': index === activeIndex, 'is-selected': option.value === modelValue }"
            type="button"
            role="option"
            :aria-selected="option.value === modelValue"
            @mouseenter="activeIndex = index"
            @click="choose(option)"
          >
            <span class="country-combobox-option-main">{{ option.label }}</span>
            <span class="country-combobox-option-code">{{ option.code?.length === 2 ? option.code : '' }}</span>
            <Check v-if="option.value === modelValue" :size="16" />
          </button>
          <p v-if="!filteredOptions.length" class="country-combobox-empty">{{ emptyLabelText }}</p>
        </div>
      </div>
    </Teleport>
  </div>
</template>
