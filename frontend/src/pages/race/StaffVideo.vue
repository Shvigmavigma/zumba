<script setup>
// Staff: attach, replace or delete the race video (finished races only).
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Trash2, Upload } from 'lucide-vue-next'

const props = defineProps({
  race: { type: Object, required: true },
  pending: { type: Boolean, default: false },
  videoFile: { type: null, default: null }
})
const emit = defineEmits(['video-file', 'upload', 'delete'])
const { t } = useI18n()
const fileInput = ref(null)

// The page clears the chosen file after upload or delete; clear the input too.
watch(() => props.videoFile, (file) => {
  if (!file && fileInput.value) fileInput.value.value = ''
})
</script>

<template>
  <form class="staff-block" @submit.prevent="emit('upload')">
    <div class="staff-block__head">
      <strong>{{ t('raceDetails.videoTitle') }}<template v-if="race.video_filename"> · {{ race.video_filename }}</template></strong>
      <span>{{ t('raceDetails.videoHint') }}</span>
    </div>
    <label class="staff-video__field">
      <span class="ui-label">{{ t('raceDetails.videoFile') }}</span>
      <input
        ref="fileInput"
        class="staff-file"
        type="file"
        accept="video/mp4,video/webm,video/quicktime,video/x-matroska,.mp4,.webm,.mov,.mkv"
        @change="emit('video-file', $event)"
      />
    </label>
    <div class="staff-actions">
      <button class="ui-btn ui-btn--primary" type="submit" :disabled="pending || !videoFile">
        <Upload :size="16" />{{ race.video_url ? t('raceDetails.replaceVideo') : t('raceDetails.uploadVideo') }}
      </button>
      <button v-if="race.video_url" class="ui-btn ui-btn--danger" type="button" :disabled="pending" @click="emit('delete')">
        <Trash2 :size="16" />{{ t('raceDetails.deleteVideo') }}
      </button>
    </div>
  </form>
</template>

<style scoped>
.staff-video__field {
  display: grid;
  gap: 8px;
}
</style>
