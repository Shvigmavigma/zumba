<script setup>
// Lightweight anchored popover: glass panel, spring-in, closes on outside
// click, Escape or navigation.
import { ref, watch } from 'vue'
import { onClickOutside, onKeyStroke } from '@vueuse/core'
import { useRoute } from 'vue-router'

const props = defineProps({
  align: { type: String, default: 'end' },
  width: { type: String, default: '280px' },
  label: { type: String, default: '' }
})
const open = defineModel('open', { type: Boolean, default: false })
const root = ref(null)
const route = useRoute()

onClickOutside(root, () => { open.value = false })
onKeyStroke('Escape', () => { open.value = false })
watch(() => route.fullPath, () => { open.value = false })

function toggle() {
  open.value = !open.value
}
</script>

<template>
  <div ref="root" class="popover" :class="`popover--${props.align}`">
    <slot name="trigger" :open="open" :toggle="toggle" />
    <Transition name="ui-pop">
      <div v-if="open" class="popover__panel ui-glass ui-glass--strong" role="dialog" :aria-label="label" :style="{ width }">
        <slot :close="() => (open = false)" />
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.popover {
  position: relative;
}

.popover__panel {
  position: absolute;
  top: calc(100% + 10px);
  z-index: 80;
  max-width: calc(100vw - 24px);
  padding: 8px;
  border-radius: var(--r-lg);
  /* Popovers live inside the glass header, whose own backdrop-filter stops
     this panel from blurring the page; a near-solid fill keeps text legible. */
  background: color-mix(in srgb, var(--c-surface-solid) 94%, transparent);
  box-shadow: var(--shadow-2);
  transform-origin: top right;
}

.popover--end .popover__panel {
  right: 0;
}

.popover--start .popover__panel {
  left: 0;
  transform-origin: top left;
}
</style>
