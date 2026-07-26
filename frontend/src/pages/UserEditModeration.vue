<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import UserAvatar from '../components/UserAvatar.vue'
import { formatRating, teamShortName } from '../pilotDisplay'

const { t } = useI18n()
const users = ref([])
const error = ref('')

async function load() {
  users.value = await api('/users/moderation/pending')
}

async function approve(user) {
  await api(`/users/${user.id}/approve`, { method: 'POST' })
  await load()
}

async function reject(user) {
  await api(`/users/${user.id}/reject`, { method: 'DELETE' })
  await load()
}

onMounted(async () => {
  try {
    await load()
  } catch (err) {
    error.value = err.message
  }
})
</script>

<template>
  <section class="section">
    <h1>{{ t('nav.moderation') }}</h1>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="grid">
      <article v-for="user in users" :key="user.id" class="card user-moderation-card">
        <div class="user-list-cell">
          <UserAvatar :color="user.avatar_color" :label="user.nickname || user.login" />
          <div class="user-moderation-main">
            <strong>{{ user.first_name }} {{ user.last_name }}</strong>
            <span>{{ user.nickname }}</span>
          </div>
        </div>
        <div class="user-moderation-meta">
          <p class="muted">#{{ user.pilot_number }} - RER {{ formatRating(user.rating) }} - {{ teamShortName(user.team_name) }} - {{ user.email }} - {{ t('fields.steam') }} {{ user.steam_id }}</p>
          <p v-if="user.pending_profile_changes" class="muted">{{ t('moderation.pendingProfileChanges', { changes: user.pending_profile_changes }) }}</p>
        </div>
        <div class="toolbar">
          <button class="button primary" @click="approve(user)">{{ t('common.approve') }}</button>
          <button class="button danger" @click="reject(user)">{{ t('common.reject') }}</button>
        </div>
      </article>
    </div>
  </section>
</template>
