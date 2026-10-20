<script setup>
// Floating status banners: errors stay until dismissed, "Saved" fades by itself
// (the parent clears the flag). Visible wherever the user is on the page.
import { useI18n } from 'vue-i18n'
import { AlertCircle, CheckCircle2, X } from 'lucide-vue-next'

defineProps({
  error: { type: String, default: '' },
  saved: { type: Boolean, default: false }
})
const emit = defineEmits(['dismiss'])
const { t } = useI18n()
</script>

<template>
  <div class="toasts" aria-live="polite">
    <Transition name="toast">
      <p v-if="error" class="ui-alert toasts__item" role="alert">
        <AlertCircle :size="18" />
        <span>{{ error }}</span>
        <button class="ui-btn ui-btn--ghost ui-btn--icon ui-btn--sm" type="button" :aria-label="t('teamsPage.dismiss')" :title="t('teamsPage.dismiss')" @click="emit('dismiss')">
          <X :size="16" />
        </button>
      </p>
    </Transition>
    <Transition name="toast">
      <p v-if="saved" class="ui-alert ui-alert--success toasts__item" role="status">
        <CheckCircle2 :size="18" />
        <span>{{ t('common.saved') }}</span>
      </p>
    </Transition>
  </div>
</template>

<style scoped>
.toasts {
  position: fixed;
  right: 0;
  bottom: calc(var(--tabbar-h) + 18px + env(safe-area-inset-bottom));
  left: 0;
  z-index: 105;
  display: grid;
  justify-items: center;
  gap: 8px;
  padding: 0 16px;
  pointer-events: none;
}

.toasts__item {
  align-items: center;
  width: min(520px, 100%);
  border-radius: var(--r-lg);
  background: color-mix(in srgb, var(--bm-red) 14%, var(--c-surface-2));
  box-shadow: var(--shadow-2);
  -webkit-backdrop-filter: var(--glass-filter);
  backdrop-filter: var(--glass-filter);
  pointer-events: auto;
}

.toasts__item.ui-alert--success {
  background: color-mix(in srgb, var(--bm-green) 12%, var(--c-surface-2));
}

.toasts__item span {
  flex: 1 1 auto;
}

.toasts__item .ui-btn {
  margin: -6px -8px -6px 0;
  color: inherit;
}

.toast-enter-active {
  transition: opacity var(--dur-2) var(--ease-out), transform 520ms var(--ease-spring);
}

.toast-leave-active {
  transition: opacity var(--dur-2) ease-in, transform var(--dur-2) ease-in;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(18px) scale(0.96);
}

@media (prefers-reduced-motion: reduce) {
  .toast-enter-active,
  .toast-leave-active {
    transition: opacity var(--dur-1);
  }

  .toast-enter-from,
  .toast-leave-to {
    transform: none;
  }
}
</style>
