<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Check, Crop, Image as ImageIcon, Link as LinkIcon, Save, Trash2, Upload, X } from 'lucide-vue-next'
import { api } from '../api'

const { t } = useI18n()
const banners = ref([])
const error = ref('')
const saving = ref({})
const uploading = ref({})
const clearing = ref({})
const savedPosition = ref('')
const openedBanner = ref(null)
const cropper = ref(null)
const cropFrame = ref(null)
const cropImage = ref(null)
const cropFrameSize = ref({ width: 0, height: 0 })
const cropError = ref('')

const positionOrder = ['top', 'left', 'right', 'bottom']
const cropTargets = {
  top: { width: 1280, height: 230 },
  bottom: { width: 760, height: 150 },
  left: { width: 245, height: 760 },
  right: { width: 245, height: 760 }
}
const sortedBanners = computed(() => [...banners.value].sort((a, b) => positionOrder.indexOf(a.position) - positionOrder.indexOf(b.position)))
const cropTarget = computed(() => (cropper.value ? cropTargets[cropper.value.position] || cropTargets.top : cropTargets.top))
const cropFrameStyle = computed(() => ({
  aspectRatio: `${cropTarget.value.width} / ${cropTarget.value.height}`
}))
const cropImageStyle = computed(() => {
  const geometry = cropGeometry()
  if (!geometry) return {}
  return {
    width: `${geometry.displayWidth}px`,
    height: `${geometry.displayHeight}px`,
    transform: `translate(-50%, -50%) translate(${cropper.value.offsetX}px, ${cropper.value.offsetY}px)`
  }
})

function bannerMeta(position) {
  const key = `banners.positions.${position}`
  const title = t(`${key}.title`)
  if (title === `${key}.title`) {
    return { title: position, description: '', sizeHint: '', badge: position.toUpperCase() }
  }
  return {
    title,
    description: t(`${key}.description`),
    sizeHint: t(`${key}.sizeHint`),
    badge: t(`${key}.badge`)
  }
}

async function load() {
  try {
    banners.value = await api('/banners')
  } catch (err) {
    error.value = err.message
  }
}

function updateBanner(updated) {
  banners.value = banners.value.map((banner) => (banner.position === updated.position ? updated : banner))
}

async function save(banner) {
  error.value = ''
  saving.value = { ...saving.value, [banner.position]: true }
  try {
    const updated = await api(`/banners/${banner.position}`, { method: 'PUT', body: banner })
    updateBanner(updated)
    savedPosition.value = banner.position
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = { ...saving.value, [banner.position]: false }
  }
}

async function uploadToPosition(banner, event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return

  if (isGifFile(file)) {
    await uploadOriginal(banner, file)
    return
  }

  openCropper(banner, URL.createObjectURL(file), file)
}

function isGifFile(file) {
  return file.type === 'image/gif' || /\.gif$/i.test(file.name || '')
}

function isGifBanner(banner) {
  return /\.gif(?:$|\?)/i.test(banner.image_url || '')
}

async function uploadOriginal(banner, file) {
  error.value = ''
  uploading.value = { ...uploading.value, [banner.position]: true }
  try {
    const body = new FormData()
    body.append('file', file)
    body.append('link_url', banner.link_url || '#')
    const updated = await api(`/banners/${banner.position}/upload`, { method: 'POST', body })
    updateBanner(updated)
    savedPosition.value = banner.position
  } catch (err) {
    error.value = err.message
  } finally {
    uploading.value = { ...uploading.value, [banner.position]: false }
  }
}

function openCropper(banner, sourceUrl, sourceFile = null) {
  error.value = ''
  cropError.value = ''
  closeCropper(false)
  cropper.value = {
    banner,
    position: banner.position,
    sourceUrl,
    objectUrl: sourceFile ? sourceUrl : '',
    sourceFile,
    naturalWidth: 0,
    naturalHeight: 0,
    zoom: 1,
    offsetX: 0,
    offsetY: 0,
    dragging: false,
    dragStartX: 0,
    dragStartY: 0,
    dragStartOffsetX: 0,
    dragStartOffsetY: 0
  }
  nextTick(updateCropFrameSize)
}

function openCropperForBanner(banner) {
  if (!banner.image_url) return
  openCropper(banner, banner.image_url)
}

function closeCropper(clearError = true) {
  if (cropper.value?.objectUrl) {
    URL.revokeObjectURL(cropper.value.objectUrl)
  }
  cropper.value = null
  cropFrameSize.value = { width: 0, height: 0 }
  if (clearError) cropError.value = ''
}

function onCropImageLoad(event) {
  if (!cropper.value) return
  cropper.value.naturalWidth = event.target.naturalWidth
  cropper.value.naturalHeight = event.target.naturalHeight
  cropper.value.zoom = 1
  cropper.value.offsetX = 0
  cropper.value.offsetY = 0
  nextTick(() => {
    updateCropFrameSize()
    clampCropOffset()
  })
}

function updateCropFrameSize() {
  if (!cropFrame.value) return
  const rect = cropFrame.value.getBoundingClientRect()
  cropFrameSize.value = { width: rect.width, height: rect.height }
}

function cropGeometry() {
  const current = cropper.value
  const frame = cropFrameSize.value
  if (!current?.naturalWidth || !current?.naturalHeight || !frame.width || !frame.height) return null
  const baseScale = Math.max(frame.width / current.naturalWidth, frame.height / current.naturalHeight)
  const scale = baseScale * current.zoom
  const displayWidth = current.naturalWidth * scale
  const displayHeight = current.naturalHeight * scale
  const maxOffsetX = Math.max(0, (displayWidth - frame.width) / 2)
  const maxOffsetY = Math.max(0, (displayHeight - frame.height) / 2)
  const left = (frame.width - displayWidth) / 2 + current.offsetX
  const top = (frame.height - displayHeight) / 2 + current.offsetY
  return { frame, scale, displayWidth, displayHeight, maxOffsetX, maxOffsetY, left, top }
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function clampCropOffset() {
  const geometry = cropGeometry()
  if (!geometry || !cropper.value) return
  cropper.value.offsetX = clamp(cropper.value.offsetX, -geometry.maxOffsetX, geometry.maxOffsetX)
  cropper.value.offsetY = clamp(cropper.value.offsetY, -geometry.maxOffsetY, geometry.maxOffsetY)
}

function startCropDrag(event) {
  if (!cropper.value || !cropGeometry()) return
  cropper.value.dragging = true
  cropper.value.dragStartX = event.clientX
  cropper.value.dragStartY = event.clientY
  cropper.value.dragStartOffsetX = cropper.value.offsetX
  cropper.value.dragStartOffsetY = cropper.value.offsetY
  event.currentTarget.setPointerCapture?.(event.pointerId)
}

function moveCropDrag(event) {
  if (!cropper.value?.dragging) return
  cropper.value.offsetX = cropper.value.dragStartOffsetX + event.clientX - cropper.value.dragStartX
  cropper.value.offsetY = cropper.value.dragStartOffsetY + event.clientY - cropper.value.dragStartY
  clampCropOffset()
}

function stopCropDrag() {
  if (!cropper.value) return
  cropper.value.dragging = false
}

function canvasBlob(canvas) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) {
        resolve(blob)
        return
      }
      reject(new Error(t('banners.cropSaveError')))
    }, 'image/webp', 0.92)
  })
}

async function applyCrop() {
  const current = cropper.value
  const image = cropImage.value
  const geometry = cropGeometry()
  if (!current || !image || !geometry) return

  cropError.value = ''
  uploading.value = { ...uploading.value, [current.position]: true }
  try {
    const target = cropTarget.value
    const sourceX = Math.max(0, -geometry.left / geometry.scale)
    const sourceY = Math.max(0, -geometry.top / geometry.scale)
    const sourceWidth = Math.min(current.naturalWidth - sourceX, geometry.frame.width / geometry.scale)
    const sourceHeight = Math.min(current.naturalHeight - sourceY, geometry.frame.height / geometry.scale)
    const canvas = document.createElement('canvas')
    canvas.width = target.width
    canvas.height = target.height
    const context = canvas.getContext('2d')
    context.drawImage(image, sourceX, sourceY, sourceWidth, sourceHeight, 0, 0, target.width, target.height)
    const blob = await canvasBlob(canvas)
    const body = new FormData()
    body.append('file', blob, `${current.position}-crop.webp`)
    body.append('link_url', current.banner.link_url || '#')
    const updated = await api(`/banners/${current.position}/upload`, { method: 'POST', body })
    updateBanner(updated)
    savedPosition.value = current.position
    closeCropper()
  } catch (err) {
    cropError.value = err.message || t('banners.cropSaveError')
  } finally {
    uploading.value = { ...uploading.value, [current.position]: false }
  }
}

async function clearBanner(banner) {
  error.value = ''
  clearing.value = { ...clearing.value, [banner.position]: true }
  try {
    const updated = await api(`/banners/${banner.position}`, { method: 'DELETE' })
    updateBanner(updated)
    savedPosition.value = banner.position
  } catch (err) {
    error.value = err.message
  } finally {
    clearing.value = { ...clearing.value, [banner.position]: false }
  }
}

function openBannerImage(banner) {
  if (!banner.image_url) return
  openedBanner.value = banner
}

function closeBannerImage() {
  openedBanner.value = null
}

function closeOnEscape(event) {
  if (event.key === 'Escape') {
    if (cropper.value) {
      closeCropper()
      return
    }
    closeBannerImage()
  }
}

onMounted(async () => {
  window.addEventListener('keydown', closeOnEscape)
  window.addEventListener('resize', updateCropFrameSize)
  await load()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', closeOnEscape)
  window.removeEventListener('resize', updateCropFrameSize)
  closeCropper()
})
</script>

<template>
  <section class="section banner-editor">
    <div class="section-header banner-editor-header">
      <div>
        <h1>{{ t('nav.banners') }}</h1>
        <p class="muted">{{ t('banners.subtitle') }}</p>
      </div>
      <div class="toolbar">
        <span class="pill">{{ banners.length }}</span>
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <div class="banner-editor-grid">
      <article v-for="banner in sortedBanners" :key="banner.position" class="card banner-editor-card">
        <div class="banner-card-head">
          <div>
            <span class="banner-position-badge">{{ bannerMeta(banner.position).badge }}</span>
            <h3>{{ bannerMeta(banner.position).title }}</h3>
            <p class="muted">{{ bannerMeta(banner.position).description }}</p>
            <p class="banner-size-hint">{{ bannerMeta(banner.position).sizeHint }}</p>
          </div>
        </div>

        <button
          class="banner-preview"
          :class="{ 'side-preview': ['left', 'right'].includes(banner.position), 'is-empty': !banner.image_url }"
          type="button"
          :disabled="!banner.image_url"
          @click="openBannerImage(banner)"
        >
          <img v-if="banner.image_url" :src="banner.image_url" alt="" />
          <span v-else class="banner-preview-empty">
            <ImageIcon :size="24" />
            {{ t('banners.noImage') }}
          </span>
        </button>

        <div class="banner-form">
          <label class="field banner-field">
            <span><LinkIcon :size="15" /> {{ t('fields.linkUrl') }}</span>
            <input v-model="banner.link_url" maxlength="255" />
          </label>
        </div>

        <div class="banner-actions">
          <span v-if="savedPosition === banner.position" class="pill">{{ t('common.saved') }}</span>
          <input :id="`banner-upload-${banner.position}`" class="visually-hidden" type="file" accept="image/png,image/jpeg,image/webp,image/gif" @change="uploadToPosition(banner, $event)" />
          <label class="button" :class="{ 'is-disabled': uploading[banner.position] }" :for="`banner-upload-${banner.position}`">
            <Upload :size="16" />
            {{ uploading[banner.position] ? t('common.uploading') : t('common.upload') }}
          </label>
          <button class="button" type="button" :title="isGifBanner(banner) ? t('banners.cropGifDisabled') : t('banners.crop')" :disabled="!banner.image_url || uploading[banner.position] || isGifBanner(banner)" @click="openCropperForBanner(banner)">
            <Crop :size="16" />
            {{ t('banners.crop') }}
          </button>
          <button class="button danger" type="button" :disabled="clearing[banner.position]" @click="clearBanner(banner)">
            <Trash2 :size="16" />
            {{ clearing[banner.position] ? t('common.clearing') : t('common.clear') }}
          </button>
          <button class="button primary" type="button" :disabled="saving[banner.position]" @click="save(banner)">
            <Save :size="16" />
            {{ saving[banner.position] ? t('common.saving') : t('common.save') }}
          </button>
        </div>
      </article>
    </div>

    <div v-if="openedBanner" class="banner-image-lightbox" @click.self="closeBannerImage">
      <section class="banner-image-dialog" role="dialog" aria-modal="true">
        <div class="banner-image-head">
          <div>
            <span class="banner-position-badge">{{ bannerMeta(openedBanner.position).badge }}</span>
            <h2>{{ bannerMeta(openedBanner.position).title }}</h2>
          </div>
          <button class="icon-button" type="button" :title="t('common.close')" @click="closeBannerImage">
            <X :size="18" />
          </button>
        </div>
        <div class="banner-image-view">
          <img :src="openedBanner.image_url" :alt="bannerMeta(openedBanner.position).title" />
        </div>
      </section>
    </div>

    <div v-if="cropper" class="banner-crop-lightbox" @click.self="closeCropper">
      <section class="banner-crop-dialog" role="dialog" aria-modal="true">
        <div class="banner-image-head">
          <div>
            <span class="banner-position-badge">{{ bannerMeta(cropper.position).badge }}</span>
            <h2>{{ t('banners.cropTitle', { title: bannerMeta(cropper.position).title }) }}</h2>
          </div>
          <button class="icon-button" type="button" :title="t('common.close')" @click="closeCropper">
            <X :size="18" />
          </button>
        </div>

        <div class="banner-crop-layout">
          <div class="banner-crop-stage">
            <div
              ref="cropFrame"
              class="banner-crop-frame"
              :class="{ 'is-dragging': cropper.dragging, 'is-side': ['left', 'right'].includes(cropper.position) }"
              :style="cropFrameStyle"
              @pointerdown="startCropDrag"
              @pointermove="moveCropDrag"
              @pointerup="stopCropDrag"
              @pointercancel="stopCropDrag"
              @pointerleave="stopCropDrag"
            >
              <img
                ref="cropImage"
                class="banner-crop-image"
                :src="cropper.sourceUrl"
                :style="cropImageStyle"
                alt=""
                draggable="false"
                @load="onCropImageLoad"
              />
            </div>
          </div>

          <div class="banner-crop-tools">
            <div class="banner-crop-size">
              <span>{{ t('banners.cropSize') }}</span>
              <strong>{{ cropTarget.width }}x{{ cropTarget.height }} px</strong>
            </div>
            <label class="field banner-crop-zoom">
              <span>{{ t('banners.cropZoom') }}</span>
              <input v-model.number="cropper.zoom" type="range" min="1" max="3" step="0.01" @input="clampCropOffset" />
            </label>
            <p v-if="cropError" class="error">{{ cropError }}</p>
            <div class="banner-crop-actions">
              <button class="button" type="button" @click="closeCropper">{{ t('banners.cropCancel') }}</button>
              <button class="button primary" type="button" :disabled="uploading[cropper.position]" @click="applyCrop">
                <Check :size="16" />
                {{ uploading[cropper.position] ? t('common.uploading') : t('banners.cropSave') }}
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  </section>
</template>
