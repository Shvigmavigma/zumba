<script setup>
// Full-screen reader for a news story: the picture or video, the text on a
// glass card that can be hidden, arrows to the neighbouring stories. Escape
// closes it and the arrow keys turn the pages; the page behind does not scroll.
import { onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronLeft, ChevronRight, X } from 'lucide-vue-next'
import { isVideoUrl } from '../../media'

const props = defineProps({
  open: { type: Boolean, default: false },
  item: { type: Object, default: null },
  /** 1-based place of the story and how many there are. */
  position: { type: Number, default: 1 },
  total: { type: Number, default: 1 }
})
const emit = defineEmits(['close', 'prev', 'next'])

const { t } = useI18n()
const textHidden = ref(false)

function onKeydown(event) {
  const action = { Escape: 'close', ArrowLeft: 'prev', ArrowRight: 'next' }[event.key]
  if (!action) return
  event.preventDefault()
  emit(action)
}

function release() {
  window.removeEventListener('keydown', onKeydown)
  document.documentElement.style.overflow = ''
}

watch(() => props.open, (open) => {
  if (!open) {
    release()
    return
  }
  textHidden.value = false
  window.addEventListener('keydown', onKeydown)
  document.documentElement.style.overflow = 'hidden'
})

onBeforeUnmount(release)
</script>

<template>
  <Teleport to="body">
    <Transition name="ui-fade">
      <div v-if="open && item" class="viewer" role="dialog" aria-modal="true" :aria-label="item.title" @click="emit('close')">
        <Transition name="ui-pop" mode="out-in">
          <video v-if="isVideoUrl(item.image_url)" :key="`v${item.id}`" class="viewer__media" :src="item.image_url" controls autoplay playsinline @click.stop></video>
          <img v-else :key="`i${item.id}`" class="viewer__media" :src="item.image_url" alt="" @click.stop />
        </Transition>
        <button class="viewer__btn viewer__close" type="button" :aria-label="t('news.closeFullscreen')" @click.stop="emit('close')"><X :size="20" /></button>
        <template v-if="total > 1">
          <button class="viewer__btn viewer__prev" type="button" :aria-label="t('news.scrollLeft')" @click.stop="emit('prev')"><ChevronLeft :size="24" /></button>
          <button class="viewer__btn viewer__next" type="button" :aria-label="t('news.scrollRight')" @click.stop="emit('next')"><ChevronRight :size="24" /></button>
        </template>
        <button class="ui-btn ui-btn--sm viewer__toggle" type="button" @click.stop="textHidden = !textHidden">
          {{ textHidden ? t('news.showText') : t('news.hideText') }}
        </button>
        <Transition name="ui-pop">
          <div v-if="!textHidden" class="viewer__text ui-glass ui-glass--strong" @click.stop>
            <span class="ui-chip ui-chip--blue">{{ position }} / {{ total }}</span>
            <h2 class="viewer__title">{{ item.title }}</h2>
            <p>{{ item.body }}</p>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.viewer {
  position: fixed;
  inset: 0;
  z-index: 120;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(2, 4, 9, 0.88);
  -webkit-backdrop-filter: blur(18px);
  backdrop-filter: blur(18px);
}

.viewer__media {
  max-width: min(1400px, 100%);
  max-height: calc(100dvh - 48px);
  border-radius: var(--r-lg);
  object-fit: contain;
  box-shadow: var(--shadow-2);
}

.viewer__btn {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 50%;
  background: rgba(10, 14, 24, 0.45);
  color: #fff;
  cursor: pointer;
  -webkit-backdrop-filter: blur(14px);
  backdrop-filter: blur(14px);
  transition: background-color var(--dur-2), transform var(--dur-2) var(--ease-ios);
}

.viewer__btn:hover {
  background: var(--bm-blue);
}

.viewer__btn:active {
  transform: scale(0.92);
}

.viewer__close {
  position: fixed;
  top: 18px;
  right: 18px;
}

.viewer__prev,
.viewer__next {
  position: fixed;
  top: 50%;
  margin-top: -21px;
}

.viewer__prev {
  left: 18px;
}

.viewer__next {
  right: 18px;
}

.viewer__toggle {
  position: fixed;
  top: 18px;
  left: 18px;
}

.viewer__text {
  position: fixed;
  bottom: 24px;
  left: 50%;
  display: grid;
  gap: 10px;
  width: min(720px, calc(100vw - 32px));
  margin-left: calc(min(720px, calc(100vw - 32px)) / -2);
  padding: 20px 22px;
  border-radius: var(--r-xl);
}

.viewer__text .ui-chip {
  justify-self: start;
}

.viewer__title {
  margin: 0;
  font-size: 22px;
}

.viewer__text p {
  max-height: 30vh;
  margin: 0;
  overflow-y: auto;
  color: var(--c-text-2);
  line-height: 1.55;
}
</style>
