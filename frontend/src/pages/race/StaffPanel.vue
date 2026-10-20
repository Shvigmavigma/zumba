<script setup>
// "Управление": every staff-only tool for this race in one card, split into
// tabs. Each tab's content is passed in through a slot of the same name.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ShieldCheck } from 'lucide-vue-next'
import SegmentedControl from '../../ui/SegmentedControl.vue'
import { roleLabel } from '../../i18nLabels'
import { state } from '../../store'

const props = defineProps({
  /** [{ value, label, icon? }] */
  tabs: { type: Array, default: () => [] }
})
const { t } = useI18n()

const active = ref(props.tabs[0]?.value || '')
const current = computed(() => (props.tabs.some((tab) => tab.value === active.value) ? active.value : props.tabs[0]?.value || ''))

watch(() => props.tabs.map((tab) => tab.value).join(','), () => {
  if (!props.tabs.some((tab) => tab.value === active.value)) active.value = props.tabs[0]?.value || ''
})
</script>

<template>
  <section id="race-staff" class="staff ui-card" aria-labelledby="race-staff-title">
    <header class="ui-card__head">
      <div class="ui-card__title">
        <p class="ui-eyebrow ui-eyebrow--accent"><ShieldCheck :size="13" />{{ t('racePage.staff.eyebrow') }}</p>
        <h2 id="race-staff-title">{{ t('racePage.staff.title') }}</h2>
      </div>
      <span v-if="state.user?.role" class="ui-chip ui-chip--amber">{{ roleLabel(t, state.user.role) }}</span>
    </header>

    <SegmentedControl v-if="tabs.length > 1" v-model="active" :options="tabs" size="sm" :aria-label="t('racePage.staff.title')" />

    <Transition name="staff-swap" mode="out-in">
      <div :key="current" class="staff__pane">
        <slot :name="current" />
      </div>
    </Transition>
  </section>
</template>

<style scoped>
.staff {
  border-style: dashed;
  border-color: color-mix(in srgb, var(--bm-amber) 30%, var(--c-line-strong));
  scroll-margin-top: calc(var(--header-h) + 16px);
}

.staff__pane {
  display: grid;
  gap: 18px;
}

.staff-swap-enter-active,
.staff-swap-leave-active {
  transition: opacity var(--dur-2) var(--ease-out), transform var(--dur-3) var(--ease-ios);
}

.staff-swap-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.staff-swap-leave-to {
  opacity: 0;
}

/* Shared look for the staff tool blocks rendered inside the tabs. */
.staff :deep(.staff-block) {
  display: grid;
  gap: 14px;
  padding: 16px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-lg);
  background: var(--c-sunken);
}

.staff :deep(.staff-block__head) {
  display: grid;
  gap: 4px;
}

.staff :deep(.staff-block__head strong) {
  font-size: 15px;
}

.staff :deep(.staff-block__head span) {
  color: var(--c-text-3);
  font-size: 13px;
  line-height: 1.45;
}

.staff :deep(.staff-actions) {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.staff :deep(.staff-file) {
  display: block;
  width: 100%;
  padding: 10px 12px;
  border: 1px dashed var(--c-line-strong);
  border-radius: var(--r-md);
  background: var(--c-surface-solid);
  color: var(--c-text-2);
  font-size: 13px;
}

.staff :deep(.staff-file::file-selector-button) {
  margin-right: 12px;
  padding: 7px 14px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-pill);
  background: var(--c-surface-2);
  color: var(--c-text);
  cursor: pointer;
  font-family: var(--font-body);
  font-weight: 600;
}

@media (prefers-reduced-motion: reduce) {
  .staff-swap-enter-active,
  .staff-swap-leave-active {
    transition: none;
  }
}
</style>
