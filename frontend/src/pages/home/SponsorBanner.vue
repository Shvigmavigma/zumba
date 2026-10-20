<script setup>
// Sponsor slot (top, bottom, left, right). Artwork keeps its uploaded ratio
// and is never tinted or cropped.
import { useI18n } from 'vue-i18n'
import { isVideoUrl } from '../../media'
import { safeHttpUrl } from '../../safeUrl'

defineProps({
  banner: { type: Object, required: true },
  variant: { type: String, default: 'wide' },
  priority: { type: Boolean, default: false }
})
const { t } = useI18n()
</script>

<template>
  <a v-spotlight class="sponsor" :class="`sponsor--${variant}`" :href="safeHttpUrl(banner.link_url) || undefined" target="_blank" rel="noopener noreferrer sponsored">
    <video v-if="isVideoUrl(banner.image_url)" :src="banner.image_url" autoplay muted loop playsinline preload="metadata"></video>
    <img v-else :src="banner.image_url" alt="" :decoding="priority ? 'sync' : 'async'" :fetchpriority="priority ? 'high' : 'auto'" :loading="priority ? 'eager' : 'lazy'" />
    <span class="sponsor__label">{{ t('home.sponsor') }}</span>
  </a>
</template>

<style scoped>
.sponsor {
  position: relative;
  display: block;
  overflow: hidden;
  border: 1px solid var(--c-line);
  border-radius: var(--r-lg);
  background: var(--c-surface-solid);
  transition: transform var(--dur-3) var(--ease-ios), border-color var(--dur-2);
}

.sponsor:hover {
  border-color: var(--c-blue-line);
  transform: translateY(-2px);
}

.sponsor img,
.sponsor video {
  display: block;
  width: 100%;
  height: auto;
}

.sponsor--side img,
.sponsor--side video {
  height: auto;
}

.sponsor__label {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 3px 8px;
  border-radius: var(--r-pill);
  background: rgba(4, 6, 11, 0.55);
  color: rgba(255, 255, 255, 0.78);
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
}
</style>
