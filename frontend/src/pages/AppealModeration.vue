<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Trash2 } from 'lucide-vue-next'
import { api } from '../api'
import PenaltyDetailsModal from '../components/PenaltyDetailsModal.vue'
import { statusLabel } from '../i18nLabels'
import { state } from '../store'

const { t } = useI18n()
const appeals = ref([])
const error = ref('')
const reasons = ref({})
const selectedPenalty = ref(null)
const penaltyError = ref('')
const penaltyLoading = ref(false)
const isAdmin = computed(() => state.user?.role === 'admin')

async function load() {
  try {
    appeals.value = await api('/appeals')
  } catch (err) {
    error.value = err.message
  }
}

async function moderate(appeal, status) {
  if (appeal.status !== 'pending') return
  await api(`/appeals/${appeal.id}/moderate`, {
    method: 'PATCH',
    body: {
      status,
      rejection_reason: reasons.value[appeal.id]
    }
  })
  await load()
}

async function deleteAppeal(appeal) {
  if (!window.confirm(t('appeals.confirmDelete'))) return
  try {
    await api(`/appeals/${appeal.id}`, { method: 'DELETE' })
    appeals.value = appeals.value.filter((item) => item.id !== appeal.id)
  } catch (err) {
    error.value = err.message
  }
}

function isPending(appeal) {
  return appeal.status === 'pending'
}

async function openPenalty(appeal) {
  selectedPenalty.value = null
  penaltyError.value = ''
  penaltyLoading.value = true
  try {
    selectedPenalty.value = await api(`/penalties/${appeal.penalty_id}`)
  } catch (err) {
    penaltyError.value = err.message
  } finally {
    penaltyLoading.value = false
  }
}

function closePenalty() {
  selectedPenalty.value = null
  penaltyError.value = ''
  penaltyLoading.value = false
}

onMounted(load)
</script>

<template>
  <section class="section appeal-moderation-page">
    <div class="section-header">
      <h1>{{ t('nav.appeals') }}</h1>
      <span class="pill">{{ appeals.length }}</span>
    </div>
    <p v-if="error" class="error">{{ error }}</p>

    <div class="appeal-list">
      <article v-for="appeal in appeals" :key="appeal.id" class="card appeal-card" :class="`appeal-${appeal.status}`">
        <div class="appeal-card-main">
          <div class="section-header appeal-card-head">
            <div>
              <strong>#{{ appeal.id }} - {{ statusLabel(t, appeal.status) }}</strong>
              <p class="muted appeal-meta">
                <span>{{ t('fields.race') }} #{{ appeal.race_id }}</span>
                <button class="inline-link" type="button" @click="openPenalty(appeal)">
                  {{ t('raceDetails.penalty') }} #{{ appeal.penalty_id }}
                </button>
              </p>
            </div>
            <a class="button small" :href="appeal.proof_link" target="_blank" rel="noreferrer">{{ t('appeals.proof') }}</a>
          </div>
          <p>{{ appeal.description }}</p>
          <p v-if="appeal.rejection_reason" class="muted">{{ appeal.rejection_reason }}</p>
        </div>

        <div class="appeal-card-actions">
          <template v-if="isPending(appeal)">
            <label class="field">
              <span>{{ t('fields.rejectionReason') }}</span>
              <input v-model="reasons[appeal.id]" />
            </label>
            <div class="appeal-action-buttons">
              <button class="button primary" type="button" @click="moderate(appeal, 'approved')">{{ t('common.approve') }}</button>
              <button class="button danger" type="button" @click="moderate(appeal, 'rejected')">{{ t('common.reject') }}</button>
            </div>
          </template>
          <span v-else class="status-badge" :class="`status-${appeal.status}`">{{ statusLabel(t, appeal.status) }}</span>
          <button
            v-if="isAdmin"
            class="icon-button danger-icon"
            type="button"
            :title="t('common.delete')"
            :aria-label="t('common.delete')"
            @click="deleteAppeal(appeal)"
          >
            <Trash2 :size="16" />
          </button>
        </div>
      </article>

      <div v-if="!appeals.length" class="empty-row">{{ t('appeals.empty') }}</div>
    </div>

    <PenaltyDetailsModal
      v-if="selectedPenalty || penaltyLoading || penaltyError"
      :penalty="selectedPenalty"
      :loading="penaltyLoading"
      :error="penaltyError"
      @close="closePenalty"
    />
  </section>
</template>
