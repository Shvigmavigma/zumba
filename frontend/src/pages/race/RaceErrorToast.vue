<script setup>
// Floating error for actions anywhere on the long race page, so a failed
// registration or upload is visible without scrolling back to the top.
import { useI18n } from 'vue-i18n'
import { AlertTriangle, X } from 'lucide-vue-next'

defineProps({
  message: { type: String, default: '' }
})
const emit = defineEmits(['dismiss'])
const { t } = useI18n()
</script>

<template>
  <Teleport to="body">
    <Transition name="race-toast">
      <div v-if="message" class="race-toast ui-alert" role="alert">
        <AlertTriangle :size="18" />
        <span class="race-toast__text">{{ message }}</span>
        <button class="race-toast__close" type="button" :aria-label="t('common.close')" @click="emit('dismiss')"><X :size="16" /></button>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.race-toast {
  position: fixed;
  bottom: calc(var(--tabbar-h) + 20px + env(safe-area-inset-bottom, 0px));
  left: 50%;
  z-index: 140;
  width: min(560px, calc(100% - 32px));
  padding: 14px 14px 14px 16px;
  border-color: color-mix(in srgb, var(--bm-red) 45%, transparent);
  border-radius: var(--r-lg);
  background: color-mix(in srgb, var(--bm-red) 14%, var(--c-surface-solid));
  box-shadow: var(--shadow-2);
  color: color-mix(in srgb, var(--bm-red) 55%, var(--c-text));
  transform: translateX(-50%);
  -webkit-backdrop-filter: var(--glass-filter);
  backdrop-filter: var(--glass-filter);
}

.race-toast__text {
  flex: 1 1 auto;
  min-width: 0;
  overflow-wrap: anywhere;
}

.race-toast__close {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 50%;
  background: color-mix(in srgb, var(--c-text) 8%, transparent);
  color: inherit;
  cursor: pointer;
}

.race-toast-enter-active,
.race-toast-leave-active {
  transition: opacity var(--dur-2) var(--ease-out), transform var(--dur-3) var(--ease-spring);
}

.race-toast-enter-from,
.race-toast-leave-to {
  opacity: 0;
  transform: translate(-50%, 20px) scale(0.96);
}

@media (prefers-reduced-motion: reduce) {
  .race-toast-enter-active,
  .race-toast-leave-active {
    transition: none;
  }
}
</style>
