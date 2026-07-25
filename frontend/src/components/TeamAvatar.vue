<script setup>
defineProps({
  color: {
    type: String,
    default: '#dc2626'
  },
  label: {
    type: String,
    default: 'Team'
  },
  mini: {
    type: Boolean,
    default: false
  }
})
</script>

<template>
  <div class="team-avatar" :class="{ 'is-mini': mini }" :style="{ '--avatar-color': color || '#dc2626' }" role="img" :aria-label="label">
    <img src="/assets/team-avatar-template.jpg" alt="" aria-hidden="true" />
  </div>
</template>
