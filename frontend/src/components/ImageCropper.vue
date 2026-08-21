<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Save, X } from 'lucide-vue-next'
import { calculateCropGeometry, clampCropOffset, cropSourceRect } from '../imageCrop'

const props = defineProps({
  sourceUrl: { type: String, required: true },
  title: { type: String, required: true },
  hint: { type: String, default: '' },
  targetWidth: { type: Number, required: true },
  targetHeight: { type: Number, required: true },
  saving: { type: Boolean, default: false },
  error: { type: String, default: '' }
})
const emit = defineEmits(['close', 'crop'])
const { t } = useI18n()
const cropFrame = ref(null)
const cropImage = ref(null)
const frameSize = ref({ width: 0, height: 0 })
const naturalSize = ref({ width: 0, height: 0 })
const zoom = ref(1)
const offset = ref({ x: 0, y: 0 })
const drag = ref(null)
const localError = ref('')
const frameStyle = computed(() => ({ aspectRatio: `${props.targetWidth} / ${props.targetHeight}` }))
const geometry = computed(() => calculateCropGeometry(
  naturalSize.value.width,
  naturalSize.value.height,
  frameSize.value.width,
  frameSize.value.height,
  zoom.value,
  offset.value.x,
  offset.value.y
))
const imageStyle = computed(() => geometry.value ? {
  width: `${geometry.value.displayWidth}px`,
  height: `${geometry.value.displayHeight}px`,
  transform: `translate(-50%, -50%) translate(${offset.value.x}px, ${offset.value.y}px)`
} : {})

function updateFrameSize() {
  const rect = cropFrame.value?.getBoundingClientRect()
  if (rect) frameSize.value = { width: rect.width, height: rect.height }
}

function clampOffset() {
  const current = geometry.value
  if (!current) return
  offset.value = {
    x: clampCropOffset(offset.value.x, current.maxOffsetX),
    y: clampCropOffset(offset.value.y, current.maxOffsetY)
  }
}

function reset() {
  naturalSize.value = { width: 0, height: 0 }
  zoom.value = 1
  offset.value = { x: 0, y: 0 }
  localError.value = ''
  nextTick(updateFrameSize)
}

function onImageLoad(event) {
  naturalSize.value = { width: event.target.naturalWidth, height: event.target.naturalHeight }
  nextTick(() => {
    updateFrameSize()
    clampOffset()
  })
}

function startDrag(event) {
  if (props.saving || !geometry.value) return
  drag.value = { x: event.clientX, y: event.clientY, offsetX: offset.value.x, offsetY: offset.value.y }
  event.currentTarget.setPointerCapture?.(event.pointerId)
}

function moveDrag(event) {
  if (!drag.value) return
  offset.value = {
    x: drag.value.offsetX + event.clientX - drag.value.x,
    y: drag.value.offsetY + event.clientY - drag.value.y
  }
  clampOffset()
}

function stopDrag() {
  drag.value = null
}

function moveWithKeyboard(event) {
  if (props.saving || !geometry.value) return
  const directions = {
    ArrowLeft: [5, 0],
    ArrowRight: [-5, 0],
    ArrowUp: [0, 5],
    ArrowDown: [0, -5]
  }
  const direction = directions[event.key]
  if (!direction) return
  event.preventDefault()
  offset.value = { x: offset.value.x + direction[0], y: offset.value.y + direction[1] }
  clampOffset()
}

function canvasBlob(canvas) {
  return new Promise((resolve, reject) => canvas.toBlob(
    (blob) => blob ? resolve(blob) : reject(new Error(t('banners.cropSaveError'))),
    'image/webp',
    0.92
  ))
}

async function applyCrop() {
  if (!geometry.value || !cropImage.value) return
  localError.value = ''
  try {
    const source = cropSourceRect(geometry.value, naturalSize.value.width, naturalSize.value.height)
    const canvas = document.createElement('canvas')
    canvas.width = props.targetWidth
    canvas.height = props.targetHeight
    const context = canvas.getContext('2d')
    if (!context) throw new Error(t('banners.cropSaveError'))
    context.drawImage(cropImage.value, source.x, source.y, source.width, source.height, 0, 0, props.targetWidth, props.targetHeight)
    emit('crop', await canvasBlob(canvas))
  } catch (err) {
    localError.value = err.message || t('banners.cropSaveError')
  }
}

function handleKeydown(event) {
  if (event.key === 'Escape' && !props.saving) emit('close')
}

watch(() => props.sourceUrl, reset, { immediate: true })
watch(zoom, clampOffset)
onMounted(() => {
  window.addEventListener('resize', updateFrameSize)
  window.addEventListener('keydown', handleKeydown)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', updateFrameSize)
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <!-- Empty/loading states are N/A: this modal exists only for a selected image; saving uses the disabled action state. -->
  <div class="banner-crop-lightbox" @click.self="!saving && emit('close')">
    <section class="banner-crop-dialog" role="dialog" aria-modal="true" :aria-label="title">
      <header class="section-header compact">
        <div>
          <h2>{{ title }}</h2>
          <p v-if="hint" class="muted">{{ hint }}</p>
        </div>
        <button class="icon-button" type="button" :disabled="saving" :title="t('common.close')" :aria-label="t('common.close')" @click="emit('close')">
          <X :size="18" />
        </button>
      </header>
      <div class="banner-crop-layout">
        <div class="banner-crop-stage">
          <div
            ref="cropFrame"
            class="banner-crop-frame logo-crop-frame"
            :class="{ 'is-dragging': drag, 'is-disabled': saving }"
            :style="frameStyle"
            :tabindex="saving ? -1 : 0"
            :aria-label="hint || title"
            @pointerdown="startDrag"
            @pointermove="moveDrag"
            @pointerup="stopDrag"
            @pointercancel="stopDrag"
            @keydown="moveWithKeyboard"
          >
            <img ref="cropImage" class="banner-crop-image" :src="sourceUrl" :style="imageStyle" alt="" @load="onImageLoad" />
          </div>
        </div>
        <aside class="banner-crop-tools">
          <div class="banner-crop-size">
            <span>{{ t('banners.cropSize') }}</span>
            <strong>{{ targetWidth }}x{{ targetHeight }} px</strong>
          </div>
          <label class="field banner-crop-zoom">
            <span>{{ t('banners.cropZoom') }}</span>
            <input v-model.number="zoom" type="range" min="1" max="3" step="0.01" :disabled="saving" />
          </label>
          <p v-if="localError || error" class="error">{{ localError || error }}</p>
          <div class="banner-crop-actions">
            <button class="button" type="button" :disabled="saving" @click="emit('close')">{{ t('banners.cropCancel') }}</button>
            <button class="button primary" type="button" :disabled="saving || !geometry" @click="applyCrop">
              <Save :size="16" />
              {{ saving ? t('common.uploading') : t('banners.cropSave') }}
            </button>
          </div>
        </aside>
      </div>
    </section>
  </div>
</template>
