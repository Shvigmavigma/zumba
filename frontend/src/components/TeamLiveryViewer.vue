<script setup>
import { computed, watch, ref } from 'vue'
import { ChevronLeft, ChevronRight, Images, Trash2, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  open: {
    type: Boolean,
    default: false
  },
  teamName: {
    type: String,
    default: ''
  },
  images: {
    type: Array,
    default: () => []
  },
  canManage: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'delete'])
const selectedIndex = ref(0)
const currentImage = computed(() => props.images[selectedIndex.value] || null)

function selectImage(index) {
  selectedIndex.value = Math.max(0, Math.min(index, props.images.length - 1))
}

function showPrevious() {
  if (props.images.length < 2) return
  selectImage((selectedIndex.value - 1 + props.images.length) % props.images.length)
}

function showNext() {
  if (props.images.length < 2) return
  selectImage((selectedIndex.value + 1) % props.images.length)
}

function imageLabel(image, index) {
  return image?.original_filename || `${props.teamName} ${index + 1}`
}

watch(() => props.open, (isOpen) => {
  if (isOpen) selectedIndex.value = 0
})

watch(() => props.images.length, () => {
  selectedIndex.value = Math.min(selectedIndex.value, Math.max(props.images.length - 1, 0))
})
</script>

<template>
  <div v-if="open" class="team-livery-viewer-backdrop" @click.self="emit('close')">
    <article class="team-livery-viewer card" role="dialog" aria-modal="true" :aria-label="t('teams.liveryViewerTitle', { name: teamName })" tabindex="-1" @keydown.esc="emit('close')" @keydown.left="showPrevious" @keydown.right="showNext">
      <header class="team-livery-viewer-head">
        <div>
          <span class="team-livery-viewer-kicker"><Images :size="15" />{{ t('teams.liveryTitle') }} · {{ images.length }}/4</span>
          <h2>{{ teamName }}</h2>
        </div>
        <button class="icon-button" type="button" :title="t('common.close')" :aria-label="t('common.close')" @click="emit('close')">
          <X :size="18" />
        </button>
      </header>

      <div v-if="currentImage" class="team-livery-viewer-stage">
        <button v-if="images.length > 1" class="team-livery-nav is-prev" type="button" :title="t('teams.previousLivery')" :aria-label="t('teams.previousLivery')" @click="showPrevious">
          <ChevronLeft :size="22" />
        </button>
        <div class="team-livery-viewer-image-wrap">
          <img :src="currentImage.image_url" :alt="imageLabel(currentImage, selectedIndex)" />
        </div>
        <button v-if="images.length > 1" class="team-livery-nav is-next" type="button" :title="t('teams.nextLivery')" :aria-label="t('teams.nextLivery')" @click="showNext">
          <ChevronRight :size="22" />
        </button>
        <button v-if="canManage" class="team-livery-delete icon-button danger-icon" type="button" :title="t('teams.deleteLivery')" :aria-label="t('teams.deleteLivery')" @click="emit('delete', currentImage)">
          <Trash2 :size="16" />
        </button>
      </div>
      <div v-else class="team-livery-viewer-empty">
        <Images :size="34" />
        <strong>{{ t('teams.liveryEmpty') }}</strong>
        <span>{{ t('teams.liveryUploadHint') }}</span>
      </div>

      <footer v-if="images.length" class="team-livery-viewer-foot">
        <div class="team-livery-thumbnails" role="tablist" :aria-label="t('teams.liveryTitle')">
          <button v-for="(image, index) in images" :key="image.id" class="team-livery-thumbnail" :class="{ 'is-selected': index === selectedIndex }" type="button" role="tab" :aria-selected="index === selectedIndex" :aria-label="imageLabel(image, index)" @click="selectImage(index)">
            <img :src="image.image_url" alt="" />
          </button>
        </div>
        <span class="team-livery-counter">{{ selectedIndex + 1 }} / {{ images.length }}</span>
      </footer>
    </article>
  </div>
</template>
