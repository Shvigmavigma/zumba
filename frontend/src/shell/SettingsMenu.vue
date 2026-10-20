<script setup>
// Display preferences in one place: theme, language and the time zone used
// for every race time on the site.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Clock3, Moon, SlidersHorizontal, Sun } from 'lucide-vue-next'
import Popover from '../ui/Popover.vue'
import SegmentedControl from '../ui/SegmentedControl.vue'
import { state } from '../store'
import { timeZoneOptions } from '../timezone'
import { setLocale, setTimeZone, toggleTheme } from './preferences'

const { t } = useI18n()
const open = ref(false)

const themeOptions = computed(() => [
  { value: 'dark', label: t('ui.settings.dark'), icon: Moon },
  { value: 'light', label: t('ui.settings.light'), icon: Sun }
])
const localeOptions = [
  { value: 'ru', label: 'Русский' },
  { value: 'en', label: 'English' }
]

let lastPointer = null
function rememberPointer(event) {
  lastPointer = event
}

function chooseTheme(value) {
  if (value !== state.theme) toggleTheme(lastPointer)
}
</script>

<template>
  <Popover v-model:open="open" :label="t('ui.settings.title')" width="320px">
    <template #trigger="{ toggle }">
      <button class="ui-btn ui-btn--ghost ui-btn--icon" type="button" :aria-expanded="open" :title="t('ui.settings.title')" :aria-label="t('ui.settings.title')" @click="toggle">
        <SlidersHorizontal :size="18" />
      </button>
    </template>
    <div class="settings" @pointerdown="rememberPointer">
      <p class="ui-eyebrow settings__heading">{{ t('ui.settings.title') }}</p>
      <div class="settings__row">
        <span class="settings__label">{{ t('ui.settings.theme') }}</span>
        <SegmentedControl :model-value="state.theme" :options="themeOptions" size="sm" block :aria-label="t('ui.settings.theme')" @update:model-value="chooseTheme" />
      </div>
      <div class="settings__row">
        <span class="settings__label">{{ t('common.language') }}</span>
        <SegmentedControl :model-value="state.locale" :options="localeOptions" size="sm" block :aria-label="t('common.language')" @update:model-value="setLocale" />
      </div>
      <label class="settings__row">
        <span class="settings__label">{{ t('common.timezone') }}</span>
        <span class="settings__select">
          <Clock3 :size="16" aria-hidden="true" />
          <select :value="state.timeZone" @change="setTimeZone($event.target.value)">
            <option v-for="option in timeZoneOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </span>
        <small class="settings__hint">{{ t('ui.settings.timezoneHint') }}</small>
      </label>
    </div>
  </Popover>
</template>

<style scoped>
.settings {
  display: grid;
  gap: 16px;
  padding: 8px 8px 10px;
}

.settings__heading {
  padding: 2px 2px 0;
}

.settings__row {
  display: grid;
  gap: 8px;
}

.settings__label {
  color: var(--c-text);
  font-size: 13px;
  font-weight: 600;
}

.settings__hint {
  color: var(--c-text-3);
  font-size: 12px;
  line-height: 1.4;
}

.settings__select {
  position: relative;
  display: flex;
  align-items: center;
  color: var(--c-text-2);
}

.settings__select svg {
  position: absolute;
  left: 12px;
  pointer-events: none;
}

.settings__select select {
  width: 100%;
  min-height: 40px;
  padding: 0 12px 0 36px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-sm);
  background: var(--c-sunken);
  color: var(--c-text);
  font-size: 13px;
}
</style>
