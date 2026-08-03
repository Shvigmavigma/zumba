<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Bell, Check, Crown, LogOut, Plus, Save, Search, Send, Trash2, Upload, UserCheck, UserMinus, Users, X, XCircle } from 'lucide-vue-next'
import { api } from '../api'
import AvatarViewer from '../components/AvatarViewer.vue'
import PaginationControls from '../components/PaginationControls.vue'
import TeamAvatar from '../components/TeamAvatar.vue'
import UserAvatar from '../components/UserAvatar.vue'
import { filterPilots, formatRating, sortPilots, teamShortName } from '../pilotDisplay'
import { state } from '../store'

const { t } = useI18n()

const teams = ref([])
const selectedTeam = ref(null)
const createRequests = ref([])
const config = ref({ member_limit: 5, my_create_request_status: null, pending_creation_request_count: 0 })
const search = ref('')
const error = ref('')
const saved = ref(false)
const loading = ref(false)
const busyTeams = ref({})
const createOpen = ref(false)
const createSaving = ref(false)
const editSaving = ref(false)
const transferSaving = ref(false)
const deleteSaving = ref(false)
const teamAvatarFile = ref(null)
const teamAvatarSaving = ref(false)
const teamAvatarViewerOpen = ref(false)
const busyApplications = ref({})
const busyMembers = ref({})
const busyCreateRequests = ref({})
const memberSearch = ref('')
const memberSort = ref('rating_desc')
const teamPage = ref(1)
const teamPageSize = 12
const memberPage = ref(1)
const memberPageSize = 10
const createForm = ref({
  name: '',
  description: '',
  avatar_color: '#dc2626'
})
const editForm = ref({
  name: '',
  description: '',
  avatar_color: '#dc2626'
})

const canModerateTeams = computed(() => ['admin', 'moder'].includes(state.user?.role))
const canCreateTeam = computed(() => state.user?.status === 'active' && !state.user?.team_id && config.value.my_create_request_status !== 'pending')
const selectedIsOwner = computed(() => Boolean(selectedTeam.value?.is_owner))
const selectedCanManage = computed(() => Boolean(selectedTeam.value?.can_manage))
const transferOwnerId = ref('')
const transferCandidates = computed(() => selectedTeam.value?.members?.filter((member) => member.id !== selectedTeam.value.owner_id) || [])
const teamTotalPages = computed(() => Math.max(1, Math.ceil(teams.value.length / teamPageSize)))
const pagedTeams = computed(() => teams.value.slice((teamPage.value - 1) * teamPageSize, teamPage.value * teamPageSize))
const visibleTeamMembers = computed(() => sortPilots(filterPilots(selectedTeam.value?.members || [], memberSearch.value), memberSort.value))
const memberTotalPages = computed(() => Math.max(1, Math.ceil(visibleTeamMembers.value.length / memberPageSize)))
const pagedTeamMembers = computed(() => visibleTeamMembers.value.slice((memberPage.value - 1) * memberPageSize, memberPage.value * memberPageSize))

function updateStoredUser(patch) {
  if (!state.user) return
  state.user = { ...state.user, ...patch }
  localStorage.setItem('user', JSON.stringify(state.user))
}

function setBusy(teamId, value) {
  busyTeams.value = { ...busyTeams.value, [teamId]: value }
}

function setApplicationBusy(applicationId, value) {
  busyApplications.value = { ...busyApplications.value, [applicationId]: value }
}

function setMemberBusy(userId, value) {
  busyMembers.value = { ...busyMembers.value, [userId]: value }
}

function setCreateRequestBusy(requestId, value) {
  busyCreateRequests.value = { ...busyCreateRequests.value, [requestId]: value }
}

function resetCreateForm() {
  createForm.value = {
    name: '',
    description: '',
    avatar_color: '#dc2626'
  }
}

function fillEditForm(team) {
  editForm.value = {
    name: team?.name || '',
    description: team?.description || '',
    avatar_color: team?.avatar_color || '#dc2626'
  }
  transferOwnerId.value = team?.members?.find((member) => member.id !== team.owner_id)?.id || ''
}

function setTeamAvatarFile(event) {
  teamAvatarFile.value = event.target.files?.[0] || null
}

function memberTitle(member) {
  return member.nickname || member.login
}

function memberTeamName(member) {
  return member.team_name || selectedTeam.value?.name || ''
}

function ownerLabel(team) {
  return team.owner_nickname || team.owner_login || t('teams.noOwner')
}

function gamesLabel(games) {
  return games?.length ? games.map((game) => t(`games.${game}`)).join(', ') : t('common.none')
}

function requestStatusLabel(status) {
  if (!status) return ''
  return t(`teams.applicationStatuses.${status}`)
}

function pendingApplicationsTitle(team) {
  return t('teams.pendingApplicationsNotice', { count: team.pending_application_count || 0 })
}

function teamFillPercent(team) {
  if (!team?.member_limit) return 0
  return Math.min(100, Math.round((team.member_count / team.member_limit) * 100))
}

async function syncCurrentUser() {
  if (!state.user) return
  try {
    const user = await api('/auth/me')
    updateStoredUser(user)
  } catch (err) {
    if (state.user) throw err
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    await syncCurrentUser()
    const suffix = search.value.trim() ? `?search=${encodeURIComponent(search.value.trim())}` : ''
    const [loadedTeams, loadedConfig] = await Promise.all([
      api(`/teams${suffix}`),
      api('/teams/config')
    ])
    teams.value = loadedTeams
    config.value = loadedConfig
    createRequests.value = canModerateTeams.value ? await api('/teams/create-requests') : []

    const selectedId = selectedTeam.value?.id
    if (selectedId && loadedTeams.some((team) => team.id === selectedId)) {
      selectedTeam.value = await api(`/teams/${selectedId}`)
      fillEditForm(selectedTeam.value)
    } else if (selectedId) {
      selectedTeam.value = null
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function openTeam(team) {
  setBusy(team.id, true)
  error.value = ''
  try {
    selectedTeam.value = await api(`/teams/${team.id}`)
    memberPage.value = 1
    fillEditForm(selectedTeam.value)
  } catch (err) {
    error.value = err.message
  } finally {
    setBusy(team.id, false)
  }
}

async function createTeam() {
  createSaving.value = true
  error.value = ''
  saved.value = false
  try {
    const createdRequest = await api('/teams', {
      method: 'POST',
      body: {
        name: createForm.value.name.trim(),
        description: createForm.value.description.trim(),
        avatar_color: createForm.value.avatar_color
      }
    })
    config.value = { ...config.value, my_create_request_status: createdRequest.status }
    createOpen.value = false
    resetCreateForm()
    saved.value = true
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    createSaving.value = false
  }
}

async function approveCreateRequest(requestItem) {
  setCreateRequestBusy(requestItem.id, true)
  error.value = ''
  saved.value = false
  try {
    await api(`/teams/create-requests/${requestItem.id}/approve`, { method: 'POST' })
    saved.value = true
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    setCreateRequestBusy(requestItem.id, false)
  }
}

async function rejectCreateRequest(requestItem) {
  setCreateRequestBusy(requestItem.id, true)
  error.value = ''
  saved.value = false
  try {
    await api(`/teams/create-requests/${requestItem.id}/reject`, { method: 'POST' })
    saved.value = true
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    setCreateRequestBusy(requestItem.id, false)
  }
}

async function saveTeam() {
  if (!selectedTeam.value) return
  editSaving.value = true
  error.value = ''
  saved.value = false
  try {
    selectedTeam.value = await api(`/teams/${selectedTeam.value.id}`, {
      method: 'PATCH',
      body: {
        name: editForm.value.name.trim(),
        description: editForm.value.description.trim(),
        avatar_color: editForm.value.avatar_color
      }
    })
    fillEditForm(selectedTeam.value)
    saved.value = true
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    editSaving.value = false
  }
}

async function uploadTeamAvatar() {
  if (!selectedTeam.value || !teamAvatarFile.value) return
  teamAvatarSaving.value = true
  error.value = ''
  saved.value = false
  try {
    const payload = new FormData()
    payload.append('file', teamAvatarFile.value)
    selectedTeam.value = await api(`/teams/${selectedTeam.value.id}/avatar`, {
      method: 'POST',
      body: payload
    })
    fillEditForm(selectedTeam.value)
    teamAvatarFile.value = null
    saved.value = true
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    teamAvatarSaving.value = false
  }
}

async function requestJoin(team) {
  setBusy(team.id, true)
  error.value = ''
  saved.value = false
  try {
    selectedTeam.value = await api(`/teams/${team.id}/join`, { method: 'POST' })
    fillEditForm(selectedTeam.value)
    saved.value = true
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    setBusy(team.id, false)
  }
}

async function leaveTeam() {
  if (!selectedTeam.value || !window.confirm(t('teams.leaveConfirm', { name: selectedTeam.value.name }))) return
  const teamId = selectedTeam.value.id
  setBusy(teamId, true)
  error.value = ''
  saved.value = false
  try {
    await api(`/teams/${teamId}/leave`, { method: 'DELETE' })
    if (state.user?.team_id === teamId) {
      updateStoredUser({ team_id: null })
    }
    selectedTeam.value = null
    saved.value = true
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    setBusy(teamId, false)
  }
}

async function transferOwnership() {
  if (!selectedTeam.value || !transferOwnerId.value) return
  const teamId = selectedTeam.value.id
  transferSaving.value = true
  error.value = ''
  saved.value = false
  try {
    selectedTeam.value = await api(`/teams/${teamId}/owner`, {
      method: 'PATCH',
      body: { new_owner_id: Number(transferOwnerId.value) }
    })
    fillEditForm(selectedTeam.value)
    saved.value = true
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    transferSaving.value = false
  }
}

async function deleteTeam() {
  if (!selectedTeam.value || !window.confirm(t('teams.deleteConfirm', { name: selectedTeam.value.name }))) return
  const teamId = selectedTeam.value.id
  deleteSaving.value = true
  setBusy(teamId, true)
  error.value = ''
  saved.value = false
  try {
    await api(`/teams/${teamId}`, { method: 'DELETE' })
    if (state.user?.team_id === teamId) {
      updateStoredUser({ team_id: null })
    }
    selectedTeam.value = null
    saved.value = true
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    deleteSaving.value = false
    setBusy(teamId, false)
  }
}

async function approveApplication(application) {
  if (!selectedTeam.value) return
  setApplicationBusy(application.id, true)
  error.value = ''
  saved.value = false
  try {
    selectedTeam.value = await api(`/teams/${selectedTeam.value.id}/applications/${application.id}/approve`, { method: 'POST' })
    fillEditForm(selectedTeam.value)
    saved.value = true
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    setApplicationBusy(application.id, false)
  }
}

async function rejectApplication(application) {
  if (!selectedTeam.value) return
  setApplicationBusy(application.id, true)
  error.value = ''
  saved.value = false
  try {
    selectedTeam.value = await api(`/teams/${selectedTeam.value.id}/applications/${application.id}/reject`, { method: 'POST' })
    fillEditForm(selectedTeam.value)
    saved.value = true
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    setApplicationBusy(application.id, false)
  }
}

async function removeMember(member) {
  if (!selectedTeam.value || member.id === selectedTeam.value.owner_id) return
  if (!window.confirm(t('teams.removeMemberConfirm', { name: memberTitle(member) }))) return
  setMemberBusy(member.id, true)
  error.value = ''
  saved.value = false
  try {
    selectedTeam.value = await api(`/teams/${selectedTeam.value.id}/members/${member.id}`, { method: 'DELETE' })
    fillEditForm(selectedTeam.value)
    saved.value = true
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    setMemberBusy(member.id, false)
  }
}

onMounted(load)
watch(search, () => {
  teamPage.value = 1
})
watch(teams, () => {
  if (teamPage.value > teamTotalPages.value) {
    teamPage.value = teamTotalPages.value
  }
})
watch([memberSearch, memberSort], () => {
  memberPage.value = 1
})
watch(visibleTeamMembers, () => {
  if (memberPage.value > memberTotalPages.value) {
    memberPage.value = memberTotalPages.value
  }
})
</script>

<template>
  <section class="section teams-page">
    <div class="section-header teams-header">
      <div>
        <h1>{{ t('teams.title') }}</h1>
        <p class="muted">{{ t('teams.subtitle', { limit: config.member_limit }) }}</p>
      </div>
      <button v-if="canCreateTeam" class="button primary" type="button" @click="createOpen = !createOpen">
        <X v-if="createOpen" :size="16" />
        <Plus v-else :size="16" />
        {{ createOpen ? t('common.close') : t('teams.createTeam') }}
      </button>
      <span v-else-if="config.my_create_request_status === 'pending'" class="team-request-state application-pending">
        {{ t('teams.createRequestSent') }}
      </span>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="saved" class="pill">{{ t('common.saved') }}</p>

    <div class="teams-toolbar">
      <label class="field teams-search-field">
        <span>{{ t('common.search') }}</span>
        <div class="input-with-icon">
          <Search :size="16" />
          <input v-model="search" type="search" :placeholder="t('teams.searchPlaceholder')" @keyup.enter="load" />
        </div>
      </label>
      <button class="button" type="button" :disabled="loading" @click="load">
        <Search :size="16" />
        {{ t('common.apply') }}
      </button>
    </div>

    <form v-if="createOpen && canCreateTeam" class="team-create-panel card" @submit.prevent="createTeam">
      <div class="team-form-preview">
        <TeamAvatar :color="createForm.avatar_color" :label="createForm.name || t('teams.newTeam')" />
        <div>
          <h2>{{ t('teams.createTitle') }}</h2>
          <p class="muted">{{ t('teams.createHint') }}</p>
        </div>
      </div>
      <div class="team-form-grid">
        <label class="field">
          <span>{{ t('fields.name') }}</span>
          <input v-model="createForm.name" type="text" maxlength="80" required />
        </label>
        <label class="field team-form-description">
          <span>{{ t('fields.description') }}</span>
          <textarea v-model="createForm.description" maxlength="1000" :placeholder="t('teams.descriptionPlaceholder')" />
        </label>
      </div>
      <button class="button primary" type="submit" :disabled="createSaving">
        <Plus :size="16" />
        {{ t('teams.sendCreateRequest') }}
      </button>
    </form>

    <section v-if="canModerateTeams" class="team-applications-section card">
      <div class="section-header">
        <div>
          <h2>{{ t('teams.creationRequestsTitle') }}</h2>
          <p class="muted">{{ t('teams.creationRequestsHint') }}</p>
        </div>
        <span class="pill">{{ createRequests.length }}</span>
      </div>
      <div class="team-application-list">
        <div v-for="requestItem in createRequests" :key="requestItem.id" class="team-application-row">
          <TeamAvatar mini :src="requestItem.avatar_url" :color="requestItem.avatar_color" :label="requestItem.name" />
          <span class="team-application-main">
            <strong>{{ requestItem.name }}</strong>
            <span>{{ t('teams.requestedBy', { name: memberTitle(requestItem.requester) }) }}</span>
          </span>
          <span class="team-member-stat">
            <strong>#{{ requestItem.requester.pilot_number }}</strong>
            <span>RER {{ formatRating(requestItem.requester.rating) }}</span>
          </span>
          <div class="team-application-actions">
            <button class="icon-button" type="button" :title="t('teams.approveCreateRequest')" :disabled="busyCreateRequests[requestItem.id]" @click="approveCreateRequest(requestItem)">
              <Check :size="16" />
            </button>
            <button class="icon-button danger-icon" type="button" :title="t('teams.rejectCreateRequest')" :disabled="busyCreateRequests[requestItem.id]" @click="rejectCreateRequest(requestItem)">
              <XCircle :size="16" />
            </button>
          </div>
        </div>
        <div v-if="!createRequests.length" class="empty-row">{{ t('teams.noCreationRequests') }}</div>
      </div>
    </section>

    <div class="teams-layout">
      <div class="teams-list card">
        <div v-for="(team, index) in pagedTeams" :key="team.id" class="team-list-item" :class="{ 'is-selected': selectedTeam?.id === team.id, 'is-full': team.member_count >= team.member_limit }">
          <button class="team-list-open" type="button" :disabled="busyTeams[team.id]" @click="openTeam(team)">
            <span class="team-list-rank">#{{ (teamPage - 1) * teamPageSize + index + 1 }}</span>
            <TeamAvatar mini :src="team.avatar_url" :color="team.avatar_color" :label="team.name" />
            <span class="team-list-main">
              <strong>{{ team.name }}</strong>
              <span>{{ t('teams.ownerLine', { owner: ownerLabel(team) }) }} · RER {{ formatRating(team.average_rating) }}</span>
            </span>
            <span class="team-list-side">
              <span v-if="team.pending_application_count > 0" class="team-notification-badge" :title="pendingApplicationsTitle(team)" :aria-label="pendingApplicationsTitle(team)">
                <Bell :size="14" />
                {{ team.pending_application_count }}
              </span>
              <span class="team-capacity" :class="{ 'is-full': team.member_count >= team.member_limit }">
                <Users :size="15" />
                {{ team.member_count }}/{{ team.member_limit }}
              </span>
            </span>
            <span class="team-list-meter" aria-hidden="true">
              <span :style="{ width: `${teamFillPercent(team)}%` }"></span>
            </span>
          </button>
        </div>
        <div v-if="!teams.length" class="empty-row">{{ t('teams.empty') }}</div>
        <PaginationControls v-model:page="teamPage" :page-size="teamPageSize" :total-items="teams.length" />
      </div>

      <article v-if="selectedTeam" class="team-detail-card card">
        <div class="team-detail-hero">
          <button class="avatar-open-button" type="button" :title="t('avatar.open')" @click="teamAvatarViewerOpen = true">
            <TeamAvatar :src="selectedTeam.avatar_url" :color="selectedTeam.avatar_color" :label="selectedTeam.name" />
          </button>
          <div class="team-detail-main">
            <div class="team-detail-title">
              <h2>{{ selectedTeam.name }}</h2>
              <span class="status-badge">{{ selectedTeam.member_count }}/{{ selectedTeam.member_limit }}</span>
            </div>
            <p>{{ selectedTeam.description || t('teams.noDescription') }}</p>
            <div class="team-detail-meta">
              <span><Crown :size="15" />{{ ownerLabel(selectedTeam) }}</span>
              <span><Users :size="15" />{{ t('teams.membersCount', { count: selectedTeam.member_count, limit: selectedTeam.member_limit }) }}</span>
              <span>RER {{ formatRating(selectedTeam.average_rating) }}</span>
            </div>
          </div>
          <div class="team-detail-actions">
            <button v-if="selectedTeam.can_join" class="button primary" type="button" :disabled="busyTeams[selectedTeam.id]" @click="requestJoin(selectedTeam)">
              <Send :size="16" />
              {{ t('teams.requestJoin') }}
            </button>
            <span v-else-if="selectedTeam.my_application_status && !selectedTeam.is_member" class="team-request-state" :class="`application-${selectedTeam.my_application_status}`">
              {{ requestStatusLabel(selectedTeam.my_application_status) }}
            </span>
            <button v-if="selectedTeam.is_member && !selectedTeam.is_owner" class="button danger" type="button" :disabled="busyTeams[selectedTeam.id]" @click="leaveTeam">
              <LogOut :size="16" />
              {{ t('teams.leave') }}
            </button>
          </div>
        </div>

        <form v-if="selectedCanManage" class="team-edit-panel" @submit.prevent="saveTeam">
          <div class="section-header">
            <h2>{{ t('teams.editTitle') }}</h2>
            <button class="button primary" type="submit" :disabled="editSaving">
              <Save :size="16" />
              {{ t('common.save') }}
            </button>
          </div>
          <div class="team-form-grid">
            <label class="field">
              <span>{{ t('fields.name') }}</span>
              <input v-model="editForm.name" type="text" maxlength="80" required />
            </label>
            <label class="field team-form-description">
              <span>{{ t('fields.description') }}</span>
              <textarea v-model="editForm.description" maxlength="1000" />
            </label>
          </div>
          <div class="avatar-edit-panel team-avatar-upload-panel">
            <button class="avatar-open-button" type="button" :title="t('avatar.open')" @click="teamAvatarViewerOpen = true">
              <TeamAvatar :src="selectedTeam.avatar_url" :color="selectedTeam.avatar_color" :label="selectedTeam.name" />
            </button>
            <div class="avatar-edit-main">
              <strong>{{ t('avatar.teamTitle') }}</strong>
              <p class="muted">{{ t('avatar.teamHint') }}</p>
              <div class="avatar-upload-row">
                <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" @change="setTeamAvatarFile" />
                <button class="button" type="button" :disabled="teamAvatarSaving || !teamAvatarFile" @click="uploadTeamAvatar">
                  <Upload :size="16" />
                  {{ t('common.upload') }}
                </button>
              </div>
            </div>
          </div>
        </form>

        <section v-if="selectedCanManage" class="team-owner-panel">
          <div>
            <h2>{{ t('teams.ownerToolsTitle') }}</h2>
            <p class="muted">{{ t('teams.ownerLeaveHint') }}</p>
          </div>
          <form class="team-owner-tools" @submit.prevent="transferOwnership">
            <label class="field">
              <span>{{ t('teams.newOwner') }}</span>
              <select v-model="transferOwnerId" :disabled="!transferCandidates.length" required>
                <option value="">{{ t('teams.chooseMember') }}</option>
                <option v-for="member in transferCandidates" :key="member.id" :value="member.id">
                  {{ memberTitle(member) }} · #{{ member.pilot_number }} · RER {{ formatRating(member.rating) }}
                </option>
              </select>
            </label>
            <button class="button" type="submit" :disabled="transferSaving || !transferOwnerId">
              <UserCheck :size="16" />
              {{ t('teams.transferOwner') }}
            </button>
            <button class="button danger" type="button" :disabled="deleteSaving" @click="deleteTeam">
              <Trash2 :size="16" />
              {{ t('teams.deleteTeam') }}
            </button>
          </form>
          <p v-if="!transferCandidates.length" class="muted team-owner-note">{{ t('teams.noTransferCandidates') }}</p>
        </section>

        <section v-if="selectedCanManage" class="team-applications-section">
          <div class="section-header">
            <h2>{{ t('teams.applicationsTitle') }}</h2>
            <span class="pill">{{ selectedTeam.applications.length }}</span>
          </div>
          <div class="team-application-list">
            <div v-for="application in selectedTeam.applications" :key="application.id" class="team-application-row">
              <UserAvatar mini :src="application.user.avatar_url" :color="application.user.avatar_color" :label="application.user.login" />
              <span class="team-application-main">
                <strong>{{ memberTitle(application.user) }}</strong>
                <span>{{ application.user.login }} · #{{ application.user.pilot_number }} · RER {{ formatRating(application.user.rating) }} · {{ teamShortName(application.user.team_name) }}</span>
              </span>
              <span class="team-member-stat">
                <strong>{{ application.user.sr.toFixed(1) }}</strong>
                <span>SR</span>
              </span>
              <div class="team-application-actions">
                <button class="icon-button" type="button" :title="t('teams.approveApplication')" :disabled="busyApplications[application.id]" @click="approveApplication(application)">
                  <Check :size="16" />
                </button>
                <button class="icon-button danger-icon" type="button" :title="t('teams.rejectApplication')" :disabled="busyApplications[application.id]" @click="rejectApplication(application)">
                  <XCircle :size="16" />
                </button>
              </div>
            </div>
            <div v-if="!selectedTeam.applications.length" class="empty-row">{{ t('teams.noApplications') }}</div>
          </div>
        </section>

        <section class="team-members-section">
          <div class="section-header">
            <h2>{{ t('fields.participants') }}</h2>
            <span class="pill">RER {{ formatRating(selectedTeam.average_rating) }}</span>
          </div>
          <div class="pilot-inline-controls">
            <input v-model="memberSearch" type="search" :placeholder="t('teams.memberSearch')" />
            <select v-model="memberSort" :aria-label="t('common.sort')">
              <option value="rating_desc">{{ t('sort.ratingDesc') }}</option>
              <option value="rating_asc">{{ t('sort.ratingAsc') }}</option>
              <option value="sr_desc">{{ t('sort.srDesc') }}</option>
              <option value="sr_asc">{{ t('sort.srAsc') }}</option>
              <option value="alpha_asc">{{ t('sort.alphaAsc') }}</option>
              <option value="alpha_desc">{{ t('sort.alphaDesc') }}</option>
            </select>
          </div>
          <div class="team-members-list">
            <div v-for="member in pagedTeamMembers" :key="member.id" class="team-member-row">
              <UserAvatar mini :src="member.avatar_url" :color="member.avatar_color" :label="member.login" />
              <RouterLink class="team-member-main" :to="`/pilots/${member.id}`">
                <strong>{{ memberTitle(member) }}</strong>
                <span>{{ member.login }} · #{{ member.pilot_number }} · {{ teamShortName(memberTeamName(member)) }}</span>
              </RouterLink>
              <span class="team-member-stat">
                <strong>{{ formatRating(member.rating) }}</strong>
                <span>RER</span>
              </span>
              <span class="team-member-stat">
                <strong>{{ member.sr.toFixed(1) }}</strong>
                <span>SR</span>
              </span>
              <span class="team-member-games">
                <span v-if="member.id === selectedTeam.owner_id" class="team-owner-chip"><Crown :size="13" />{{ t('teams.owner') }}</span>
                {{ gamesLabel(member.games) }}
              </span>
              <div class="team-member-actions">
                <button
                  v-if="selectedCanManage && member.id !== selectedTeam.owner_id"
                  class="icon-button danger-icon"
                  type="button"
                  :title="t('teams.removeMember')"
                  :disabled="busyMembers[member.id]"
                  @click="removeMember(member)"
                >
                  <UserMinus :size="16" />
                </button>
              </div>
            </div>
            <div v-if="!visibleTeamMembers.length" class="empty-row">{{ selectedTeam.members.length ? t('common.noMatches') : t('teams.noMembers') }}</div>
          </div>
          <PaginationControls v-model:page="memberPage" :page-size="memberPageSize" :total-items="visibleTeamMembers.length" />
        </section>
      </article>

      <div v-else class="team-detail-empty card">
        <Users :size="34" />
        <h2>{{ t('teams.pickTeam') }}</h2>
        <p class="muted">{{ state.user ? t('teams.pickTeamHint') : t('teams.loginToJoin') }}</p>
      </div>
    </div>
    <AvatarViewer
      :open="teamAvatarViewerOpen"
      :src="selectedTeam?.avatar_url"
      :label="selectedTeam?.name || t('teams.newTeam')"
      :fallback-color="selectedTeam?.avatar_color"
      team
      @close="teamAvatarViewerOpen = false"
    />
  </section>
</template>
