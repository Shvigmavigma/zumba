<script setup>
import { onMounted, ref } from 'vue'
import { ChevronDown, RefreshCw } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { formatDateTime } from '../timezone'

const { t } = useI18n()
const entries = ref([])
const loading = ref(false)
const error = ref('')
const isCollapsed = ref(false)

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
