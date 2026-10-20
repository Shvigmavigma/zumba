<script setup>
import { computed, nextTick, ref, watch, onBeforeUnmount } from 'vue'
import { Download, FileJson, FolderOpen, Images, Trash2, Upload, X } from 'lucide-vue-next'
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
const imagesViewerIndex = ref(0)
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

function openImages(index) {
  imagesViewerIndex.value = index
  imagesViewerOpen.value = true
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
  <section v-if="canManage || livery || loading || error" class="ui-card pilot-livery">
    <header class="ui-card__head">
      <div class="ui-card__title">
        <p class="ui-eyebrow ui-eyebrow--accent"><Images :size="14" />ACC</p>
        <h2>{{ t('profile.liveryTitle') }}</h2>
        <p v-if="canManage" class="pilot-livery__hint">{{ t('profile.liveryPrompt') }}</p>
      </div>
      <div v-if="canManage" class="pilot-livery__manage">
        <button class="ui-btn ui-btn--primary ui-btn--sm" type="button" :disabled="saving" @click="openUploadDialog">
          <Upload :size="15" />
          {{ livery ? t('profile.liveryReplace') : t('profile.liveryUpload') }}
        </button>
        <a class="ui-btn ui-btn--outline ui-btn--sm" :href="loaderUrl" download>
          <Download :size="15" />
          {{ t('profile.liveryLoaderDownload') }}
        </a>
      </div>
    </header>

    <p v-if="loading" class="pilot-livery__note" role="status">{{ t('profile.liveryLoading') }}</p>
    <p v-else-if="!livery && canManage" class="pilot-livery__note">{{ t('profile.liveryEmpty') }}</p>

    <div v-if="livery" class="pilot-livery__details">
      <div class="pilot-livery__gallery">
        <button
          v-for="(image, index) in livery.images"
          :key="image.id"
          class="pilot-livery__shot"
          type="button"
          :title="image.original_filename || t('teams.liveryImageAlt', { number: index + 1 })"
          @click="openImages(index)"
        >
          <img :src="image.image_url" :alt="image.original_filename || t('teams.liveryImageAlt', { number: index + 1 })" loading="lazy" />
        </button>
        <span v-if="!livery.images.length" class="pilot-livery__note">{{ t('profile.liveryImagesEmpty') }}</span>
      </div>

      <div class="pilot-livery__summary">
        <div class="pilot-livery__name">
          <span class="ui-eyebrow">{{ t('profile.liveryFolderName') }}</span>
          <code class="ui-mono">{{ livery.custom_skin_name }}</code>
        </div>
        <div class="pilot-livery__downloads">
          <a class="ui-btn ui-btn--outline ui-btn--sm" :href="livery.cars_archive_url" :download="`bmrl-cars-${livery.package_id}.zip`">
            <FileJson :size="15" />
            {{ t('profile.liveryCarsArchive') }}
            <span class="pilot-livery__size">{{ formatBytes(livery.cars_archive_size) }}</span>
          </a>
          <a class="ui-btn ui-btn--outline ui-btn--sm" :href="livery.liveries_archive_url" :download="`bmrl-liveries-${livery.package_id}.zip`">
            <FolderOpen :size="15" />
            {{ t('profile.liveryFolderArchive') }}
            <span class="pilot-livery__size">{{ formatBytes(livery.liveries_archive_size) }}</span>
          </a>
          <button v-if="canManage" class="ui-btn ui-btn--danger ui-btn--icon ui-btn--sm" type="button" :title="t('profile.liveryDelete')" :aria-label="t('profile.liveryDelete')" :disabled="deleting" @click="deleteLivery">
            <Trash2 :size="16" />
          </button>
          <a v-if="!canManage" class="ui-btn ui-btn--ghost ui-btn--sm" :href="loaderUrl" download>
            <Download :size="15" />
            {{ t('profile.liveryLoaderDownload') }}
          </a>
        </div>
      </div>
    </div>

    <p v-if="error && !uploadDialogOpen" class="ui-alert" role="alert">{{ error }}</p>
    <p v-else-if="success" class="ui-alert ui-alert--success" role="status">{{ success }}</p>

    <dialog ref="dialog" class="pilot-livery__dialog" aria-labelledby="pilot-livery-dialog-title" @cancel.prevent="closeUploadDialog">
      <form class="pilot-livery__form" @submit.prevent="saveLivery">
        <header class="ui-modal__head">
          <h2 id="pilot-livery-dialog-title">{{ t('profile.liveryUploadTitle') }}</h2>
          <button class="ui-btn ui-btn--ghost ui-btn--icon ui-btn--sm" type="button" :disabled="saving" :title="t('common.close')" :aria-label="t('common.close')" @click="closeUploadDialog">
            <X :size="18" />
          </button>
        </header>

        <label class="pilot-livery__field">
          <span class="ui-label"><FileJson :size="15" />{{ t('profile.liveryCarsFile') }}</span>
          <input ref="carInput" class="pilot-livery__file" type="file" accept=".json,application/json" required :disabled="saving" @change="handleCarFile" />
        </label>
        <label class="pilot-livery__field">
          <span class="ui-label"><FolderOpen :size="15" />{{ t('profile.liveryFolderFiles') }}</span>
          <input ref="folderInput" class="pilot-livery__file" type="file" webkitdirectory directory multiple required :disabled="saving" @change="handleFolder" />
          <small v-if="selectedFolderName" class="pilot-livery__picked ui-mono">{{ selectedFolderName }} · {{ liveryFiles.length }}</small>
          <small>{{ t('profile.liveryFolderHint') }}</small>
        </label>
        <label class="pilot-livery__field">
          <span class="ui-label"><Images :size="15" />{{ t('profile.liveryScreenshots') }}</span>
          <input ref="imageInput" class="pilot-livery__file" type="file" accept="image/png,image/jpeg,image/webp,image/gif" multiple :disabled="saving" @change="handleImages" />
          <small>{{ t('profile.liveryImagesHint') }}</small>
          <small v-if="previewFiles.length" class="pilot-livery__picked ui-mono">{{ previewFiles.length }}/4</small>
        </label>

        <p v-if="error" class="ui-alert" role="alert">{{ error }}</p>
        <footer class="pilot-livery__actions">
          <button class="ui-btn ui-btn--ghost" type="button" :disabled="saving" @click="closeUploadDialog">{{ t('profile.liveryCancel') }}</button>
          <button class="ui-btn ui-btn--primary" type="submit" :disabled="saving || !carFile || !liveryFiles.length">
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
      :start-index="imagesViewerIndex"
      @close="imagesViewerOpen = false"
    />
  </section>
</template>

<style scoped>
.pilot-livery {
  display: grid;
  gap: 16px;
}

.pilot-livery__hint,
.pilot-livery__note {
  margin: 0;
  color: var(--c-text-3);
  font-size: 13px;
}

.pilot-livery__manage,
.pilot-livery__downloads {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.pilot-livery__details {
  display: grid;
  gap: 14px;
}

.pilot-livery__gallery {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 220px), 1fr));
  gap: 10px;
}

.pilot-livery__shot {
  aspect-ratio: 16 / 9;
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  background: var(--c-sunken);
  cursor: zoom-in;
  transition: border-color var(--dur-1), transform var(--dur-2) var(--ease-ios);
}

.pilot-livery__shot:hover {
  border-color: var(--c-blue-line);
  transform: translateY(-2px);
}

.pilot-livery__shot img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.pilot-livery__summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px 20px;
  padding: 12px 14px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  background: var(--c-sunken);
}

.pilot-livery__name {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.pilot-livery__name code {
  color: var(--c-text);
  font-size: 14px;
  overflow-wrap: anywhere;
}

.pilot-livery__size {
  color: var(--c-text-3);
  font-weight: 500;
}

.pilot-livery__dialog {
  width: min(560px, calc(100% - 32px));
  max-height: calc(100dvh - 40px);
  padding: clamp(18px, 2.4vw, 26px);
  overflow-y: auto;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-xl);
  background: var(--c-surface-solid);
  box-shadow: var(--shadow-2);
  color: var(--c-text);
}

.pilot-livery__dialog::backdrop {
  background: var(--c-overlay);
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
}

.pilot-livery__form {
  display: grid;
  gap: 16px;
}

.pilot-livery__field {
  display: grid;
  gap: 6px;
}

.pilot-livery__field .ui-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.pilot-livery__field small {
  color: var(--c-text-3);
  font-size: 12.5px;
  line-height: 1.4;
}

.pilot-livery__field .pilot-livery__picked {
  color: var(--c-accent-text);
}

.pilot-livery__file {
  width: 100%;
  padding: 10px 12px;
  border: 1px dashed var(--c-line-strong);
  border-radius: var(--r-sm);
  background: var(--c-sunken);
  color: var(--c-text-2);
  font: inherit;
  font-size: 13.5px;
}

.pilot-livery__file::file-selector-button {
  margin-right: 12px;
  padding: 7px 12px;
  border: 0;
  border-radius: 999px;
  background: var(--bm-blue);
  color: #fff;
  cursor: pointer;
  font: inherit;
  font-weight: 600;
}

.pilot-livery__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

@media (prefers-reduced-motion: reduce) {
  .pilot-livery__shot {
    transition: none;
  }
}
</style>
