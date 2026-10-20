<script setup>
// The team's livery screenshots (up to four). Whoever manages the team gets
// them with the team and can add or delete; everybody else sees only the
// count and loads the images on demand. Every change reports the updated team
// back to the page.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Download, Images, LoaderCircle, Upload } from 'lucide-vue-next'
import { api } from '../../api'
import TeamLiveryViewer from '../../components/TeamLiveryViewer.vue'
import { readTeamLiveryCache, writeTeamLiveryCache } from './teamLiveryCache'

const MAX_LIVERIES = 4

const props = defineProps({
  team: { type: Object, required: true },
  canManage: { type: Boolean, default: false }
})
const emit = defineEmits(['update:team', 'error', 'saved'])
const { t } = useI18n()

const viewerOpen = ref(false)
const viewerIndex = ref(0)
const saving = ref(false)
const loading = ref(false)
const loaded = ref(false)

const images = computed(() => props.team.livery_images || [])
const count = computed(() => Number(props.team.livery_image_count ?? images.value.length))
const canAdd = computed(() => props.canManage && images.value.length < MAX_LIVERIES)
/** A visitor has not asked for the images yet. */
const deferred = computed(() => !props.canManage && count.value > 0 && !images.value.length && !loaded.value)
const inputId = computed(() => `team-livery-upload-${props.team.id}`)

function imageLabel(image, index) {
  return image.original_filename || t('teams.liveryImageAlt', { number: index + 1 })
}

function openViewer(index = 0) {
  viewerIndex.value = index
  viewerOpen.value = true
}

async function loadImages() {
  if (!deferred.value || loading.value) return
  const teamId = props.team.id
  loading.value = true
  emit('error', '')
  try {
    const cached = await readTeamLiveryCache(teamId)
    const list = cached && cached.length === count.value ? cached : await api(`/teams/${teamId}/liveries`)
    const loadedImages = Array.isArray(list) ? list : []
    // The pilot may have opened another team while this one was loading.
    if (props.team.id !== teamId) return
    emit('update:team', { ...props.team, livery_images: loadedImages, livery_image_count: loadedImages.length })
    await writeTeamLiveryCache(teamId, loadedImages)
    loaded.value = true
    if (loadedImages.length) openViewer()
  } catch (err) {
    emit('error', err.message)
  } finally {
    loading.value = false
  }
}

async function upload(event) {
  const input = event.target
  const files = Array.from(input.files || [])
  if (!files.length) return
  if (files.length > MAX_LIVERIES - images.value.length) {
    emit('error', t('teams.liveryMaximum'))
    input.value = ''
    return
  }
  saving.value = true
  emit('error', '')
  try {
    let updated = props.team
    for (const file of files) {
      const payload = new FormData()
      payload.append('file', file)
      updated = await api(`/teams/${props.team.id}/liveries`, { method: 'POST', body: payload })
      emit('update:team', updated)
    }
    await writeTeamLiveryCache(updated.id, updated.livery_images || [])
    emit('saved')
  } catch (err) {
    emit('error', err.message)
  } finally {
    saving.value = false
    input.value = ''
  }
}

async function remove(image) {
  if (!image || !window.confirm(t('teams.deleteLiveryConfirm'))) return
  saving.value = true
  emit('error', '')
  try {
    const updated = await api(`/teams/${props.team.id}/liveries/${image.id}`, { method: 'DELETE' })
    emit('update:team', updated)
    await writeTeamLiveryCache(updated.id, updated.livery_images || [])
    emit('saved')
    if (!(updated.livery_images || []).length) viewerOpen.value = false
  } catch (err) {
    emit('error', err.message)
  } finally {
    saving.value = false
  }
}

watch(() => props.team.id, () => {
  viewerOpen.value = false
  loaded.value = false
})
</script>

<template>
  <section class="liveries ui-card" aria-labelledby="team-liveries-title">
    <header class="liveries__head">
      <div class="liveries__title">
        <p class="ui-eyebrow ui-eyebrow--accent"><Images :size="14" />{{ t('teams.liveryCount', { count }) }}</p>
        <h3 id="team-liveries-title" class="ui-title liveries__h">{{ t('teams.liveryTitle') }}</h3>
      </div>
      <div class="liveries__actions">
        <button v-if="images.length" class="ui-btn ui-btn--outline ui-btn--sm" type="button" @click="openViewer()">
          <Images :size="15" />{{ t('teams.openLiveries') }}
        </button>
        <button v-else-if="deferred" class="ui-btn ui-btn--primary ui-btn--sm" type="button" :disabled="loading" @click="loadImages">
          <LoaderCircle v-if="loading" class="liveries__spin" :size="15" />
          <Download v-else :size="15" />
          {{ loading ? t('teams.loadingLivery') : t('teams.loadLivery') }}
        </button>
        <label v-if="canAdd" class="ui-btn ui-btn--primary ui-btn--sm" :class="{ 'is-disabled': saving }" :for="inputId">
          <LoaderCircle v-if="saving" class="liveries__spin" :size="15" />
          <Upload v-else :size="15" />
          {{ images.length ? t('teams.addLivery') : t('teams.uploadLivery') }}
        </label>
        <input :id="inputId" class="ui-sr" type="file" accept="image/png,image/jpeg,image/webp,image/gif" multiple :disabled="saving || !canAdd" @change="upload" />
      </div>
    </header>

    <ul v-if="images.length" class="liveries__strip">
      <li v-for="(image, index) in images" :key="image.id">
        <button class="liveries__shot" type="button" :title="imageLabel(image, index)" @click="openViewer(index)">
          <img :src="image.image_url" :alt="imageLabel(image, index)" loading="lazy" />
        </button>
      </li>
    </ul>
    <p v-else class="liveries__note">{{ deferred ? t('teams.liveryDeferred') : t('teams.liveryEmpty') }}</p>
    <p v-if="canManage" class="liveries__note">{{ canAdd ? t('teams.liveryUploadHint') : t('teams.liveryMaximum') }}</p>

    <TeamLiveryViewer
      :open="viewerOpen"
      :team-name="team.name"
      :images="images"
      :can-manage="canManage"
      :start-index="viewerIndex"
      @close="viewerOpen = false"
      @delete="remove"
    />
  </section>
</template>

<style scoped>
.liveries {
  display: grid;
  gap: 14px;
}

.liveries__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px 16px;
}

.liveries__title {
  display: grid;
  gap: 6px;
}

.liveries__h {
  margin: 0;
}

.liveries__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.liveries__actions .is-disabled {
  cursor: progress;
  opacity: 0.6;
  pointer-events: none;
}

.liveries__strip {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 220px), 1fr));
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.liveries__shot {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  background: var(--c-sunken);
  cursor: zoom-in;
  transition: border-color var(--dur-1), transform var(--dur-2) var(--ease-ios);
}

.liveries__shot:hover {
  border-color: var(--c-blue-line);
  transform: translateY(-2px);
}

.liveries__shot img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.liveries__note {
  margin: 0;
  color: var(--c-text-3);
  font-size: 13px;
}

.liveries__spin {
  animation: liveries-spin 900ms linear infinite;
}

@keyframes liveries-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .liveries__shot {
    transition: none;
  }

  .liveries__spin {
    animation: none;
  }
}
</style>
