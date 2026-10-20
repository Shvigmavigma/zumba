<script setup>
// The season champion's finish for rows and cards in lists. RankAura renders
// it for the 'season' finish, so it is laid over its host the same way (the
// host must be position: relative): the drifting title layers and a gold rim.
// The dark plate itself comes from the 'season' surface in ranks.css.
// Decorative only.
import SeasonTitleLayers from './SeasonTitleLayers.vue'

defineProps({
  /** 'lg' for big cards; rows and small cards use the default. */
  size: { type: String, default: 'md' }
})
</script>

<template>
  <span class="season-aura" aria-hidden="true">
    <SeasonTitleLayers :size="size === 'lg' ? 'card' : 'row'" />
    <span class="season-rim"></span>
  </span>
</template>

<style scoped>
/* It lies over the host's content, so the whole overlay is blended: the
   letters only ever add a little light, and what they hide stays readable. */
.season-aura {
  position: absolute;
  inset: 0;
  z-index: 2;
  overflow: hidden;
  /* Hosts that cannot pass a radius by inheritance (table rows) set the variable. */
  border-radius: var(--aura-radius, inherit);
  box-shadow: inset 0 0 26px -10px rgba(245, 200, 76, 0.55);
  mix-blend-mode: screen;
  pointer-events: none;
}
</style>
