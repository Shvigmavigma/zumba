<script setup>
// Full-size track artwork. Closes on the backdrop, the close button or Escape
// (Escape is handled by the page).
import { useI18n } from 'vue-i18n'
import { X } from 'lucide-vue-next'

defineProps({
  open: { type: Boolean, default: false },
  src: { type: String, default: '' },
  title: { type: String, default: '' },
  badge: { type: String, default: '' }
})
const emit = defineEmits(['close'])
const { t } = useI18n()
</script>

<template>
  <Teleport to="body">
    <Transition name="lightbox">
      <div v-if="open && src" class="ui-modal-backdrop lightbox" @click.self="emit('close')">
        <section class="lightbox__dialog" role="dialog" aria-modal="true" :aria-label="title">
          <header class="lightbox__head">
            <div>
              <span class="ui-chip ui-chip--solid">{{ badge }}</span>
              <h2 class="lightbox__title">{{ title }}</h2>
            </div>
            <button class="ui-btn ui-btn--ghost ui-btn--icon" type="button" :title="t('common.close')" :aria-label="t('common.close')" @click="emit('close')">
              <X :size="18" />
            </button>
          </header>
          <div class="lightbox__view">
            <img :src="src" :alt="title" />
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.lightbox__dialog {
  display: grid;
  gap: 14px;
  width: min(1200px, 100%);
  max-height: calc(100dvh - 40px);
  padding: clamp(14px, 2vw, 22px);
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-xl);
  background: var(--c-surface-2);
  box-shadow: var(--shadow-2);
  -webkit-backdrop-filter: var(--glass-filter);
  backdrop-filter: var(--glass-filter);
}

.lightbox__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.lightbox__head > div {
  display: grid;
  gap: 8px;
}

.lightbox__title {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(18px, 2vw, 24px);
  text-transform: uppercase;
}

.lightbox__view {
  display: grid;
  place-items: center;
  min-height: 0;
  overflow: hidden;
  border-radius: var(--r-lg);
  background: var(--c-sunken);
}

.lightbox__view img {
  max-width: 100%;
  max-height: calc(100dvh - 180px);
  object-fit: contain;
}

.lightbox-enter-active,
.lightbox-leave-active {
  transition: opacity var(--dur-2) var(--ease-out);
}

.lightbox-enter-active .lightbox__dialog,
.lightbox-leave-active .lightbox__dialog {
  transition: transform var(--dur-3) var(--ease-ios), filter var(--dur-2) var(--ease-out);
}

.lightbox-enter-from,
.lightbox-leave-to {
  opacity: 0;
}

.lightbox-enter-from .lightbox__dialog,
.lightbox-leave-to .lightbox__dialog {
  filter: blur(6px);
  transform: translateY(16px) scale(0.96);
}

@media (prefers-reduced-motion: reduce) {
  .lightbox-enter-active,
  .lightbox-leave-active,
  .lightbox-enter-active .lightbox__dialog,
  .lightbox-leave-active .lightbox__dialog {
    transition: none;
  }
}
</style>
