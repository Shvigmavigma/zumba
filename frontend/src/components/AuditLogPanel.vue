<script setup>
import { onMounted, ref } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { formatDateTime } from '../timezone'

const { t } = useI18n()
const entries = ref([])
const loading = ref(false)
const error = ref('')

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
  <section class="admin-settings-card admin-audit-card card">
    <div class="section-header compact">
      <div>
        <h2>{{ t('adminUsers.auditTitle') }}</h2>
        <p class="muted">{{ t('adminUsers.auditHint') }}</p>
      </div>
      <button class="button small" type="button" :disabled="loading" @click="load">
        <RefreshCw :size="14" />
        {{ t('adminUsers.auditRefresh') }}
      </button>
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
