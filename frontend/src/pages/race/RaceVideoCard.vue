<script setup>
// Race replay attached by the stewards after the finish.
import { useI18n } from 'vue-i18n'
import { Film, PlayCircle } from 'lucide-vue-next'
import EmptyState from '../../ui/EmptyState.vue'

defineProps({
  race: { type: Object, required: true },
  canManage: { type: Boolean, default: false }
})
const { t } = useI18n()
</script>

<template>
  <section class="video ui-card" aria-labelledby="race-video-title">
    <header class="ui-card__head">
      <div class="ui-card__title">
        <p class="ui-eyebrow ui-eyebrow--accent"><PlayCircle :size="13" />{{ t('racePage.video.eyebrow') }}</p>
        <h2 id="race-video-title">{{ t('raceDetails.videoTitle') }}</h2>
      </div>
      <span v-if="canManage && race.video_filename" class="ui-chip video__file"><Film :size="13" />{{ race.video_filename }}</span>
    </header>

    <div v-if="race.video_url" class="video__frame">
      <video controls preload="metadata" :src="race.video_url"></video>
    </div>
    <EmptyState v-else :icon="Film" compact :title="t('raceDetails.noVideo')" :text="canManage ? t('raceDetails.videoHint') : ''" />
  </section>
</template>

<style scoped>
.video__file {
  max-width: 260px;
  overflow: hidden;
  font-family: var(--font-body);
  letter-spacing: 0;
  text-overflow: ellipsis;
  text-transform: none;
}

.video__frame {
  overflow: hidden;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-lg);
  background: #000;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.35);
}

.video__frame video {
  display: block;
  width: 100%;
  max-height: 70vh;
  aspect-ratio: 16 / 9;
  background: #000;
}
</style>
