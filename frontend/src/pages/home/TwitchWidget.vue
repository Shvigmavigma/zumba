<script setup>
// Floating Twitch picture-in-picture: draggable, collapsible (remembered per
// browser) and opening a full player. Shows the live stream or the latest VOD.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Maximize2, Minimize2, PlayCircle, Radio, X } from 'lucide-vue-next'
import { api } from '../../api'
import { safeHttpUrl } from '../../safeUrl'
import { validTwitchParent } from '../../twitchEmbed'

const { t } = useI18n()
const DEFAULT_STATUS = {
  channel_login: 'bmrlracing',
  channel_url: 'https://www.twitch.tv/bmrlracing',
  is_configured: false,
  is_live: false,
  status: 'channel',
  embed_type: 'channel',
  embed_value: 'bmrlracing',
  external_url: 'https://www.twitch.tv/bmrlracing',
  title: '',
  game_name: '',
  thumbnail_url: '',
  viewer_count: null
}
const MARGIN = 16
const PHONE_BOTTOM = 100

const saved = typeof localStorage === 'undefined' ? null : localStorage.getItem('twitchWidgetCollapsed')
const status = ref({ ...DEFAULT_STATUS })
const viewerOpen = ref(false)
const collapsed = ref(saved === null ? true : saved === 'true')
const position = ref({ x: 24, y: 120 })
const pip = ref(null)
const drag = ref(null)
const dragged = ref(false)
let userMoved = false
const previewStart = Math.floor(Math.random() * 900) + 15

const parent = computed(() => validTwitchParent(typeof window === 'undefined' ? 'localhost' : window.location.hostname))
const canEmbed = computed(() => {
  if (!parent.value) return false
  if (status.value.is_live && status.value.embed_type === 'channel') return true
  return status.value.status === 'vod' && status.value.embed_type === 'video' && Boolean(status.value.embed_value)
})
const canPreview = computed(() => status.value.is_live && canEmbed.value)
const statusText = computed(() => {
  if (status.value.is_live) return t('twitch.live')
  if (status.value.status === 'vod') return t('twitch.latestVideo')
  return t('twitch.channel')
})
const title = computed(() => status.value.title || (status.value.status === 'vod' ? t('twitch.latestVideo') : t('twitch.channel')))
const style = computed(() => ({ transform: `translate3d(${position.value.x}px, ${position.value.y}px, 0)` }))

function formatTime(total) {
  return `${Math.floor(total / 3600)}h${Math.floor((total % 3600) / 60)}m${total % 60}s`
}

function embedSrc({ autoplay = false, preview = false } = {}) {
  if (!parent.value) return ''
  const params = new URLSearchParams({ parent: parent.value, muted: 'true', autoplay: autoplay ? 'true' : 'false' })
  if (status.value.embed_type === 'video' && status.value.embed_value) {
    params.set('video', status.value.embed_value)
    if (preview) params.set('time', formatTime(previewStart))
  } else {
    params.set('channel', status.value.channel_login || DEFAULT_STATUS.channel_login)
  }
  return `https://player.twitch.tv/?${params.toString()}`
}

function size() {
  if (collapsed.value) return { width: pip.value?.offsetWidth || 200, height: pip.value?.offsetHeight || 52 }
  const width = window.innerWidth <= 520 ? Math.max(280, window.innerWidth - 32) : 380
  return { width, height: Math.round(width * 0.56) + 64 }
}

function bottomMargin() {
  return window.innerWidth <= 760 ? PHONE_BOTTOM : MARGIN
}

function clamp(next = position.value) {
  const { width, height } = size()
  const maxX = Math.max(MARGIN, window.innerWidth - width - MARGIN)
  const maxY = Math.max(MARGIN, window.innerHeight - height - bottomMargin())
  position.value = { x: Math.min(Math.max(MARGIN, next.x), maxX), y: Math.min(Math.max(MARGIN, next.y), maxY) }
}

function placeDefault() {
  const { width, height } = size()
  clamp({ x: window.innerWidth - width - MARGIN, y: window.innerHeight - height - bottomMargin() })
}

function startDrag(event) {
  if (event.button !== undefined && event.button !== 0) return
  drag.value = { id: event.pointerId, sx: event.clientX, sy: event.clientY, bx: position.value.x, by: position.value.y }
  try {
    event.currentTarget.setPointerCapture?.(event.pointerId)
  } catch {
    // Synthetic events cannot capture; window listeners still track the drag.
  }
  window.addEventListener('pointermove', onDrag)
  window.addEventListener('pointerup', stopDrag, { once: true })
}

function onDrag(event) {
  const current = drag.value
  if (!current || current.id !== event.pointerId) return
  const dx = event.clientX - current.sx
  const dy = event.clientY - current.sy
  if (Math.abs(dx) + Math.abs(dy) > 5) {
    dragged.value = true
    userMoved = true
  }
  clamp({ x: current.bx + dx, y: current.by + dy })
}

function stopDrag() {
  drag.value = null
  window.removeEventListener('pointermove', onDrag)
}

function openFromWidget() {
  if (dragged.value) {
    dragged.value = false
    return
  }
  viewerOpen.value = true
}

function toggleCollapsed(event) {
  event?.stopPropagation()
  collapsed.value = !collapsed.value
  localStorage.setItem('twitchWidgetCollapsed', collapsed.value ? 'true' : 'false')
  requestAnimationFrame(() => (userMoved ? clamp() : placeDefault()))
}

function onKeydown(event) {
  if (event.key === 'Escape' && viewerOpen.value) {
    event.preventDefault()
    viewerOpen.value = false
  }
}

function onResize() {
  // Until the pilot drags it, the widget stays docked bottom-right.
  if (userMoved) clamp()
  else placeDefault()
}

onMounted(async () => {
  window.addEventListener('keydown', onKeydown)
  window.addEventListener('resize', onResize)
  placeDefault()
  try {
    status.value = { ...DEFAULT_STATUS, ...(await api('/twitch/status')) }
  } catch {
    status.value = { ...DEFAULT_STATUS }
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('resize', onResize)
  window.removeEventListener('pointermove', onDrag)
})
</script>

<template>
  <Teleport to="body">
    <div
      ref="pip"
      class="pip ui-glass ui-glass--strong"
      :class="{ 'is-collapsed': collapsed, 'is-live': status.is_live, 'is-dragging': drag }"
      role="button"
      tabindex="0"
      :style="style"
      :title="t('twitch.dragHint')"
      @click="openFromWidget"
      @keydown.enter.prevent="viewerOpen = true"
      @keydown.space.prevent="viewerOpen = true"
      @pointerdown="startDrag"
    >
      <span class="pip__head">
        <span class="pip__badge" :class="{ 'is-live': status.is_live }">
          <span class="ui-dot" :class="status.is_live ? 'ui-dot--red ui-dot--live' : ''"></span>{{ statusText }}
        </span>
        <span v-if="collapsed" class="pip__mini-title">Twitch</span>
        <button
          class="pip__toggle"
          type="button"
          :title="collapsed ? t('twitch.expandWidget') : t('twitch.collapseWidget')"
          :aria-label="collapsed ? t('twitch.expandWidget') : t('twitch.collapseWidget')"
          @click.stop="toggleCollapsed"
          @pointerdown.stop
        >
          <Maximize2 v-if="collapsed" :size="14" />
          <Minimize2 v-else :size="14" />
        </button>
      </span>
      <span v-if="!collapsed" class="pip__screen">
        <iframe v-if="canPreview" :src="embedSrc({ preview: true })" title="BMRL Twitch preview" allow="autoplay; fullscreen; picture-in-picture" scrolling="no"></iframe>
        <img v-else-if="status.thumbnail_url" :src="status.thumbnail_url" alt="" />
        <span class="pip__play"><PlayCircle :size="38" /></span>
      </span>
      <strong v-if="!collapsed" class="pip__title">{{ title }}</strong>
    </div>

    <Transition name="ui-fade">
      <div v-if="viewerOpen" class="player-backdrop" role="dialog" aria-modal="true" :aria-label="title" @click="viewerOpen = false">
        <div class="player ui-glass ui-glass--strong" @click.stop>
          <header class="player__head">
            <div>
              <span class="ui-eyebrow"><Radio :size="14" />Twitch</span>
              <h2 class="player__title">{{ title }}</h2>
            </div>
            <button class="ui-btn ui-btn--ghost ui-btn--icon" type="button" :aria-label="t('twitch.closePlayer')" @click="viewerOpen = false"><X :size="20" /></button>
          </header>
          <div v-if="canEmbed" class="player__frame">
            <iframe :src="embedSrc({ autoplay: status.is_live })" title="BMRL Twitch" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen scrolling="no"></iframe>
          </div>
          <div v-else class="player__empty">
            <Radio :size="34" />
            <strong>{{ t('twitch.unavailable') }}</strong>
            <p>{{ t('twitch.playerUnavailable') }}</p>
            <a class="ui-btn ui-btn--primary" :href="safeHttpUrl(status.external_url) || safeHttpUrl(status.channel_url) || undefined" target="_blank" rel="noopener noreferrer">{{ t('twitch.openTwitch') }}</a>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.pip {
  position: fixed;
  top: 0;
  left: 0;
  z-index: 55;
  display: grid;
  gap: 8px;
  width: 380px;
  max-width: calc(100vw - 32px);
  padding: 8px;
  border-radius: 20px;
  box-shadow: var(--shadow-2);
  cursor: grab;
  touch-action: none;
  user-select: none;
  transition: width 420ms var(--ease-ios), box-shadow var(--dur-2);
}

.pip.is-dragging {
  cursor: grabbing;
  transition: none;
}

.pip.is-collapsed {
  width: max-content;
  border-radius: var(--r-pill);
}

@media (max-width: 760px) {
  .pip.is-collapsed .pip__mini-title {
    display: none;
  }
}

.pip.is-live {
  box-shadow: var(--shadow-2), 0 0 0 1px color-mix(in srgb, var(--bm-red) 40%, transparent);
}

.pip__head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pip__badge {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 5px 10px;
  border-radius: var(--r-pill);
  background: color-mix(in srgb, #9146ff 22%, transparent);
  color: var(--c-text);
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
}

.pip__badge.is-live {
  background: color-mix(in srgb, var(--bm-red) 22%, transparent);
}

.pip__mini-title {
  flex: 1 1 auto;
  color: var(--c-text-2);
  font-size: 13px;
  font-weight: 600;
}

.pip__toggle {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  margin-left: auto;
  border: 1px solid var(--c-line);
  border-radius: 50%;
  background: var(--c-sunken);
  color: var(--c-text-2);
  cursor: pointer;
}

.pip__screen {
  position: relative;
  display: block;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-radius: 14px;
  background: radial-gradient(70% 70% at 50% 40%, #2a1858, #0a0614);
}

.pip__screen iframe,
.pip__screen img {
  width: 100%;
  height: 100%;
  border: 0;
  object-fit: cover;
  pointer-events: none;
}

.pip__play {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: rgba(255, 255, 255, 0.9);
  transition: transform var(--dur-3) var(--ease-spring);
}

.pip:hover .pip__play {
  transform: scale(1.1);
}

.pip__title {
  padding: 0 4px 2px;
  overflow: hidden;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.player-backdrop {
  position: fixed;
  inset: 0;
  z-index: 120;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(2, 4, 9, 0.8);
  -webkit-backdrop-filter: blur(14px);
  backdrop-filter: blur(14px);
}

.player {
  display: grid;
  gap: 14px;
  width: min(1180px, 100%);
  padding: 16px;
  border-radius: var(--r-xl);
}

.player__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.player__head > div {
  display: grid;
  gap: 6px;
}

.player__title {
  margin: 0;
  font-size: 18px;
}

.player__frame {
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-radius: var(--r-lg);
  background: #000;
}

.player__frame iframe {
  width: 100%;
  height: 100%;
  border: 0;
}

.player__empty {
  display: grid;
  justify-items: center;
  gap: 10px;
  padding: 48px 20px;
  color: var(--c-text-2);
  text-align: center;
}

.player__empty p {
  max-width: 50ch;
  margin: 0;
}
</style>
