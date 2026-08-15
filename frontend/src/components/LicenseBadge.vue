<script setup>
import { computed, onMounted } from 'vue'
import { ensureLicenseSettings } from '../licenseSettings'
import { DEFAULT_LICENSE_TIERS, licenseBadgeStyle, ratingForGame, ratingLicenseTier } from '../pilotDisplay'
import { state } from '../store'

const props = defineProps({
  user: {
    type: Object,
    default: null
  },
  game: {
    type: String,
    default: 'ACC'
  },
  rating: {
    type: [Number, String],
    default: null
  },
  compact: {
    type: Boolean,
    default: true
  }
})

const badgeRating = computed(() => props.user ? ratingForGame(props.user, props.game) : props.rating)
const tier = computed(() => ratingLicenseTier(badgeRating.value, state.licenseTiers || DEFAULT_LICENSE_TIERS))

onMounted(ensureLicenseSettings)
</script>

<template>
  <span class="license-badge" :class="{ 'is-compact': compact }" :style="licenseBadgeStyle(tier)">
    {{ tier.name }}
  </span>
</template>
