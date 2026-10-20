// Track artwork on the race page: the image and its frame from the assets
// config, the full-size lightbox, and the two staff tools — uploading a new
// image and choosing the frame (zoom and focus point) the hero shows it in.
import { computed, ref } from 'vue'
import { api } from '../../api'
import { updateRaceAssetsCache } from '../../raceDisplay'
import { trackAsset, trackImageFrame } from './trackImage'

// Used until the hero reports the real size of its artwork area.
const DEFAULT_FRAME_BOX = { width: 1200, height: 700 }

/**
 * @param {object} options
 * @param {import('vue').Ref<object | null>} options.race
 * @param {import('vue').Ref<object>} options.raceAssets  whole assets config, replaced after every save
 * @param {import('vue').ComputedRef<object>} options.raceAssetConfig  assets of the race's game
 * @param {import('vue').Ref<boolean>} options.actionPending
 * @param {(action: () => Promise<void>) => Promise<void>} options.runAction  staff action with shared error reporting
 */
export function useTrackImage({ race, raceAssets, raceAssetConfig, actionPending, runAction }) {
  const file = ref(null)
  const lightboxOpen = ref(false)
  const framingOpen = ref(false)
  const framingError = ref('')
  const frameBox = ref(DEFAULT_FRAME_BOX)

  const image = computed(() => trackAsset(raceAssetConfig.value, 'track_images', race.value?.track, race.value?.track_id) || '')
  const frame = computed(() => trackImageFrame(raceAssetConfig.value, race.value?.track, race.value?.track_id))

  function saveAssets(config) {
    raceAssets.value = config
    updateRaceAssetsCache(config)
  }

  function openLightbox() {
    if (image.value) lightboxOpen.value = true
  }

  function closeLightbox() {
    lightboxOpen.value = false
  }

  function setFile(event) {
    file.value = event.target.files?.[0] || null
  }

  async function upload() {
    if (!race.value || !file.value) return
    await runAction(async () => {
      const body = new FormData()
      body.append('game', race.value.game)
      body.append('track', race.value.track)
      body.append('file', file.value)
      saveAssets(await api('/race-assets/track-image', { method: 'POST', body }))
      file.value = null
    })
  }

  /**
   * Opens the framing tool for a box of the given size, so staff see the
   * image in the same proportions as the hero shows it.
   * @param {{ width: number, height: number } | null | undefined} box
   */
  function openFraming(box) {
    if (!image.value) return
    if (box?.width > 0 && box?.height > 0) frameBox.value = { width: Math.round(box.width), height: Math.round(box.height) }
    framingError.value = ''
    framingOpen.value = true
  }

  function closeFraming() {
    framingOpen.value = false
    framingError.value = ''
  }

  /** @param {{ zoom: number, x: number, y: number }} next */
  async function saveFrame(next) {
    if (!race.value) return
    actionPending.value = true
    framingError.value = ''
    try {
      saveAssets(await api('/race-assets/track-image/crop', {
        method: 'PATCH',
        body: { game: race.value.game, track: race.value.track, ...next }
      }))
      closeFraming()
    } catch (err) {
      // Shown inside the framing tool: the page's own alert is behind it.
      framingError.value = err.message
    } finally {
      actionPending.value = false
    }
  }

  return {
    trackImage: image,
    trackFrame: frame,
    trackImageFile: file,
    trackLightboxOpen: lightboxOpen,
    trackFramingOpen: framingOpen,
    trackFramingError: framingError,
    trackFrameBox: frameBox,
    openTrackImage: openLightbox,
    closeTrackImage: closeLightbox,
    setTrackImage: setFile,
    uploadTrackImage: upload,
    openTrackFraming: openFraming,
    closeTrackFraming: closeFraming,
    saveTrackFrame: saveFrame
  }
}
