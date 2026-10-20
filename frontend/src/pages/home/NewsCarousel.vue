<script setup>
// League news as a full-width broadcast banner: the current story fills the
// frame with its number, date and headline; on wide screens a rail on the
// right lists what comes next, and a bar along the bottom fills up with the
// autoplay timer. Behaviour is unchanged: the pinned item opens first,
// autoplay follows the admin interval and pauses after manual navigation, and
// every item opens full screen. The eye button hides the preview (headline,
// text, shade and queue) and leaves the picture alone; the choice is kept
// in the browser. With nothing published the banner keeps its place and
// says so.
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowUpRight, ChevronLeft, ChevronRight, Eye, EyeOff, Maximize2, Newspaper, Pin, Plus } from 'lucide-vue-next'
import { isVideoUrl } from '../../media'
import { state } from '../../store'
import { formatShortDate } from '../../timezone'
import RacingLines from '../../ui/fx/RacingLines.vue'
import NewsQueue from './NewsQueue.vue'
import NewsViewer from './NewsViewer.vue'

const props = defineProps({
  news: { type: Array, required: true },
  settings: { type: Object, default: () => ({ auto_rotate_seconds: 30, manual_pause_seconds: 300 }) }
})

const { t } = useI18n()
const track = ref(null)
const active = ref(0)
const viewerOpen = ref(false)
const paused = ref(false)
const cycle = ref(0)
let autoplayTimer = null
let pauseTimer = null
let scrollResetTimer = null
let programmaticScroll = false
let scrollTarget = 0
let manualPauseUntil = 0
// Fallback for scrolls that never arrive exactly (e.g. already at the target).
const SCROLL_SETTLE_MS = { smooth: 1200, auto: 80 }
// Stories listed in the rail: the current one and what follows it.
const RAIL_LIMIT = 4
const PREVIEW_HIDDEN_KEY = 'bmrl-news-preview-hidden'

const previewHidden = ref(readPreviewHidden())

function readPreviewHidden() {
  try {
    return window.localStorage.getItem(PREVIEW_HIDDEN_KEY) === '1'
  } catch {
    return false
  }
}

function togglePreview() {
  previewHidden.value = !previewHidden.value
  try {
    window.localStorage.setItem(PREVIEW_HIDDEN_KEY, previewHidden.value ? '1' : '0')
  } catch {
    // Without storage the choice lasts until the page is left.
  }
}

const current = computed(() => props.news[active.value] || null)
const canManageNews = computed(() => state.user?.status === 'active' && ['admin', 'moder', 'smm'].includes(state.user?.role))
const intervalSeconds = computed(() => Math.max(5, Number(props.settings.auto_rotate_seconds) || 30))
// The queue starts at the current story and wraps round to the first.
const rail = computed(() =>
  Array.from({ length: Math.min(RAIL_LIMIT, props.news.length) }, (_, offset) => {
    const index = wrap(active.value + offset)
    return { index, item: props.news[index] }
  })
)

/** Two-digit slide numbers, as on a timing screen. */
function slideNumber(index) {
  return String(index + 1).padStart(2, '0')
}

function wrap(index) {
  const total = props.news.length
  return total ? ((index % total) + total) % total : 0
}

function clearAutoplay() {
  if (autoplayTimer !== null) {
    window.clearInterval(autoplayTimer)
    autoplayTimer = null
  }
}

function startAutoplay() {
  clearAutoplay()
  if (props.news.length < 2) return
  autoplayTimer = window.setInterval(() => {
    if (viewerOpen.value || Date.now() < manualPauseUntil) return
    goTo(active.value + 1, 'smooth', false)
  }, intervalSeconds.value * 1000)
}

function pauseAfterManual() {
  const pause = Math.max(0, Number(props.settings.manual_pause_seconds) || 0) * 1000
  manualPauseUntil = Date.now() + pause
  paused.value = pause > 0
  if (pauseTimer !== null) window.clearTimeout(pauseTimer)
  if (!pause) {
    startAutoplay()
    return
  }
  pauseTimer = window.setTimeout(() => {
    manualPauseUntil = 0
    paused.value = false
    cycle.value += 1
    startAutoplay()
  }, pause)
}

function goTo(index, behavior = 'smooth', manual = false) {
  if (manual) pauseAfterManual()
  const next = wrap(index)
  active.value = next
  cycle.value += 1
  if (!manual && !viewerOpen.value) startAutoplay()
  const el = track.value
  if (!el) return
  programmaticScroll = true
  scrollTarget = next * el.clientWidth
  if (scrollResetTimer !== null) window.clearTimeout(scrollResetTimer)
  scrollResetTimer = window.setTimeout(() => { programmaticScroll = false }, SCROLL_SETTLE_MS[behavior] ?? SCROLL_SETTLE_MS.smooth)
  el.scrollTo({ left: scrollTarget, behavior })
}

function syncFromScroll() {
  const el = track.value
  // While goTo() animates the track, the slide under the midpoint is not the
  // target yet; syncing then would flick the counter back and forth.
  if (!el?.clientWidth) return
  if (programmaticScroll) {
    if (Math.abs(el.scrollLeft - scrollTarget) < 2) programmaticScroll = false
    return
  }
  const next = Math.min(Math.max(Math.round(el.scrollLeft / el.clientWidth), 0), props.news.length - 1)
  if (next === active.value) return
  pauseAfterManual()
  cycle.value += 1
  active.value = next
}

function openViewer(index) {
  goTo(index, 'auto')
  viewerOpen.value = true
}

function initialIndex() {
  const pinned = props.news.findIndex((item) => item.is_pinned)
  return pinned >= 0 ? pinned : 0
}

onMounted(() => {
  requestAnimationFrame(() => goTo(initialIndex(), 'auto'))
  startAutoplay()
})

watch(() => props.news.map((item) => item.id).join(','), () => {
  goTo(initialIndex(), 'auto')
  startAutoplay()
})

onBeforeUnmount(() => {
  clearAutoplay()
  if (pauseTimer !== null) window.clearTimeout(pauseTimer)
  if (scrollResetTimer !== null) window.clearTimeout(scrollResetTimer)
})
</script>

<template>
  <section v-if="news.length" v-reveal class="news" :class="{ 'is-clean': previewHidden }" :aria-label="t('news.title')" :style="{ '--news-interval': `${intervalSeconds}s` }">
    <div ref="track" class="news__track" @scroll.passive="syncFromScroll">
      <article
        v-for="(item, index) in news"
        :key="item.id"
        class="news__slide"
        :class="{ 'is-active': index === active }"
        role="button"
        tabindex="0"
        :aria-label="`${t('news.openFullscreen')}: ${item.title}`"
        @click="openViewer(index)"
        @keydown.enter.prevent="openViewer(index)"
        @keydown.space.prevent="openViewer(index)"
      >
        <video v-if="isVideoUrl(item.image_url)" class="news__media" :src="item.image_url" autoplay muted loop playsinline preload="metadata"></video>
        <img v-else class="news__media" :src="item.image_url" alt="" :loading="index === 0 ? 'eager' : 'lazy'" />
        <div class="news__shade" aria-hidden="true"></div>
        <div class="news__content">
          <span class="news__number ui-outline-text" aria-hidden="true">{{ slideNumber(index) }}</span>
          <p class="news__meta">
            <span class="ui-num">{{ formatShortDate(item.created_at) }}</span>
            <span v-if="item.is_pinned" class="news__tag"><Pin :size="12" />{{ t('home.news.pinned') }}</span>
          </p>
          <h3 class="news__title">{{ item.title }}</h3>
          <p class="news__body">{{ item.body }}</p>
          <span class="news__read">{{ t('home.news.read') }}<ArrowUpRight :size="16" /></span>
        </div>
      </article>
    </div>

    <div class="news__top">
      <span class="news__pill news__pill--label"><span class="ui-dot ui-dot--blue ui-dot--live"></span>{{ t('news.title') }}</span>
      <span class="news__pill news__pill--count ui-num" aria-live="polite">{{ slideNumber(active) }} / {{ slideNumber(news.length - 1) }}</span>
      <button
        class="news__round"
        type="button"
        :aria-pressed="previewHidden"
        :aria-label="previewHidden ? t('home.news.showPreview') : t('home.news.hidePreview')"
        :title="previewHidden ? t('home.news.showPreview') : t('home.news.hidePreview')"
        @click.stop="togglePreview"
      >
        <EyeOff v-if="previewHidden" :size="17" />
        <Eye v-else :size="17" />
      </button>
      <button class="news__round" type="button" :aria-label="t('news.openFullscreen')" :title="t('news.openFullscreen')" @click.stop="openViewer(active)"><Maximize2 :size="17" /></button>
    </div>

    <template v-if="news.length > 1">
      <button class="news__round news__arrow news__arrow--prev" type="button" :aria-label="t('news.scrollLeft')" @click.stop="goTo(active - 1, 'smooth', true)"><ChevronLeft :size="22" /></button>
      <button class="news__round news__arrow news__arrow--next" type="button" :aria-label="t('news.scrollRight')" @click.stop="goTo(active + 1, 'smooth', true)"><ChevronRight :size="22" /></button>
      <!-- Wide screens list what comes next; narrower ones fall back to the dots. -->
      <NewsQueue v-if="!previewHidden" :entries="rail" :active="active" :paused="paused" :cycle="cycle" @select="goTo($event, 'smooth', true)" />

      <div class="news__dots" role="tablist" :aria-label="t('news.indicators')">
        <button
          v-for="(item, index) in news"
          :key="item.id"
          class="news__dot"
          :class="{ 'is-active': index === active, 'is-paused': paused }"
          type="button"
          role="tab"
          :aria-selected="index === active"
          :aria-label="t('news.goTo', { number: index + 1 })"
          @click.stop="goTo(index, 'smooth', true)"
        >
          <span :key="index === active ? `run-${cycle}` : 'idle'"></span>
        </button>
      </div>
      <span :key="`bar-${cycle}`" class="news__bar" :class="{ 'is-paused': paused }" aria-hidden="true"></span>
    </template>
  </section>

  <section v-else v-reveal class="news news--empty" :aria-label="t('news.title')">
    <RacingLines class="news__lines" :count="12" />
    <div class="news__top">
      <span class="news__pill">{{ t('news.title') }}</span>
    </div>
    <div class="news__content">
      <span class="news__empty-icon"><Newspaper :size="22" /></span>
      <h3 class="news__title">{{ t('home.newsEmpty.title') }}</h3>
      <p class="news__body">{{ t('home.newsEmpty.text') }}</p>
      <RouterLink v-if="canManageNews" class="ui-btn ui-btn--primary news__add" to="/news/manage"><Plus :size="17" />{{ t('home.newsEmpty.action') }}</RouterLink>
    </div>
  </section>

  <NewsViewer
    :open="viewerOpen"
    :item="current"
    :position="active + 1"
    :total="news.length"
    @close="viewerOpen = false"
    @prev="goTo(active - 1, 'smooth', true)"
    @next="goTo(active + 1, 'smooth', true)"
  />
</template>

<style scoped>
.news {
  position: relative;
  /* A height, not an aspect ratio: with a ratio the height limit also capped
     the width, and on wide screens the banner stopped short of the right edge. */
  height: clamp(360px, 38vw, 600px);
  overflow: hidden;
  border: 1px solid var(--c-line);
  border-radius: var(--r-xl);
  background: #05070d;
  box-shadow: var(--shadow-2);
  isolation: isolate;
}

.news__track {
  display: flex;
  height: 100%;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  scrollbar-width: none;
}

.news__track::-webkit-scrollbar {
  display: none;
}

.news__slide {
  position: relative;
  flex: 0 0 100%;
  height: 100%;
  overflow: hidden;
  cursor: zoom-in;
  scroll-snap-align: start;
}

.news__media {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transform-origin: 60% 40%;
}

/* A slow push-in while the slide is on screen, timed to the autoplay interval. */
.news__slide.is-active .news__media {
  animation: news-push var(--news-interval, 30s) linear forwards;
}

@keyframes news-push {
  from {
    transform: scale(1);
  }
  to {
    transform: scale(1.06);
  }
}

.news__shade {
  position: absolute;
  inset: 0;
  transition: opacity var(--dur-3) var(--ease-out);
  background:
    linear-gradient(180deg, rgba(3, 6, 12, 0.5) 0%, transparent 24%),
    linear-gradient(0deg, rgba(3, 6, 12, 0.94) 0%, rgba(3, 6, 12, 0.62) 30%, transparent 62%);
}

.news__content {
  position: absolute;
  bottom: 0;
  left: 0;
  transition: opacity var(--dur-3) var(--ease-out), visibility var(--dur-3);
  display: grid;
  justify-items: start;
  gap: 12px;
  /* Leaves the right side to the queue rail. */
  width: min(860px, 62%);
  padding: 0 clamp(20px, 3vw, 44px) clamp(30px, 3.6vw, 46px) clamp(20px, 6.4vw, 92px);
  color: #fff;
}

/* The slide number, drawn as an outline over the picture. */
.news__number {
  --outline-color: rgba(255, 255, 255, 0.5);
  --outline-width: 1.25px;
  margin-bottom: -6px;
  font-family: var(--font-display);
  font-size: clamp(46px, 5.6vw, 92px);
  font-weight: 900;
  letter-spacing: -0.02em;
  line-height: 0.9;
}

.news__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  margin: 0;
  color: rgba(255, 255, 255, 0.72);
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.news__tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 9px;
  border-radius: var(--r-pill);
  background: var(--bm-blue);
  color: #fff;
  font-size: 10.5px;
}

.news__read {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 38px;
  margin-top: 2px;
  padding: 0 16px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: var(--r-pill);
  background: rgba(8, 12, 22, 0.42);
  color: #fff;
  font-size: 13.5px;
  font-weight: 700;
  -webkit-backdrop-filter: blur(12px) saturate(160%);
  backdrop-filter: blur(12px) saturate(160%);
  transition: background-color var(--dur-2), border-color var(--dur-2), opacity 600ms var(--ease-out), transform 800ms var(--ease-ios);
}

.news__slide:hover .news__read {
  border-color: transparent;
  background: var(--bm-blue);
}

/* The headline rises in each time its slide becomes the current one. */
.news__content > * {
  opacity: 0;
  transform: translateY(14px);
  transition: opacity 600ms var(--ease-out), transform 800ms var(--ease-ios);
}

.news__slide.is-active .news__content > * {
  opacity: 1;
  transform: none;
}

.news__slide.is-active .news__title {
  transition-delay: 80ms;
}

.news__slide.is-active .news__body {
  transition-delay: 160ms;
}

.news__slide.is-active .news__read {
  transition-delay: 240ms;
}

.news__title {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: #fff;
  font-family: var(--font-body);
  font-size: clamp(22px, 2.6vw, 40px);
  font-weight: 800;
  letter-spacing: -0.015em;
  line-height: 1.12;
  text-shadow: 0 2px 24px rgba(0, 0, 0, 0.45);
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.news__body {
  display: -webkit-box;
  max-width: 720px;
  margin: 0;
  overflow: hidden;
  color: rgba(255, 255, 255, 0.84);
  font-size: clamp(14px, 1.2vw, 16px);
  font-weight: 500;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.news__top {
  position: absolute;
  top: clamp(14px, 1.8vw, 22px);
  right: clamp(14px, 1.8vw, 22px);
  left: clamp(14px, 1.8vw, 22px);
  z-index: 3;
  display: flex;
  align-items: center;
  gap: 8px;
  pointer-events: none;
}

.news__top > * {
  pointer-events: auto;
}

.news__pill {
  display: inline-flex;
  align-items: center;
  height: 34px;
  padding: 0 14px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: var(--r-pill);
  background: rgba(8, 12, 22, 0.5);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  -webkit-backdrop-filter: blur(14px) saturate(160%);
  backdrop-filter: blur(14px) saturate(160%);
}

.news__pill--label {
  gap: 9px;
  font-family: var(--font-mono);
  font-size: 11.5px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.news__pill--count {
  margin-left: auto;
  font-size: 13.5px;
  letter-spacing: 0.06em;
}

.news__round {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  padding: 0;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 50%;
  background: rgba(8, 12, 22, 0.5);
  color: #fff;
  cursor: pointer;
  -webkit-backdrop-filter: blur(14px) saturate(160%);
  backdrop-filter: blur(14px) saturate(160%);
  transition: background-color var(--dur-2), border-color var(--dur-2), transform var(--dur-2) var(--ease-ios);
}

.news__round:hover {
  border-color: transparent;
  background: var(--bm-blue);
}

.news__round:active {
  transform: scale(0.92);
}

.news__round:focus-visible,
.news__dot:focus-visible,
.news__slide:focus-visible {
  outline: 2px solid var(--bm-cyan);
  outline-offset: 2px;
}

.news__arrow {
  position: absolute;
  top: 50%;
  z-index: 3;
  width: 50px;
  height: 50px;
  margin-top: -25px;
}

.news__arrow--prev {
  left: clamp(12px, 1.6vw, 20px);
}

.news__arrow--next {
  right: clamp(12px, 1.6vw, 20px);
}

/* ---------- Autoplay bar along the bottom edge ---------- */
.news__bar {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 3;
  height: 3px;
  background: linear-gradient(90deg, var(--bm-blue), var(--bm-cyan));
  transform: scaleX(0);
  transform-origin: left;
  animation: news-fill var(--news-interval, 30s) linear forwards;
}

.news__bar.is-paused {
  animation-play-state: paused;
}

@keyframes news-fill {
  to {
    transform: scaleX(1);
  }
}

/* Preview hidden: the picture alone. The controls stay, and the dots stand
   in for the queue on every width. */
.news.is-clean .news__shade {
  opacity: 0;
}

.news.is-clean .news__content {
  visibility: hidden;
  opacity: 0;
  pointer-events: none;
}

.news.is-clean .news__dots {
  display: flex;
}

/* Dots take over from the queue (NewsQueue.vue) where there is no room for it. */
.news__dots {
  position: absolute;
  right: clamp(18px, 2.4vw, 32px);
  bottom: clamp(22px, 3.4vw, 40px);
  z-index: 3;
  display: none;
  align-items: center;
  gap: 4px;
}

@media (max-width: 1100px) {
  .news__dots {
    display: flex;
  }

  .news__content {
    width: min(860px, 82%);
  }
}

.news__dot {
  display: grid;
  place-items: center;
  height: 22px;
  padding: 0 4px;
  border: 0;
  background: none;
  cursor: pointer;
}

.news__dot span {
  display: block;
  width: 9px;
  height: 9px;
  overflow: hidden;
  border-radius: var(--r-pill);
  background: rgba(255, 255, 255, 0.42);
  transition: width 500ms var(--ease-ios), background-color var(--dur-2);
}

.news__dot:hover span {
  background: rgba(255, 255, 255, 0.75);
}

/* The active indicator stretches into a pill and fills with the autoplay timer. */
.news__dot.is-active span {
  width: 38px;
  background: rgba(255, 255, 255, 0.3);
}

.news__dot.is-active span::after {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: inherit;
  background: #fff;
  content: '';
  transform: scaleX(0);
  transform-origin: left;
  animation: news-progress var(--news-interval, 30s) linear forwards;
}

.news__dot.is-active.is-paused span::after {
  animation: none;
  transform: scaleX(1);
}

@keyframes news-progress {
  to {
    transform: scaleX(1);
  }
}

/* Empty state: same frame and placement, themed surface instead of a photo. */
.news--empty {
  aspect-ratio: auto;
  min-height: 300px;
  background:
    radial-gradient(70% 90% at 85% 0%, color-mix(in srgb, var(--bm-blue) 34%, transparent), transparent 70%),
    radial-gradient(55% 80% at 0% 100%, color-mix(in srgb, var(--bm-blue-deep) 40%, transparent), transparent 70%),
    var(--c-surface-solid);
}

.news__lines {
  opacity: 0.7;
}

.news--empty .news__content {
  justify-items: start;
  max-width: 680px;
}

.news--empty .news__content > * {
  opacity: 1;
  transform: none;
}

.news--empty .news__title {
  color: var(--c-text);
  text-shadow: none;
}

.news--empty .news__body {
  color: var(--c-text-2);
}

.news--empty .news__pill {
  border-color: var(--c-line);
  background: var(--c-sunken);
  color: var(--c-text);
}

.news__empty-icon {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border: 1px solid var(--c-blue-line);
  border-radius: 14px;
  background: color-mix(in srgb, var(--bm-blue) 20%, transparent);
  color: var(--c-accent-text);
}

.news__add {
  margin-top: 4px;
}

@media (max-width: 760px) {
  .news {
    height: clamp(380px, 104vw, 480px);
  }

  .news__content {
    width: 100%;
    padding: 0 18px 52px;
  }

  .news__read {
    display: none;
  }

  .news__arrow {
    display: none;
  }

  .news__dots {
    right: 50%;
    bottom: 16px;
    transform: translateX(50%);
  }
}

@media (prefers-reduced-motion: reduce) {
  .news__slide.is-active .news__media {
    animation: none;
  }

  .news__content > * {
    opacity: 1;
    transform: none;
    transition: none;
  }

  .news__dot.is-active span::after {
    animation: none;
    transform: scaleX(1);
  }

  .news__bar {
    display: none;
  }
}
</style>
