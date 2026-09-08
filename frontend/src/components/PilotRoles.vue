<script setup>
defineProps({
  roles: {
    type: Array,
    default: () => []
  }
})
</script>

<template>
  <span v-if="roles?.length" class="pilot-roles" aria-label="Роли пилота">
    <span
      v-for="role in roles"
      :key="role.id"
      class="pilot-role-badge"
      :class="`is-${role.display_mode || (role.image_url ? 'text_image' : 'text')}`"
      :style="{ '--pilot-role-border': role.border_color || 'var(--primary)' }"
      :title="role.name"
    >
      <span v-if="(role.display_mode || (role.image_url ? 'text_image' : 'text')) !== 'image'" class="pilot-role-text">{{ role.name }}</span>
      <span v-if="role.image_url && (role.display_mode || (role.image_url ? 'text_image' : 'text')) !== 'text'" class="pilot-role-image-wrap">
        <img class="pilot-role-image" :src="role.image_url" :alt="role.name" />
      </span>
    </span>
  </span>
</template>
