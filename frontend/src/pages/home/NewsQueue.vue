<script setup>
// The queue beside the news banner on wide screens: the story on screen and
// the ones that follow, each a button that jumps to it. The current entry
// fills up with the autoplay timer; when the banner moves on, the list slides
// up by one.
import { useI18n } from 'vue-i18n'
import { isVideoUrl } from '../../media'

defineProps({
  /** [{ index, item }] starting with the story on screen. */
  entries: { type: Array, required: true },
  active: { type: Number, default: 0 },
  paused: { type: Boolean, default: false },
  /** Changes whenever the autoplay timer restarts. */
  cycle: { type: Number, default: 0 }
})
const emit = defineEmits(['select'])

const { t } = useI18n()

/** Two-digit numbers, as on a timing screen. */
function storyNumber(index) {
  return String(index + 1).padStart(2, '0')
}
</script>

<template>
  <aside class="queue" :aria-label="t('home.news.queue')">
    <p class="queue__title">{{ t('home.news.queue') }}</p>
    <TransitionGroup name="queue-move" tag="ol" class="queue__list">
      <li v-for="entry in entries" :key="entry.item.id">
        <button
          class="queue__item"
          :class="{ 'is-active': entry.index === active, 'is-paused': paused }"
          type="button"
          :aria-current="entry.index === active ? 'true' : undefined"
          @click.stop="emit('select', entry.index)"
        >
          <span class="queue__thumb">
            <video v-if="isVideoUrl(entry.item.image_url)" :src="entry.item.image_url" muted playsinline preload="metadata"></video>
            <img v-else :src="entry.item.image_url" alt="" loading="lazy" />
          </span>
          <span class="queue__text">
            <small class="ui-num">{{ storyNumber(entry.index) }}</small>
            <b>{{ entry.item.title }}</b>
          </span>
          <span v-if="entry.index === active" :key="`run-${cycle}`" class="queue__progress" aria-hidden="true"></span>
        </button>
      </li>
    </TransitionGroup>
  </aside>
</template>

<style scoped>
/* Sits over the banner's picture, on the right, just above the middle. */
.queue {
  position: absolute;
  top: 50%;
  right: clamp(76px, 6.4vw, 96px);
  z-index: 3;
  display: grid;
  gap: 10px;
  width: min(330px, 27%);
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: var(--r-lg);
  background: rgba(6, 9, 16, 0.46);
  -webkit-backdrop-filter: blur(18px) saturate(160%);
  backdrop-filter: blur(18px) saturate(160%);
  transform: translateY(-46%);
}

.queue__title {
  margin: 0;
  color: rgba(255, 255, 255, 0.6);
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.queue__list {
  position: relative;
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.queue__item {
  position: relative;
  display: grid;
  grid-template-columns: 62px minmax(0, 1fr);
  align-items: center;
  gap: 11px;
  width: 100%;
  padding: 7px;
  overflow: hidden;
  border: 1px solid transparent;
  border-radius: var(--r-sm);
  background: none;
  color: rgba(255, 255, 255, 0.72);
  cursor: pointer;
  text-align: left;
  transition: background-color var(--dur-2), border-color var(--dur-2), color var(--dur-2);
}

.queue__item:hover {
  background: rgba(255, 255, 255, 0.07);
  color: #fff;
}

.queue__item.is-active {
  border-color: rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.queue__item:focus-visible {
  outline: 2px solid var(--bm-cyan);
  outline-offset: 2px;
}

.queue__thumb {
  display: block;
  aspect-ratio: 16 / 10;
  overflow: hidden;
  border-radius: 8px;
  background: #0b111d;
}

.queue__thumb img,
.queue__thumb video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.queue__text {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.queue__text small {
  color: var(--bm-cyan);
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.1em;
}

.queue__text b {
  display: -webkit-box;
  overflow: hidden;
  font-size: 12.5px;
  font-weight: 700;
  line-height: 1.3;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

/* The story on screen fills up with the autoplay timer. */
.queue__progress {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--bm-blue), var(--bm-cyan));
  transform: scaleX(0);
  transform-origin: left;
  animation: queue-fill var(--news-interval, 30s) linear forwards;
}

.is-paused .queue__progress {
  animation-play-state: paused;
}

@keyframes queue-fill {
  to {
    transform: scaleX(1);
  }
}

.queue-move-move {
  transition: transform 500ms var(--ease-ios);
}

.queue-move-enter-active,
.queue-move-leave-active {
  transition: opacity 300ms var(--ease-out), transform 500ms var(--ease-ios);
}

.queue-move-enter-from,
.queue-move-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

/* Leaving entries step out of the flow so the others can slide up. */
.queue-move-leave-active {
  position: absolute;
  right: 0;
  left: 0;
}

/* No room beside the story: the banner shows its dots instead. */
@media (max-width: 1100px) {
  .queue {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .queue__progress {
    display: none;
  }

  .queue-move-move,
  .queue-move-enter-active,
  .queue-move-leave-active {
    transition: none;
  }
}
</style>
