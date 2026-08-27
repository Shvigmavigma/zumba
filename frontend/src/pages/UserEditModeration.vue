<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Trash2 } from 'lucide-vue-next'
import { api } from '../api'
import LicenseBadge from '../components/LicenseBadge.vue'
import PaginationControls from '../components/PaginationControls.vue'
import UserAvatar from '../components/UserAvatar.vue'
import { formatPilotNumber, formatRating, teamShortName } from '../pilotDisplay'
import { state } from '../store'

const { t } = useI18n()
const users = ref([])
const error = ref('')
const page = ref(1)
const pageSize = 8
const totalPages = computed(() => Math.max(1, Math.ceil(users.value.length / pageSize)))
const pagedUsers = computed(() => users.value.slice((page.value - 1) * pageSize, page.value * pageSize))
const isAdmin = computed(() => state.user?.role === 'admin')

function visiblePendingChanges(value) {
  if (!value || typeof value !== 'object') return String(value || '')
  return JSON.stringify(Object.fromEntries(Object.entries(value).filter(([key]) => key !== 'email')))
}

async function load() {
  users.value = await api('/users/moderation/pending')
}

async function approve(user) {
  try {
    await api(`/users/${user.id}/approve`, { method: 'POST' })
    users.value = users.value.filter((item) => item.id !== user.id)
  } catch (err) {
    error.value = err.message
  }
}

async function reject(user) {
  try {
    await api(`/users/${user.id}/reject`, { method: 'DELETE' })
    users.value = users.value.filter((item) => item.id !== user.id)
  } catch (err) {
    error.value = err.message
  }
}

async function deleteRequest(user) {
  if (!window.confirm(t('moderation.confirmDelete'))) return
  try {
    await api(`/users/${user.id}/moderation`, { method: 'DELETE' })
    users.value = users.value.filter((item) => item.id !== user.id)
  } catch (err) {
    error.value = err.message
  }
}

onMounted(async () => {
  try {
    await load()
  } catch (err) {
    error.value = err.message
  }
})

watch(users, () => {
  if (page.value > totalPages.value) {
    page.value = totalPages.value
  }
})
</script>

<template>
  <section class="section">
    <h1>{{ t('nav.moderation') }}</h1>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="grid">
      <article v-for="user in pagedUsers" :key="user.id" class="card user-moderation-card">
        <div class="user-list-cell">
          <UserAvatar :src="user.avatar_url" :color="user.avatar_color" :label="user.nickname || user.login" />
          <div class="user-moderation-main">
            <span class="user-name-line">
              <strong>{{ user.first_name }} {{ user.last_name }}</strong>
              <LicenseBadge :user="user" />
            </span>
            <span>{{ user.nickname }}</span>
          </div>
        </div>
        <div class="user-moderation-meta">
          <p class="muted">#{{ formatPilotNumber(user.pilot_number) }} - RER {{ formatRating(user.rating) }} - {{ teamShortName(user.team_name, user.team_abbreviation) }} - {{ t('fields.steam') }} {{ user.steam_id }}</p>
          <p v-if="user.pending_profile_changes" class="muted">{{ t('moderation.pendingProfileChanges', { changes: visiblePendingChanges(user.pending_profile_changes) }) }}</p>
        </div>
        <div class="toolbar">
          <button class="button primary" @click="approve(user)">{{ t('common.approve') }}</button>
          <button class="button danger" @click="reject(user)">{{ t('common.reject') }}</button>
          <button
            v-if="isAdmin"
            class="icon-button danger-icon"
            type="button"
            :title="t('moderation.deleteRequest')"
            :aria-label="t('moderation.deleteRequest')"
            @click="deleteRequest(user)"
          >
            <Trash2 :size="16" />
          </button>
        </div>
      </article>
    </div>
    <PaginationControls v-model:page="page" :page-size="pageSize" :total-items="users.length" />
  </section>
</template>
