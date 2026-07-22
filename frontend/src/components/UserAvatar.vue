<script setup>
defineProps({
  color: {
    type: String,
    default: '#2563eb'
  },
  label: {
    type: String,
    default: 'Avatar'
  },
  mini: {
    type: Boolean,
    default: false
  }
})
</script>

<template>
  <div class="user-avatar" :class="{ 'is-mini': mini }" :style="{ '--avatar-color': color || '#2563eb' }" role="img" :aria-label="label">
    <img src="/assets/avatar-template.jpg" alt="" aria-hidden="true" />
  </div>
</template>
