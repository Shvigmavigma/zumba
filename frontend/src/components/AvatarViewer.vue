<script setup>
import { onBeforeUnmount, watch } from 'vue'
import { X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { onKeyStroke } from '@vueuse/core'

const { t } = useI18n()

const props = defineProps({
  open: {
    type: Boolean,
    default: false
  },
  src: {
    type: String,
    default: ''
  },
  label: {
    type: String,
    default: 'Avatar'
  },
  fallbackColor: {
    type: String,
    default: '#2563eb'
  },
  team: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close'])

onKeyStroke('Escape', () => {
  if (props.open) emit('close')
})

watch(() => props.open, (open) => {
  document.documentElement.style.overflow = open ? 'hidden' : ''
})

// Leaving the page with the viewer open (e.g. browser Back) must not keep the next page locked.
onBeforeUnmount(() => {
  if (props.open) document.documentElement.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <Transition name="ui-fade">
      <div v-if="open" class="viewer" role="dialog" aria-modal="true" :aria-label="label" @click.self="$emit('close')">
        <article class="viewer__card" :class="{ 'is-team': team }" :style="{ '--avatar-color': fallbackColor || '#2563eb' }">
          <header class="viewer__head">
            <h2>{{ label }}</h2>
            <button class="ui-btn ui-btn--ghost ui-btn--icon ui-btn--sm" type="button" :title="t('common.close')" :aria-label="t('common.close')" @click="$emit('close')">
              <X :size="18" />
            </button>
          </header>
          <div class="viewer__frame">
            <img v-if="src" :src="src" :alt="label" />
            <div v-else class="viewer__empty">{{ t('avatar.empty') }}</div>
          </div>
        </article>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.viewer {
  position: fixed;
  inset: 0;
  z-index: 130;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(2, 4, 9, 0.78);
  -webkit-backdrop-filter: blur(16px);
  backdrop-filter: blur(16px);
}

.viewer__card {
  display: grid;
  gap: 14px;
  width: min(520px, 100%);
  padding: 16px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-xl);
  background: var(--c-surface-2);
  box-shadow: var(--shadow-2);
  animation: viewer-in 460ms var(--ease-ios);
  -webkit-backdrop-filter: var(--glass-filter);
  backdrop-filter: var(--glass-filter);
}

@keyframes viewer-in {
  from {
    opacity: 0;
    filter: blur(6px);
    transform: scale(0.94);
  }
}

.viewer__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.viewer__head h2 {
  margin: 0;
  overflow: hidden;
  font-size: 17px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.viewer__frame {
  display: grid;
  place-items: center;
  aspect-ratio: 1;
  overflow: hidden;
  border-radius: 50%;
  background: var(--avatar-color);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--avatar-color) 30%, transparent), 0 30px 60px rgba(0, 0, 0, 0.4);
}

.viewer__card.is-team .viewer__frame {
  border-radius: var(--r-xl);
}

.viewer__frame img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.viewer__empty {
  padding: 24px;
  color: rgba(255, 255, 255, 0.85);
  font-size: 14px;
  text-align: center;
}

@media (prefers-reduced-motion: reduce) {
  .viewer__card {
    animation: none;
  }
}
</style>
