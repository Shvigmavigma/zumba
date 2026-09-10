<script setup>
import { computed, onMounted, ref } from 'vue'
import { ChevronDown, RefreshCw, Trash2 } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { state } from '../store'
import { formatDateTime } from '../timezone'

const { t } = useI18n()
const emit = defineEmits(['clear'])
const entries = ref([])
const loading = ref(false)
const error = ref('')
const isCollapsed = ref(false)
const canClear = computed(() => state.user?.is_system_admin === true)

async function load() {
  loading.value = true
  error.value = ''
  try {
    entries.value = await api('/audit?limit=100')
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

defineExpose({ load })
onMounted(load)
</script>

<template>
  <section class="admin-settings-card admin-audit-card card" :class="{ 'is-collapsed': isCollapsed }">
    <div class="section-header compact admin-zone-head">
      <div>
        <h2>{{ t('adminUsers.auditTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.auditHint') }}</p>
      </div>
      <div class="admin-audit-actions">
        <button class="button small" type="button" :disabled="loading" @click="load">
          <RefreshCw :size="14" />
          {{ t('adminUsers.auditRefresh') }}
        </button>
        <button v-if="canClear" class="button danger small" type="button" :disabled="loading" @click="emit('clear')">
          <Trash2 :size="14" />
          {{ t('adminUsers.auditClear') }}
        </button>
        <button class="icon-button admin-zone-toggle" type="button" :aria-expanded="!isCollapsed" :aria-label="isCollapsed ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" :title="isCollapsed ? t('adminUsers.expandZone') : t('adminUsers.collapseZone')" @click="isCollapsed = !isCollapsed">
          <ChevronDown :size="18" />
        </button>
      </div>
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <div v-if="!entries.length && !loading" class="empty-row">{{ t('adminUsers.auditEmpty') }}</div>
    <div v-else class="admin-audit-list">
      <article v-for="entry in entries" :key="entry.id" class="admin-audit-row">
        <div class="admin-audit-meta">
          <span class="pill">{{ entry.method }} {{ entry.status_code }}</span>
          <span class="muted">{{ formatDateTime(entry.created_at) }}</span>
        </div>
        <strong>{{ entry.action }}</strong>
        <span class="muted">{{ entry.actor_login || t('adminUsers.auditSystem') }} · {{ entry.actor_role || '—' }}</span>
      </article>
    </div>
  </section>
</template>
