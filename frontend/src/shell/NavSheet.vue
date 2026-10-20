<script setup>
// Phone navigation sheet (Kokonut UI "smooth drawer"): every section, staff
// tools and display settings. Drag the handle down or tap outside to close.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { onKeyStroke } from '@vueuse/core'
import { LogIn, UserPlus, X } from 'lucide-vue-next'
import SegmentedControl from '../ui/SegmentedControl.vue'
import { state } from '../store'
import { timeZoneOptions } from '../timezone'
import { setLocale, setTimeZone, toggleTheme } from './preferences'
import { useNavigation } from './useNavigation'

const open = defineModel('open', { type: Boolean, default: false })
const { t } = useI18n()
const route = useRoute()
const { publicItems, staffItems } = useNavigation()
const dragY = ref(0)
let startY = null

const themeOptions = computed(() => [
  { value: 'dark', label: t('ui.settings.dark') },
  { value: 'light', label: t('ui.settings.light') }
])
const localeOptions = [
  { value: 'ru', label: 'RU' },
  { value: 'en', label: 'EN' }
]

watch(() => route.fullPath, () => { open.value = false })
watch(open, (value) => {
  document.documentElement.style.overflow = value ? 'hidden' : ''
  dragY.value = 0
})
onKeyStroke('Escape', () => { open.value = false })

function onDragStart(event) {
  startY = event.clientY
  event.currentTarget.setPointerCapture?.(event.pointerId)
}

function onDragMove(event) {
  if (startY === null) return
  dragY.value = Math.max(0, event.clientY - startY)
}

function onDragEnd() {
  if (dragY.value > 110) open.value = false
  dragY.value = 0
  startY = null
}

function chooseTheme(value) {
  if (value !== state.theme) toggleTheme()
}
</script>

<template>
  <Teleport to="body">
    <Transition name="ui-fade">
      <div v-if="open" class="sheet-backdrop" @click="open = false"></div>
    </Transition>
    <Transition name="ui-sheet">
      <section
        v-if="open"
        class="sheet ui-glass ui-glass--strong"
        role="dialog"
        aria-modal="true"
        :aria-label="t('ui.nav.menu')"
        :style="dragY ? { transform: `translateY(${dragY}px)`, transition: 'none' } : null"
      >
        <div class="sheet__handle" @pointerdown="onDragStart" @pointermove="onDragMove" @pointerup="onDragEnd" @pointercancel="onDragEnd">
          <span></span>
        </div>
        <header class="sheet__head">
          <p class="ui-eyebrow">{{ t('ui.nav.menu') }}</p>
          <button class="ui-btn ui-btn--ghost ui-btn--icon ui-btn--sm" type="button" :aria-label="t('common.close')" @click="open = false"><X :size="18" /></button>
        </header>

        <nav class="sheet__grid" :aria-label="t('ui.nav.primary')">
          <RouterLink v-for="item in publicItems" :key="item.key" class="sheet__tile" :to="item.to" :class="{ 'is-active': item.to === '/' ? route.path === '/' : route.path.startsWith(item.to) }">
            <component :is="item.icon" :size="20" />
            <span>{{ item.label }}</span>
          </RouterLink>
        </nav>

        <template v-if="staffItems.length">
          <p class="ui-eyebrow sheet__section">{{ t('ui.nav.manage') }}</p>
          <nav class="sheet__list" :aria-label="t('ui.nav.manage')">
            <RouterLink v-for="item in staffItems" :key="item.key" class="sheet__row" :to="item.to">
              <component :is="item.icon" :size="18" />{{ item.label }}
            </RouterLink>
          </nav>
        </template>

        <p class="ui-eyebrow sheet__section">{{ t('ui.settings.title') }}</p>
        <div class="sheet__settings">
          <SegmentedControl :model-value="state.theme" :options="themeOptions" size="sm" block :aria-label="t('ui.settings.theme')" @update:model-value="chooseTheme" />
          <SegmentedControl :model-value="state.locale" :options="localeOptions" size="sm" block :aria-label="t('common.language')" @update:model-value="setLocale" />
          <select class="sheet__select" :value="state.timeZone" :aria-label="t('common.timezone')" @change="setTimeZone($event.target.value)">
            <option v-for="option in timeZoneOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </div>

        <div v-if="!state.user" class="sheet__auth">
          <RouterLink class="ui-btn ui-btn--outline" to="/login"><LogIn :size="16" />{{ t('nav.login') }}</RouterLink>
          <RouterLink class="ui-btn ui-btn--primary" to="/register"><UserPlus :size="16" />{{ t('ui.nav.join') }}</RouterLink>
        </div>
      </section>
    </Transition>
  </Teleport>
</template>

<style scoped>
.sheet-backdrop {
  position: fixed;
  inset: 0;
  z-index: 90;
  background: var(--c-overlay);
  -webkit-backdrop-filter: blur(4px);
  backdrop-filter: blur(4px);
}

.sheet {
  position: fixed;
  right: 8px;
  bottom: 8px;
  left: 8px;
  z-index: 91;
  display: grid;
  gap: 14px;
  max-height: min(86dvh, 760px);
  padding: 4px 16px calc(16px + env(safe-area-inset-bottom));
  overflow-y: auto;
  border-radius: 28px;
  box-shadow: var(--shadow-2);
}

.sheet__handle {
  display: grid;
  place-items: center;
  height: 22px;
  cursor: grab;
  touch-action: none;
}

.sheet__handle span {
  width: 42px;
  height: 5px;
  border-radius: 99px;
  background: color-mix(in srgb, var(--c-text) 22%, transparent);
}

.sheet__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sheet__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.sheet__tile {
  display: grid;
  gap: 10px;
  min-height: 84px;
  padding: 14px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  background: var(--c-sunken);
  color: var(--c-text);
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
}

.sheet__tile svg {
  color: var(--c-accent-text);
}

.sheet__tile.is-active {
  border-color: var(--c-blue-line);
  background: var(--c-blue-soft);
}

.sheet__section {
  margin-top: 4px;
}

.sheet__list {
  display: grid;
  gap: 2px;
}

.sheet__row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 44px;
  padding: 0 12px;
  border-radius: var(--r-sm);
  color: var(--c-text);
  font-weight: 550;
  text-decoration: none;
}

.sheet__row svg {
  color: var(--c-text-2);
}

.sheet__row.router-link-active {
  background: var(--c-blue-soft);
}

.sheet__settings {
  display: grid;
  gap: 8px;
}

.sheet__select {
  min-height: 42px;
  padding: 0 12px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-sm);
  background: var(--c-sunken);
  color: var(--c-text);
}

.sheet__auth {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
</style>
