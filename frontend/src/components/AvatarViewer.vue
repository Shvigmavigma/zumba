<script setup>
import { X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps({
  open: {
    type: Boolean,
    default: false
  },
  src: {
    type: String,
    default: ''
  },
  label: {
    type: String,
    default: 'Avatar'
  },
  fallbackColor: {
    type: String,
    default: '#2563eb'
  },
  team: {
    type: Boolean,
    default: false
  }
})

defineEmits(['close'])
</script>

<template>
  <div v-if="open" class="avatar-viewer-backdrop" @click.self="$emit('close')">
    <article class="avatar-viewer card" :class="{ 'is-team': team }" :style="{ '--avatar-color': fallbackColor || '#2563eb' }">
      <div class="section-header avatar-viewer-head">
        <h2>{{ label }}</h2>
        <button class="icon-button" type="button" :title="t('common.close')" :aria-label="t('common.close')" @click="$emit('close')">
          <X :size="18" />
        </button>
      </div>
      <div class="avatar-viewer-frame">
        <img v-if="src" :src="src" :alt="label" />
        <div v-else class="avatar-viewer-empty">{{ t('avatar.empty') }}</div>
      </div>
    </article>
  </div>
</template>
