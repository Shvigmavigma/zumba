<script setup>
import { computed } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  page: { type: Number, required: true },
  pageSize: { type: Number, default: 20 },
  hasNext: { type: Boolean, default: false },
  totalItems: { type: Number, default: null },
  loadedCount: { type: Number, default: null }
})
const emit = defineEmits(['update:page'])
const { t } = useI18n()

const totalPages = computed(() => props.totalItems === null ? null : Math.max(1, Math.ceil(props.totalItems / props.pageSize)))
const canGoBack = computed(() => props.page > 1)
const canGoNext = computed(() => totalPages.value === null ? props.hasNext : props.page < totalPages.value)
const shouldShow = computed(() => props.page > 1 || props.hasNext || (totalPages.value !== null && totalPages.value > 1))
const pageLabel = computed(() => totalPages.value === null
  ? t('pagination.page', { page: props.page })
  : t('pagination.pageOf', { page: props.page, total: totalPages.value }))

function setPage(page) {
  if (page < 1 || page === props.page) return
  emit('update:page', page)
}
</script>

<template>
  <nav v-if="shouldShow" class="pagination-controls" :aria-label="t('pagination.label')">
    <button class="icon-button" type="button" :title="t('pagination.previous')" :disabled="!canGoBack" @click="setPage(page - 1)">
      <ChevronLeft :size="18" />
    </button>
    <div class="pagination-state">
      <strong>{{ pageLabel }}</strong>
      <span v-if="totalItems !== null">{{ t('pagination.items', { count: totalItems }) }}</span>
      <span v-else-if="loadedCount !== null">{{ t('pagination.loaded', { count: loadedCount }) }}</span>
    </div>
    <button class="icon-button" type="button" :title="t('pagination.next')" :disabled="!canGoNext" @click="setPage(page + 1)">
      <ChevronRight :size="18" />
    </button>
  </nav>
</template>
