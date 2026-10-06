<script setup>
import { computed, nextTick, ref, watch, onBeforeUnmount } from 'vue'
import { Download, FileJson, FolderOpen, Trash2, Upload, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import TeamLiveryViewer from './TeamLiveryViewer.vue'

const props = defineProps({
  userId: { type: Number, required: true },
  canManage: { type: Boolean, default: false }
})

const { t } = useI18n()
const livery = ref(null)
const imagesViewerOpen = ref(false)
const uploadDialogOpen = ref(false)
const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const error = ref('')
const success = ref('')
const carFile = ref(null)
const liveryFiles = ref([])
const previewFiles = ref([])
const pendingUploadId = ref('')
const carInput = ref(null)
const folderInput = ref(null)
const imageInput = ref(null)
const dialog = ref(null)
const selectedFolderName = computed(() => {
  const path = liveryFiles.value[0]?.webkitRelativePath || ''
  return path ? path.replaceAll('\\', '/').split('/')[0] : ''
})
const loaderUrl = '/downloads/BMRL-Livery-Loader-win-x64.zip'
const CHUNKED_UPLOAD_THRESHOLD = 64 * 1024 * 1024
const UPLOAD_CHUNK_SIZE = 8 * 1024 * 1024
const UPLOAD_BATCH_MAX_BYTES = 48 * 1024 * 1024
const UPLOAD_BATCH_MAX_PARTS = 100

function formatBytes(bytes) {
  const size = Number(bytes)
  if (!Number.isFinite(size) || size <= 0) return '0 Б'
  if (size < 1024 * 1024) return `${Math.ceil(size / 1024)} КБ`
  return `${(size / (1024 * 1024)).toFixed(1)} МБ`
}

async function loadLivery() {
  if (!props.userId) return
  loading.value = true
  error.value = ''
  try {
    livery.value = await api(`/users/${props.userId}/livery`)
  } catch {
    error.value = t('profile.liveryLoadError')
  } finally {
    loading.value = false
  }
}

async function cancelPendingUpload() {
  const uploadId = pendingUploadId.value
  pendingUploadId.value = ''
  if (uploadId) {
    await api(`/users/me/livery/upload-sessions/${uploadId}`, { method: 'DELETE' }).catch(() => {})
  }
}

async function handleCarFile(event) {
  await cancelPendingUpload()
  carFile.value = event.target.files?.[0] || null
  error.value = ''
}

async function handleFolder(event) {
  await cancelPendingUpload()
  liveryFiles.value = Array.from(event.target.files || [])
  error.value = ''
  const roots = new Set(liveryFiles.value.map((file) => (file.webkitRelativePath || '').replaceAll('\\', '/').split('/')[0]).filter(Boolean))
  if (roots.size > 1) {
    error.value = t('profile.liveryOneFolder')
  }
}

async function handleImages(event) {
  await cancelPendingUpload()
  const selected = Array.from(event.target.files || [])
  if (selected.length > 4) {
    previewFiles.value = []
    event.target.value = ''
    error.value = t('teams.liveryMaximum')
    return
  }
  previewFiles.value = selected
  error.value = ''
}

function clearSelectedFiles() {
  carFile.value = null
  liveryFiles.value = []
  previewFiles.value = []
  if (carInput.value) carInput.value.value = ''
  if (folderInput.value) folderInput.value.value = ''
  if (imageInput.value) imageInput.value.value = ''
}

async function openUploadDialog() {
  error.value = ''
  success.value = ''
  clearSelectedFiles()
  uploadDialogOpen.value = true
  await nextTick()
  if (dialog.value && !dialog.value.open) dialog.value.showModal()
}

async function closeUploadDialog() {
  if (saving.value && pendingUploadId.value) return
  await cancelPendingUpload()
  uploadDialogOpen.value = false
  if (dialog.value?.open) dialog.value.close()
}

function createChunkBatches(files, chunkSize, maxBytes, maxParts) {
  const batches = []
  let batch = []
  let batchBytes = 0
  const flush = () => {
    if (batch.length) batches.push(batch)
    batch = []
    batchBytes = 0
  }

  files.forEach((file, fileIndex) => {
    for (let offset = 0; offset < file.size; offset += chunkSize) {
      const blob = file.slice(offset, Math.min(file.size, offset + chunkSize))
      if (batch.length && (batch.length >= maxParts || batchBytes + blob.size > maxBytes)) flush()
      batch.push({ fileIndex, offset, file, blob })
      batchBytes += blob.size
    }
  })
  flush()
  return batches
}

async function saveChunkedLivery() {
  const fileManifest = liveryFiles.value.map((file) => ({
    path: file.webkitRelativePath || file.name,
    size: file.size
  }))

  if (!pendingUploadId.value) pendingUploadId.value = crypto.randomUUID().replaceAll('-', '')
  const uploadId = pendingUploadId.value
  const start = new FormData()
  start.append('upload_id', uploadId)
  start.append('car_file', carFile.value, carFile.value.name)
  start.append('manifest_file', new Blob([JSON.stringify(fileManifest)], { type: 'application/json' }), 'manifest.json')
  for (const image of previewFiles.value) start.append('images', image, image.name)
  const uploadConfig = await api('/users/me/livery/upload-sessions', { method: 'POST', body: start })

  const chunkSize = Number(uploadConfig.chunk_size) || UPLOAD_CHUNK_SIZE
  const batchMaxBytes = Number(uploadConfig.batch_max_bytes) || UPLOAD_BATCH_MAX_BYTES
  const batches = createChunkBatches(liveryFiles.value, chunkSize, batchMaxBytes, UPLOAD_BATCH_MAX_PARTS)
  for (const batch of batches) {
    const form = new FormData()
    form.append('file_indexes', JSON.stringify(batch.map((part) => part.fileIndex)))
    form.append('offsets', JSON.stringify(batch.map((part) => part.offset)))
    for (const part of batch) form.append('chunks', part.blob, part.file.name)
    await api(`/users/me/livery/upload-sessions/${uploadId}/chunks`, { method: 'PUT', body: form })
  }

  const result = await api(`/users/me/livery/upload-sessions/${uploadId}/complete`, { method: 'POST' })
  pendingUploadId.value = ''
  return result
}

async function saveLivery() {
  if (!props.canManage || saving.value) return
  if (!carFile.value || !liveryFiles.value.length) {
    error.value = t('profile.liveryUploadError')
    return
  }

  const form = new FormData()
  form.append('car_file', carFile.value, carFile.value.name)
  for (const file of liveryFiles.value) {
    form.append('livery_files', file, file.webkitRelativePath || file.name)
  }
  for (const file of previewFiles.value) {
    form.append('images', file, file.name)
  }

  saving.value = true
  error.value = ''
  success.value = ''
  try {
    const totalBytes = carFile.value.size + liveryFiles.value.reduce((sum, file) => sum + file.size, 0) + previewFiles.value.reduce((sum, file) => sum + file.size, 0)
    livery.value = totalBytes > CHUNKED_UPLOAD_THRESHOLD
      ? await saveChunkedLivery()
      : await api('/users/me/livery', { method: 'PUT', body: form })
    success.value = t('profile.liverySaved')
    closeUploadDialog()
    clearSelectedFiles()
  } catch (err) {
    error.value = err.message || t('profile.liveryUploadError')
  } finally {
    saving.value = false
  }
}

async function deleteLivery() {
  if (!props.canManage || deleting.value || !livery.value || !window.confirm(t('profile.liveryDeleteConfirm'))) return
  deleting.value = true
  error.value = ''
  success.value = ''
  try {
    await api('/users/me/livery', { method: 'DELETE' })
    livery.value = null
    success.value = t('profile.liveryDeleted')
  } catch (err) {
    error.value = err.message
  } finally {
    deleting.value = false
  }
}

watch(() => props.userId, loadLivery, { immediate: true })
watch(uploadDialogOpen, async (open) => {
  await nextTick()
  if (open && dialog.value && !dialog.value.open) dialog.value.showModal()
  else if (!open && dialog.value?.open) dialog.value.close()
})
onBeforeUnmount(() => {
  if (dialog.value?.open) dialog.value.close()
})
</script>

<template>
  <section v-if="canManage || livery || loading || error" class="card pilot-livery-panel">
    <header class="pilot-livery-head">
      <div>
        <h2>{{ t('profile.liveryTitle') }}</h2>
        <p class="muted">{{ t('profile.liveryPrompt') }}</p>
      </div>
      <div v-if="canManage" class="pilot-livery-manage">
        <button class="button small primary" type="button" :disabled="saving" @click="openUploadDialog">
          <Upload :size="15" />
          {{ livery ? t('profile.liveryReplace') : t('profile.liveryUpload') }}
        </button>
        <a class="button small" :href="loaderUrl" download>
          <Download :size="15" />
          {{ t('profile.liveryLoaderDownload') }}
        </a>
      </div>
    </header>

    <p v-if="loading" class="muted" role="status">{{ t('profile.liveryLoading') }}</p>
    <p v-else-if="!livery && canManage" class="pilot-livery-empty">{{ t('profile.liveryEmpty') }}</p>

    <div v-if="livery" class="pilot-livery-details">
      <div class="pilot-livery-gallery">
        <button
          v-for="(image, index) in livery.images"
          :key="image.id"
          class="team-livery-preview"
          type="button"
          :title="image.original_filename || t('teams.liveryImageAlt', { number: index + 1 })"
          @click="imagesViewerOpen = true"
        >
          <img :src="image.image_url" :alt="image.original_filename || t('teams.liveryImageAlt', { number: index + 1 })" loading="lazy" />
        </button>
        <span v-if="!livery.images.length" class="pilot-livery-empty muted">{{ t('profile.liveryImagesEmpty') }}</span>
      </div>

      <div class="pilot-livery-summary">
        <div class="pilot-livery-name">
          <strong>{{ t('profile.liveryFolderName') }}</strong>
          <code>{{ livery.custom_skin_name }}</code>
        </div>
        <div class="pilot-livery-downloads">
          <a class="button small" :href="livery.cars_archive_url" :download="`bmrl-cars-${livery.package_id}.zip`">
            <FileJson :size="15" />
            {{ t('profile.liveryCarsArchive') }}
            <span class="muted">{{ formatBytes(livery.cars_archive_size) }}</span>
          </a>
          <a class="button small" :href="livery.liveries_archive_url" :download="`bmrl-liveries-${livery.package_id}.zip`">
            <FolderOpen :size="15" />
            {{ t('profile.liveryFolderArchive') }}
            <span class="muted">{{ formatBytes(livery.liveries_archive_size) }}</span>
          </a>
          <button v-if="canManage" class="icon-button danger-icon" type="button" :title="t('profile.liveryDelete')" :aria-label="t('profile.liveryDelete')" :disabled="deleting" @click="deleteLivery">
            <Trash2 :size="16" />
          </button>
          <a v-if="!canManage" class="button small" :href="loaderUrl" download>
            <Download :size="15" />
            {{ t('profile.liveryLoaderDownload') }}
          </a>
        </div>
      </div>
    </div>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-else-if="success" class="success pilot-livery-message" role="status">{{ success }}</p>

    <dialog ref="dialog" class="pilot-livery-dialog" :aria-labelledby="'pilot-livery-dialog-title'" @cancel.prevent="closeUploadDialog">
      <form class="pilot-livery-form" @submit.prevent="saveLivery">
        <header class="pilot-livery-dialog-head">
          <h2 id="pilot-livery-dialog-title">{{ t('profile.liveryUploadTitle') }}</h2>
          <button class="icon-button" type="button" :disabled="saving" :title="t('common.close')" :aria-label="t('common.close')" @click="closeUploadDialog">
            <X :size="18" />
          </button>
        </header>

        <label class="pilot-livery-file-field">
          <span>{{ t('profile.liveryCarsFile') }}</span>
          <input ref="carInput" type="file" accept=".json,application/json" required :disabled="saving" @change="handleCarFile" />
        </label>
        <label class="pilot-livery-file-field">
          <span>{{ t('profile.liveryFolderFiles') }}</span>
          <input ref="folderInput" type="file" webkitdirectory directory multiple required :disabled="saving" @change="handleFolder" />
          <small v-if="selectedFolderName">{{ selectedFolderName }} · {{ liveryFiles.length }}</small>
          <small>{{ t('profile.liveryFolderHint') }}</small>
        </label>
        <label class="pilot-livery-file-field">
          <span>{{ t('profile.liveryScreenshots') }}</span>
          <input ref="imageInput" type="file" accept="image/png,image/jpeg,image/webp,image/gif" multiple :disabled="saving" @change="handleImages" />
          <small>{{ t('profile.liveryImagesHint') }}</small>
          <small v-if="previewFiles.length">{{ previewFiles.length }}/4</small>
        </label>

        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <footer class="pilot-livery-dialog-actions">
          <button class="button" type="button" :disabled="saving" @click="closeUploadDialog">{{ t('profile.liveryCancel') }}</button>
          <button class="button primary" type="submit" :disabled="saving || !carFile || !liveryFiles.length">
            <Upload :size="15" />
            {{ saving ? t('profile.liverySaving') : t('profile.liverySave') }}
          </button>
        </footer>
      </form>
    </dialog>

    <TeamLiveryViewer
      :open="imagesViewerOpen"
      :team-name="livery?.custom_skin_name || ''"
      :title="t('profile.liveryTitle')"
      :images="livery?.images || []"
      @close="imagesViewerOpen = false"
    />
  </section>
</template>
