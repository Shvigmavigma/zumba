<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Image as ImageIcon, Link as LinkIcon, Save, Trash2, Upload, X } from 'lucide-vue-next'
import { api } from '../api'

const { t } = useI18n()
const banners = ref([])
const error = ref('')
const saving = ref({})
const uploading = ref({})
const clearing = ref({})
const savedPosition = ref('')
const openedBanner = ref(null)

const positionOrder = ['top', 'left', 'right', 'bottom']
const sortedBanners = computed(() => [...banners.value].sort((a, b) => positionOrder.indexOf(a.position) - positionOrder.indexOf(b.position)))

function bannerMeta(position) {
  const key = `banners.positions.${position}`
  const title = t(`${key}.title`)
  if (title === `${key}.title`) {
    return { title: position, description: '', badge: position.toUpperCase() }
  }
  return {
    title,
    description: t(`${key}.description`),
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
    closeBannerImage()
  }
}

onMounted(async () => {
  window.addEventListener('keydown', closeOnEscape)
  await load()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', closeOnEscape)
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
  </section>
</template>
