<script setup>
// Staff: edit, close or delete the race, replace the track artwork and choose
// the frame the hero shows it in.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Crop, Flag, ImageUp, Pencil, Trash2 } from 'lucide-vue-next'

const props = defineProps({
  race: { type: Object, required: true },
  pending: { type: Boolean, default: false },
  trackImageFile: { type: null, default: null },
  /** The track already has artwork that can be framed. */
  hasTrackImage: { type: Boolean, default: false }
})
const emit = defineEmits(['close-race', 'delete-race', 'track-file', 'upload-track', 'frame-track'])
const { t } = useI18n()
const fileInput = ref(null)

// The page clears the chosen file after a successful upload; clear the input too.
watch(() => props.trackImageFile, (file) => {
  if (!file && fileInput.value) fileInput.value.value = ''
})
</script>

<template>
  <div class="staff-block">
    <div class="staff-block__head">
      <strong>{{ t('racePage.staff.raceTitle') }}</strong>
      <span>{{ t('racePage.staff.raceHint') }}</span>
    </div>
    <div class="staff-actions">
      <RouterLink class="ui-btn ui-btn--outline" :to="`/races/${race.id}/edit`"><Pencil :size="16" />{{ t('common.edit') }}</RouterLink>
      <button v-if="race.status !== 'finished' && race.results" class="ui-btn ui-btn--primary" type="button" :disabled="pending" @click="emit('close-race')">
        <Flag :size="16" />{{ t('raceDetails.closeRace') }}
      </button>
      <button class="ui-btn ui-btn--danger" type="button" :disabled="pending" @click="emit('delete-race')">
        <Trash2 :size="16" />{{ t('common.delete') }}
      </button>
    </div>
  </div>

  <form v-if="race.track" class="staff-block" @submit.prevent="emit('upload-track')">
    <div class="staff-block__head">
      <strong>{{ t('adminUsers.trackImages') }} · {{ race.track }}</strong>
      <span>{{ t('racePage.staff.trackHint') }}</span>
    </div>
    <input ref="fileInput" class="staff-file" type="file" accept="image/png,image/jpeg,image/webp,image/gif" :aria-label="t('adminUsers.trackImages')" @change="emit('track-file', $event)" />
    <div class="staff-actions">
      <button class="ui-btn ui-btn--primary ui-btn--sm" type="submit" :disabled="pending || !trackImageFile">
        <ImageUp :size="15" />{{ t('common.save') }}
      </button>
      <button class="ui-btn ui-btn--outline ui-btn--sm" type="button" :disabled="pending || !hasTrackImage" @click="emit('frame-track')">
        <Crop :size="15" />{{ t('raceDetails.adjustTrackImage') }}
      </button>
    </div>
  </form>
</template>
