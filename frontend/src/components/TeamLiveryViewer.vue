<script setup>
// Gallery of livery screenshots (a team's, or a pilot's own): one large image,
// thumbnails below, arrows and the keyboard to move between them.
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight, Images, Trash2, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  open: {
    type: Boolean,
    default: false
  },
  teamName: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    default: ''
  },
  images: {
    type: Array,
    default: () => []
  },
  canManage: {
    type: Boolean,
    default: false
  },
  /** The image to show first when the gallery opens. */
  startIndex: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['close', 'delete'])
const dialog = ref(null)
const selectedIndex = ref(0)
const currentImage = computed(() => props.images[selectedIndex.value] || null)

function selectImage(index) {
  selectedIndex.value = Math.max(0, Math.min(index, props.images.length - 1))
}

function showPrevious() {
  if (props.images.length < 2) return
  selectImage((selectedIndex.value - 1 + props.images.length) % props.images.length)
}

function showNext() {
  if (props.images.length < 2) return
  selectImage((selectedIndex.value + 1) % props.images.length)
}

function imageLabel(image, index) {
  return image?.original_filename || `${props.teamName} ${index + 1}`
}

function onKeydown(event) {
  if (event.key === 'Escape') emit('close')
  else if (event.key === 'ArrowLeft') showPrevious()
  else if (event.key === 'ArrowRight') showNext()
}

watch(() => props.open, async (isOpen) => {
  if (!isOpen) {
    window.removeEventListener('keydown', onKeydown)
    return
  }
  selectImage(props.startIndex)
  window.addEventListener('keydown', onKeydown)
  await nextTick()
  dialog.value?.focus()
})

watch(() => props.images.length, () => {
  selectedIndex.value = Math.min(selectedIndex.value, Math.max(props.images.length - 1, 0))
})

onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <Transition name="livery">
      <div v-if="open" class="ui-modal-backdrop livery" @click.self="emit('close')">
        <article ref="dialog" class="livery__dialog" role="dialog" aria-modal="true" :aria-label="title || t('teams.liveryViewerTitle', { name: teamName })" tabindex="-1">
          <header class="livery__head">
            <div class="livery__heading">
              <span class="ui-eyebrow ui-eyebrow--accent"><Images :size="14" />{{ title || t('teams.liveryTitle') }} · {{ images.length }}/4</span>
              <h2 class="livery__title">{{ teamName }}</h2>
            </div>
            <button class="ui-btn ui-btn--ghost ui-btn--icon" type="button" :title="t('common.close')" :aria-label="t('common.close')" @click="emit('close')">
              <X :size="18" />
            </button>
          </header>

          <div v-if="currentImage" class="livery__stage">
            <button v-if="images.length > 1" class="livery__nav livery__nav--prev" type="button" :title="t('teams.previousLivery')" :aria-label="t('teams.previousLivery')" @click="showPrevious">
              <ChevronLeft :size="22" />
            </button>
            <img :key="currentImage.id" class="livery__image" :src="currentImage.image_url" :alt="imageLabel(currentImage, selectedIndex)" />
            <button v-if="images.length > 1" class="livery__nav livery__nav--next" type="button" :title="t('teams.nextLivery')" :aria-label="t('teams.nextLivery')" @click="showNext">
              <ChevronRight :size="22" />
            </button>
            <button v-if="canManage" class="ui-btn ui-btn--danger ui-btn--icon ui-btn--sm livery__delete" type="button" :title="t('teams.deleteLivery')" :aria-label="t('teams.deleteLivery')" @click="emit('delete', currentImage)">
              <Trash2 :size="16" />
            </button>
          </div>
          <div v-else class="livery__empty">
            <Images :size="34" />
            <strong>{{ t('teams.liveryEmpty') }}</strong>
            <span>{{ t('teams.liveryUploadHint') }}</span>
          </div>

          <footer v-if="images.length" class="livery__foot">
            <div class="livery__thumbs" role="tablist" :aria-label="t('teams.liveryTitle')">
              <button v-for="(image, index) in images" :key="image.id" class="livery__thumb" :class="{ 'is-selected': index === selectedIndex }" type="button" role="tab" :aria-selected="index === selectedIndex" :aria-label="imageLabel(image, index)" @click="selectImage(index)">
                <img :src="image.image_url" alt="" />
              </button>
            </div>
            <span class="livery__counter ui-num">{{ selectedIndex + 1 }} / {{ images.length }}</span>
          </footer>
        </article>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.livery__dialog {
  display: grid;
  gap: 14px;
  width: min(1200px, 100%);
  max-height: calc(100dvh - 40px);
  padding: clamp(14px, 2vw, 22px);
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-xl);
  background: var(--c-surface-2);
  box-shadow: var(--shadow-2);
  outline: none;
  -webkit-backdrop-filter: var(--glass-filter);
  backdrop-filter: var(--glass-filter);
}

.livery__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.livery__heading {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.livery__title {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(18px, 2vw, 24px);
  overflow-wrap: anywhere;
  text-transform: uppercase;
}

.livery__stage {
  position: relative;
  display: grid;
  place-items: center;
  min-height: 0;
  overflow: hidden;
  border-radius: var(--r-lg);
  background: var(--c-sunken);
}

.livery__image {
  max-width: 100%;
  max-height: calc(100dvh - 260px);
  object-fit: contain;
  animation: livery-image var(--dur-2) var(--ease-out);
}

@keyframes livery-image {
  from {
    opacity: 0;
  }
}

.livery__nav {
  position: absolute;
  top: 50%;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 50%;
  background: rgba(8, 12, 22, 0.62);
  color: #fff;
  cursor: pointer;
  transform: translateY(-50%);
  transition: background var(--dur-1), transform var(--dur-2) var(--ease-ios);
}

.livery__nav--prev {
  left: 12px;
}

.livery__nav--next {
  right: 12px;
}

.livery__nav:hover {
  background: var(--bm-blue);
  transform: translateY(-50%) scale(1.06);
}

.livery__delete {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 1;
}

.livery__empty {
  display: grid;
  justify-items: center;
  gap: 6px;
  padding: clamp(32px, 8vw, 80px) 20px;
  border-radius: var(--r-lg);
  background: var(--c-sunken);
  color: var(--c-text-3);
  text-align: center;
}

.livery__empty strong {
  color: var(--c-text);
}

.livery__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.livery__thumbs {
  display: flex;
  gap: 8px;
  min-width: 0;
  overflow-x: auto;
}

.livery__thumb {
  flex: none;
  width: 84px;
  aspect-ratio: 16 / 9;
  padding: 0;
  overflow: hidden;
  border: 2px solid transparent;
  border-radius: var(--r-sm);
  background: var(--c-sunken);
  cursor: pointer;
  opacity: 0.6;
  transition: opacity var(--dur-1), border-color var(--dur-1);
}

.livery__thumb:hover,
.livery__thumb.is-selected {
  opacity: 1;
}

.livery__thumb.is-selected {
  border-color: var(--bm-blue-bright);
}

.livery__thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.livery__counter {
  flex: none;
  color: var(--c-text-3);
  font-size: 13px;
}

.livery-enter-active,
.livery-leave-active {
  transition: opacity var(--dur-2) var(--ease-out);
}

.livery-enter-active .livery__dialog,
.livery-leave-active .livery__dialog {
  transition: transform var(--dur-3) var(--ease-ios), filter var(--dur-2) var(--ease-out);
}

.livery-enter-from,
.livery-leave-to {
  opacity: 0;
}

.livery-enter-from .livery__dialog,
.livery-leave-to .livery__dialog {
  filter: blur(6px);
  transform: translateY(16px) scale(0.96);
}

@media (prefers-reduced-motion: reduce) {
  .livery__image {
    animation: none;
  }

  .livery__nav,
  .livery-enter-active,
  .livery-leave-active,
  .livery-enter-active .livery__dialog,
  .livery-leave-active .livery__dialog {
    transition: none;
  }
}
</style>
