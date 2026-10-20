<script setup>
// Header of the track records card: the title on the left, the whole circuit
// on the right, and a backdrop (TrackBackdrop) in the space that is left.
// Everything is keyed by track, so the backdrop, the circuit and the title
// come in again on every switch. Administrators get the artwork tools.
// A track that has a 3D layout (ui/track/trackLayouts.js) shows that instead
// of the picture, with the track's records on it (TrackStage3D); the layout
// and its component are fetched only then. If they cannot be fetched, the
// picture is shown as for any other track.
import { computed, defineAsyncComponent, shallowRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ImagePlus, Trash2 } from 'lucide-vue-next'
import TrackBackdrop from './TrackBackdrop.vue'

const TrackStage3D = defineAsyncComponent(() => import('./TrackStage3D.vue'))

const props = defineProps({
  /** Selected track's name; empty until one is picked. */
  track: { type: String, default: '' },
  image: { type: String, default: '' },
  canManage: { type: Boolean, default: false },
  /** An upload or a delete is running. */
  busy: { type: Boolean, default: false },
  /** The track's entry in the 3D layouts registry, or null when it has none. */
  layout: { type: Object, default: null },
  /** The track's finished races, for the 3D stage to read the sector times from. */
  races: { type: Array, default: () => [] },
  /** First row of the track's records table: the lap record. */
  topRow: { type: Object, default: null }
})
const emit = defineEmits(['choose-image', 'delete-image'])
const { t } = useI18n()

const layoutData = shallowRef(null)
const layoutFailed = shallowRef(false)
/** A 3D layout is on its way or on screen: the picture and its backdrop stay out. */
const wants3d = computed(() => Boolean(props.layout) && !layoutFailed.value)

watch(() => props.layout, async (entry) => {
  layoutData.value = null
  layoutFailed.value = false
  if (!entry) return
  try {
    const data = await entry.load()
    // The visitor may have picked another track while this one was loading.
    if (props.layout === entry) layoutData.value = data
  } catch {
    if (props.layout === entry) layoutFailed.value = true
  }
}, { immediate: true })
</script>

<template>
  <div class="hero" :class="{ 'has-art': image && !wants3d, 'has-3d': wants3d }">
    <TrackBackdrop v-if="!wants3d" :key="track" :track="track" />
    <div v-if="image && !wants3d" :key="`${track}|${image}`" class="hero__art">
      <img v-track-art class="hero__image ui-ink" :src="image" :alt="t('pilotsPage.tracks.mapAlt', { track })" />
    </div>
    <div class="hero__head">
      <div :key="track" class="hero__text">
        <p class="ui-eyebrow ui-eyebrow--accent">{{ t('pilotsPage.tracks.recordsTitle') }} · {{ t('tracks.topLimit') }}</p>
        <h2 class="hero__title ui-display">{{ track || t('tracks.title') }}</h2>
        <p class="hero__sub">{{ t('tracks.subtitle') }}</p>
      </div>
      <div v-if="canManage" class="hero__actions">
        <label class="ui-btn ui-btn--sm ui-btn--outline hero__upload">
          <ImagePlus :size="15" />
          {{ t('tracks.addImage') }}
          <input type="file" accept="image/png,image/jpeg,image/webp" @change="emit('choose-image', $event)" />
        </label>
        <button v-if="image" class="ui-btn ui-btn--danger ui-btn--sm" type="button" :disabled="busy" @click="emit('delete-image')">
          <Trash2 :size="15" />
          {{ t('tracks.deleteImage') }}
        </button>
      </div>
    </div>
    <template v-if="wants3d">
      <Suspense v-if="layoutData">
        <TrackStage3D :key="track" class="hero__stage" :track="track" :layout="layoutData" :races="races" :top-row="topRow" />
        <template #fallback>
          <div class="hero__stage hero__stage--wait ui-skeleton" role="status" :aria-label="t('ui.common.loading')"></div>
        </template>
      </Suspense>
      <div v-else class="hero__stage hero__stage--wait ui-skeleton" role="status" :aria-label="t('ui.common.loading')"></div>
    </template>
  </div>
</template>

<style scoped>
.hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  min-height: 240px;
  overflow: hidden;
}

.hero.has-art {
  grid-template-columns: minmax(0, 1fr) minmax(300px, 40%);
}

.hero__art {
  position: relative;
  grid-column: 2;
  grid-row: 1;
  min-width: 0;
}

.hero__art::before {
  position: absolute;
  inset: 6% 2%;
  border-radius: 50%;
  background: radial-gradient(closest-side, color-mix(in srgb, var(--bm-blue) 30%, transparent), transparent);
  content: '';
}

/* Contained, not cropped: the whole circuit stays in view. A diagram is
   drawn as ink (.ui-ink): the usual blend mode does not hold while the image
   is animated above the card's backdrop blur, and its sheet would flash as a
   black box on every switch. */
.hero__image {
  position: absolute;
  top: 14px;
  right: 20px;
  bottom: 14px;
  left: 4px;
  width: calc(100% - 24px);
  height: calc(100% - 28px);
  object-fit: contain;
  animation: hero-art-in 640ms var(--ease-ios) backwards;
}

@keyframes hero-art-in {
  from {
    opacity: 0;
    transform: translateX(26px) scale(0.94);
  }
}

.hero__head {
  position: relative;
  display: flex;
  flex-direction: column;
  grid-column: 1;
  grid-row: 1;
  justify-content: flex-end;
  gap: 14px;
  min-width: 0;
  padding: 22px;
}

.hero__text {
  display: grid;
  gap: 8px;
  animation: hero-text-in 520ms var(--ease-ios) backwards;
}

@keyframes hero-text-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
}

.hero__title {
  color: var(--c-text);
  font-size: clamp(22px, 3vw, 36px);
  overflow-wrap: anywhere;
}

.hero__sub {
  margin: 0;
  color: var(--c-text-2);
  font-size: 13.5px;
}

.hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hero__upload input {
  display: none;
}

/* ---------- A track with a 3D layout: the title, then the stage across the card ---------- */
.hero.has-3d {
  min-height: 0;
}

.hero.has-3d .hero__head {
  flex-flow: row wrap;
  align-items: flex-end;
  justify-content: space-between;
  padding-bottom: 6px;
}

.hero__stage {
  grid-column: 1;
  grid-row: 2;
  min-width: 0;
  margin: 0 22px 22px;
}

/* Holds the stage's place while its component and data arrive. */
.hero__stage--wait {
  aspect-ratio: 3 / 1;
  min-height: 220px;
  border-radius: var(--r-lg);
}

/* Phones: the circuit goes above the text. */
@media (max-width: 760px) {
  .hero {
    min-height: 0;
  }

  .hero.has-art {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: 170px auto;
  }

  .hero__art {
    grid-column: 1;
  }

  .hero.has-art .hero__head {
    grid-row: 2;
    padding-top: 6px;
  }

  .hero__stage {
    margin: 0 14px 14px;
  }

  .hero__image {
    right: 16px;
    left: 16px;
    width: calc(100% - 32px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero__image,
  .hero__text {
    animation: none;
  }
}
</style>
