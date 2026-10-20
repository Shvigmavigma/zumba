<script setup>
// Searchable car list for the fuel calculator. Typing filters the list (the
// parent does the filtering), focus opens it, a pick fills the field.
// Arrow keys and Enter work as well as the mouse.
import { computed, ref, useId, watch } from 'vue'
import { Check, ChevronDown, Search } from 'lucide-vue-next'

const props = defineProps({
  /** Cars to show: [{ label, class }]. */
  options: { type: Array, required: true },
  /** Label of the selected car. */
  selected: { type: String, default: '' },
  inputId: { type: String, default: '' },
  describedBy: { type: String, default: undefined },
  placeholder: { type: String, default: '' },
  emptyText: { type: String, default: '' }
})
const emit = defineEmits(['select'])
const search = defineModel({ type: String, default: '' })

const listId = `car-list-${useId()}`
const open = ref(false)
const active = ref(-1)
const activeId = computed(() => (open.value && active.value >= 0 ? `${listId}-${active.value}` : undefined))

watch(() => props.options, () => {
  active.value = -1
})

function openList(event) {
  open.value = true
  event?.target?.select?.()
}

function closeList() {
  window.setTimeout(() => {
    open.value = false
  }, 120)
}

function choose(item) {
  emit('select', item)
  open.value = false
}

function onKeydown(event) {
  if (event.key === 'Escape') {
    open.value = false
    return
  }
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    open.value = true
    if (!props.options.length) return
    const step = event.key === 'ArrowDown' ? 1 : -1
    active.value = (active.value + step + props.options.length) % props.options.length
    document.getElementById(`${listId}-${active.value}`)?.scrollIntoView({ block: 'nearest' })
    return
  }
  if (event.key === 'Enter') {
    event.preventDefault()
    const item = props.options[active.value]
    if (open.value && item) choose(item)
  }
}
</script>

<template>
  <div class="picker" :class="{ 'is-open': open }">
    <Search class="picker__icon" :size="17" aria-hidden="true" />
    <input
      :id="inputId"
      v-model="search"
      class="ui-input picker__input"
      type="search"
      maxlength="120"
      autocomplete="off"
      role="combobox"
      aria-autocomplete="list"
      :aria-expanded="open"
      :aria-controls="listId"
      :aria-activedescendant="activeId"
      :aria-describedby="describedBy"
      :placeholder="placeholder"
      @focus="openList"
      @blur="closeList"
      @keydown="onKeydown"
    />
    <ChevronDown class="picker__chevron" :size="17" aria-hidden="true" />

    <Transition name="ui-pop">
      <div v-if="open" :id="listId" class="picker__list ui-glass ui-glass--strong" role="listbox">
        <button
          v-for="(item, index) in options"
          :id="`${listId}-${index}`"
          :key="item.label"
          class="picker__option"
          :class="{ 'is-active': index === active, 'is-selected': item.label === selected }"
          type="button"
          role="option"
          tabindex="-1"
          :aria-selected="item.label === selected"
          @mousedown.prevent="choose(item)"
          @mouseenter="active = index"
        >
          <span class="picker__name">{{ item.label }}</span>
          <span class="picker__class">{{ item.class }}</span>
          <Check v-if="item.label === selected" class="picker__check" :size="16" aria-hidden="true" />
        </button>
        <span v-if="!options.length" class="picker__empty">{{ emptyText }}</span>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.picker {
  position: relative;
  display: flex;
  align-items: center;
  min-width: 0;
}

.picker__icon {
  position: absolute;
  left: 14px;
  z-index: 1;
  color: var(--c-text-3);
  pointer-events: none;
  transition: color var(--dur-2);
}

.picker:focus-within .picker__icon {
  color: var(--c-accent-text);
}

.picker__input {
  padding-right: 42px;
  padding-left: 42px;
  font-weight: 600;
}

.picker__input::-webkit-search-cancel-button {
  -webkit-appearance: none;
  appearance: none;
}

.picker__chevron {
  position: absolute;
  right: 14px;
  color: var(--c-text-3);
  pointer-events: none;
  transition: transform var(--dur-3) var(--ease-ios), color var(--dur-2);
}

.picker.is-open .picker__chevron {
  color: var(--c-accent-text);
  transform: rotate(180deg);
}

.picker__list {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  left: 0;
  z-index: 40;
  display: grid;
  gap: 2px;
  max-height: min(340px, 52vh);
  padding: 6px;
  overflow-y: auto;
  overscroll-behavior: contain;
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-2);
  transform-origin: top center;
}

.picker__option {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto 18px;
  align-items: center;
  gap: 10px;
  min-height: 44px;
  padding: 8px 12px;
  border: 0;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--c-text);
  cursor: pointer;
  font-family: var(--font-body);
  text-align: left;
  transition: background-color var(--dur-1);
}

.picker__option.is-active {
  background: var(--c-blue-soft);
}

.picker__option.is-selected .picker__name {
  color: var(--c-accent-text);
}

.picker__name {
  overflow: hidden;
  color: var(--c-text);
  font-size: 14px;
  font-weight: 550;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.picker__class {
  padding: 3px 8px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-pill);
  background: var(--c-sunken);
  color: var(--c-text-2);
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.06em;
  white-space: nowrap;
}

.picker__check {
  grid-column: 3;
  color: var(--c-accent-text);
}

.picker__empty {
  padding: 14px 12px;
  color: var(--c-text-3);
  font-size: 14px;
}
</style>
