<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'

const appeals = ref([])
const error = ref('')
const reasons = ref({})

async function load() {
  try {
    appeals.value = await api('/appeals')
  } catch (err) {
    error.value = err.message
  }
}

async function moderate(appeal, status) {
  await api(`/appeals/${appeal.id}/moderate`, { method: 'PATCH', body: { status, rejection_reason: reasons.value[appeal.id] } })
  await load()
}

onMounted(load)
</script>

<template>
  <section class="section">
    <h1>AppealModeration</h1>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="grid">
      <article v-for="appeal in appeals" :key="appeal.id" class="card">
        <div class="section-header">
          <strong>#{{ appeal.id }} · {{ appeal.status }}</strong>
          <a :href="appeal.proof_link" target="_blank" rel="noreferrer">Proof</a>
        </div>
        <p>{{ appeal.description }}</p>
        <label class="field"><span>Rejection reason</span><input v-model="reasons[appeal.id]" /></label>
        <div class="toolbar">
          <button class="button primary" @click="moderate(appeal, 'approved')">Approve</button>
          <button class="button danger" @click="moderate(appeal, 'rejected')">Reject</button>
        </div>
      </article>
    </div>
  </section>
</template>

