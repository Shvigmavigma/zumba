<script setup>
import { brandingSettings } from '../brandingSettings'

defineProps({
  color: {
    type: String,
    default: '#2563eb'
  },
  label: {
    type: String,
    default: 'Avatar'
  },
  src: {
    type: String,
    default: ''
  },
  mini: {
    type: Boolean,
    default: false
  }
})
</script>

<template>
  <div class="user-avatar" :class="{ 'is-mini': mini, 'has-upload': !!src }" :style="{ '--avatar-color': color || '#2563eb' }" role="img" :aria-label="label">
    <img :src="src || brandingSettings.default_avatar_url" alt="" aria-hidden="true" />
  </div>
</template>
