<script setup>
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
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

const { t } = useI18n()
const isRerExcluded = computed(() => Boolean(props.user?.exclude_from_rer))
const badgeRating = computed(() => props.user ? ratingForGame(props.user, props.game) : props.rating)
const tier = computed(() => ratingLicenseTier(badgeRating.value, state.licenseTiers || DEFAULT_LICENSE_TIERS))

onMounted(ensureLicenseSettings)
</script>

<template>
  <span class="license-badge" :class="{ 'is-compact': compact, 'is-rer-excluded': isRerExcluded }" :style="isRerExcluded ? undefined : licenseBadgeStyle(tier)">
    {{ isRerExcluded ? t('common.rerExcluded') : tier.name }}
  </span>
</template>
