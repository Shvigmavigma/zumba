<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { AlertCircle, LogIn, Plus, RotateCcw, Search, Shield, Users, X } from 'lucide-vue-next'
import { api } from '../api'
import AvatarViewer from '../components/AvatarViewer.vue'
import PaginationControls from '../components/PaginationControls.vue'
import { pilotName } from '../pilotDisplay'
import { state } from '../store'
import EmptyState from '../ui/EmptyState.vue'
import PageHeader from '../ui/PageHeader.vue'
import { prefersReducedMotion } from '../ui/motion/env'
import TeamCard from './teams/TeamCard.vue'
import TeamCreateDialog from './teams/TeamCreateDialog.vue'
import TeamCreateRequests from './teams/TeamCreateRequests.vue'
import TeamHero from './teams/TeamHero.vue'
import TeamLiveries from './teams/TeamLiveries.vue'
import TeamOwnerTools from './teams/TeamOwnerTools.vue'
import TeamRoster from './teams/TeamRoster.vue'
import TeamSearchBar from './teams/TeamSearchBar.vue'
import TeamStats from './teams/TeamStats.vue'
import TeamSwitcher from './teams/TeamSwitcher.vue'
import TeamToasts from './teams/TeamToasts.vue'
import { DEFAULT_TEAM_COLOR, normalizeTeamAbbreviation } from './teams/teamUtils'

const SAVED_TOAST_MS = 3500

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const teams = ref([])
const selectedTeam = ref(null)
const createRequests = ref([])
const config = ref({ member_limit: 5, my_create_request_status: null, pending_creation_request_count: 0 })
const search = ref('')
const appliedSearch = ref('')
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
const memberRatingGame = ref('ACC')
const teamPage = ref(1)
const teamPageSize = 12
const navDirection = ref('forward')
const stage = ref(null)
const createForm = ref({
  name: '',
  abbreviation: '',
  description: '',
  avatar_color: DEFAULT_TEAM_COLOR
})
const editForm = ref({
  name: '',
  abbreviation: '',
  description: '',
  avatar_color: DEFAULT_TEAM_COLOR
})
let savedTimer = 0

const canModerateTeams = computed(() => ['admin', 'moder'].includes(state.user?.role))
const canCreateTeam = computed(() => state.user?.status === 'active' && !state.user?.team_id && config.value.my_create_request_status !== 'pending')
const selectedCanManage = computed(() => Boolean(selectedTeam.value?.can_manage))
const transferOwnerId = ref('')
const transferCandidates = computed(() => selectedTeam.value?.members?.filter((member) => member.id !== selectedTeam.value.owner_id) || [])
const teamTotalPages = computed(() => Math.max(1, Math.ceil(teams.value.length / teamPageSize)))
const pagedTeams = computed(() => teams.value.slice((teamPage.value - 1) * teamPageSize, teamPage.value * teamPageSize))
const queryTeamId = computed(() => {
  const id = Number(route.query.team)
  return Number.isInteger(id) && id > 0 ? id : null
})
/** A ?team= deep link is still loading: show the gantry instead of flashing the grid. */
const openingFromLink = computed(() => loading.value && !selectedTeam.value && queryTeamId.value !== null)
const showMyTeam = computed(() => Boolean(state.user?.team_id) && selectedTeam.value?.id !== state.user.team_id)

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
    abbreviation: '',
    description: '',
    avatar_color: DEFAULT_TEAM_COLOR
  }
}

function fillEditForm(team) {
  editForm.value = {
    name: team?.name || '',
    abbreviation: team?.abbreviation || '',
    description: team?.description || '',
    avatar_color: team?.avatar_color || DEFAULT_TEAM_COLOR
  }
  transferOwnerId.value = team?.members?.find((member) => member.id !== team.owner_id)?.id || ''
}

function setTeamAvatarFile(event) {
  teamAvatarFile.value = event.target.files?.[0] || null
}

function memberTitle(member) {
  return pilotName(member, member.nickname || member.login)
}

function queryWithoutTeam() {
  const query = { ...route.query }
  delete query.team
  return query
}

/** Mirrors the open team in the URL so the page can be shared and Back returns to the grid. */
function syncTeamQuery(teamId) {
  if (String(route.query.team) === String(teamId)) return
  const query = { ...route.query, team: String(teamId) }
  if (route.query.team === undefined) router.push({ query })
  else router.replace({ query })
}

async function clearTeamQuery() {
  if (route.query.team === undefined) return
  await router.replace({ query: queryWithoutTeam() })
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
    const query = search.value.trim()
    const suffix = query ? `?search=${encodeURIComponent(query)}` : ''
    const [loadedTeams, loadedConfig] = await Promise.all([
      api(`/teams${suffix}`),
      api('/teams/config')
    ])
    teams.value = loadedTeams
    config.value = loadedConfig
    appliedSearch.value = query
    createRequests.value = canModerateTeams.value ? await api('/teams/create-requests') : []

    const selectedId = selectedTeam.value?.id || queryTeamId.value
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

async function openTeam(team, { updateUrl = true } = {}) {
  setBusy(team.id, true)
  error.value = ''
  try {
    selectedTeam.value = await api(`/teams/${team.id}`)
    fillEditForm(selectedTeam.value)
    if (updateUrl) syncTeamQuery(selectedTeam.value.id)
  } catch (err) {
    error.value = err.message
  } finally {
    setBusy(team.id, false)
  }
}

async function openTeamFromQuery(value) {
  const id = Number(value)
  if (!Number.isInteger(id) || id <= 0) {
    // Browser Back from an open team: return to the grid.
    if (value === undefined) selectedTeam.value = null
    return
  }
  if (selectedTeam.value?.id === id) return
  await openTeam({ id }, { updateUrl: false })
}

function closeTeam() {
  selectedTeam.value = null
  if (route.query.team === undefined) return
  const query = queryWithoutTeam()
  const listPath = router.resolve({ path: route.path, query }).fullPath
  if (window.history.state?.back === listPath) router.back()
  else router.replace({ query })
}

async function resetSearch() {
  search.value = ''
  await load()
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
        abbreviation: normalizeTeamAbbreviation(createForm.value.abbreviation),
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
        abbreviation: normalizeTeamAbbreviation(editForm.value.abbreviation),
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
    await clearTeamQuery()
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
    await clearTeamQuery()
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

/** Brings the list/detail stage into view when switching views from far down the page. */
function scrollStageIntoView() {
  const el = stage.value
  if (!el) return
  const offset = (parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--header-h')) || 76) + 16
  const top = el.getBoundingClientRect().top
  if (top >= offset) return
  window.scrollTo({ top: top + window.scrollY - offset, behavior: prefersReducedMotion() ? 'auto' : 'smooth' })
}

onMounted(load)
onBeforeUnmount(() => window.clearTimeout(savedTimer))
watch(() => route.query.team, openTeamFromQuery)
watch(search, () => {
  teamPage.value = 1
})
watch(teams, () => {
  if (teamPage.value > teamTotalPages.value) {
    teamPage.value = teamTotalPages.value
  }
})
// Push forward into a team, slide back to the grid.
watch(() => selectedTeam.value?.id ?? null, (id, previous) => {
  navDirection.value = id === null ? 'back' : 'forward'
  if (id !== previous) nextTick(scrollStageIntoView)
}, { flush: 'sync' })
watch(saved, (value) => {
  window.clearTimeout(savedTimer)
  if (value) savedTimer = window.setTimeout(() => { saved.value = false }, SAVED_TOAST_MS)
})
watch(createOpen, (open) => {
  if (!open && !createSaving.value) error.value = ''
})
</script>

<template>
  <div class="ui-page ui-shell ui-shell--wide teams">
    <PageHeader :eyebrow="t('teamsPage.eyebrow')" :title="t('teams.title')" :lead="t('teamsPage.lead')">
      <template #aside>
        <TeamStats :teams="teams" />
      </template>
      <template #actions>
        <button v-if="showMyTeam" class="ui-btn ui-btn--outline" type="button" :disabled="busyTeams[state.user.team_id]" @click="openTeam({ id: state.user.team_id })">
          <Shield :size="16" />{{ t('teamsPage.myTeam') }}
        </button>
        <button v-if="canCreateTeam" v-magnet v-spark class="ui-btn ui-btn--primary" type="button" @click="createOpen = true">
          <Plus :size="17" />{{ t('teams.createTeam') }}
        </button>
        <span v-else-if="config.my_create_request_status === 'pending'" class="ui-chip ui-chip--amber teams__pending">
          <span class="ui-dot ui-dot--amber ui-dot--live"></span>{{ t('teams.createRequestSent') }}
        </span>
      </template>
    </PageHeader>

    <div ref="stage" class="teams__stage">
      <Transition name="ui-fade">
        <TeamSwitcher v-if="selectedTeam" :teams="teams" :current-id="selectedTeam.id" :busy="busyTeams" @select="openTeam" @back="closeTeam" />
      </Transition>

      <Transition :name="`teams-${navDirection}`" mode="out-in">
        <!-- Deep link (?team=) still loading -->
        <EmptyState v-if="openingFromLink" key="opening" loading :title="t('teamsPage.loadingTeam')" />

        <!-- One team -->
        <div v-else-if="selectedTeam" :key="`team-${selectedTeam.id}`" class="teams__detail">
          <TeamHero
            :team="selectedTeam"
            :busy="Boolean(busyTeams[selectedTeam.id])"
            :signed-in="Boolean(state.user)"
            @join="requestJoin"
            @leave="leaveTeam"
            @open-avatar="teamAvatarViewerOpen = true"
          />
          <TeamLiveries
            v-if="selectedCanManage || selectedTeam.livery_image_count"
            v-reveal="{ delay: 80, y: 18 }"
            :team="selectedTeam"
            :can-manage="selectedCanManage"
            @update:team="selectedTeam = $event"
            @error="error = $event"
            @saved="saved = true"
          />
          <div class="teams__detail-grid" :class="{ 'has-tools': selectedCanManage }">
            <TeamRoster
              v-model:game="memberRatingGame"
              v-reveal="{ delay: 120, y: 18 }"
              :team="selectedTeam"
              :can-manage="selectedCanManage"
              :busy-members="busyMembers"
              @remove="removeMember"
            />
            <TeamOwnerTools
              v-if="selectedCanManage"
              v-model:form="editForm"
              v-model:transferOwnerId="transferOwnerId"
              v-reveal="{ delay: 200, y: 18 }"
              :team="selectedTeam"
              :candidates="transferCandidates"
              :game="memberRatingGame"
              :edit-saving="editSaving"
              :transfer-saving="transferSaving"
              :delete-saving="deleteSaving"
              :avatar-saving="teamAvatarSaving"
              :avatar-file="teamAvatarFile"
              :busy-applications="busyApplications"
              @save="saveTeam"
              @select-file="setTeamAvatarFile"
              @upload="uploadTeamAvatar"
              @transfer="transferOwnership"
              @delete="deleteTeam"
              @approve="approveApplication"
              @reject="rejectApplication"
              @open-avatar="teamAvatarViewerOpen = true"
            />
          </div>
        </div>

        <!-- All teams -->
        <div v-else key="grid" class="teams__browse">
          <TeamSearchBar v-model="search" :loading="loading" :limit="config.member_limit" @submit="load" />

          <p v-if="!state.user" class="ui-alert ui-alert--info teams__guest">
            <LogIn :size="18" />
            <span>{{ t('teamsPage.guest.text') }}</span>
            <RouterLink class="ui-link" to="/login">{{ t('teamsPage.guest.login') }}</RouterLink>
          </p>

          <TeamCreateRequests
            v-if="canModerateTeams"
            :requests="createRequests"
            :busy="busyCreateRequests"
            :game="memberRatingGame"
            @approve="approveCreateRequest"
            @reject="rejectCreateRequest"
          />

          <template v-if="teams.length">
            <ul class="teams__grid" :class="{ 'is-loading': loading }" :aria-busy="loading || null">
              <li v-for="(team, index) in pagedTeams" :key="team.id" v-reveal="{ delay: (index % 4) * 70, y: 26 }">
                <TeamCard :team="team" :busy="Boolean(busyTeams[team.id])" @open="openTeam" />
              </li>
            </ul>
            <PaginationControls v-model:page="teamPage" :page-size="teamPageSize" :total-items="teams.length" />
          </template>
          <EmptyState v-else-if="loading" loading :title="t('ui.common.loading')" />
          <EmptyState v-else-if="error" :icon="AlertCircle" :title="error">
            <button class="ui-btn ui-btn--outline ui-btn--sm" type="button" @click="load"><RotateCcw :size="15" />{{ t('ui.common.retry') }}</button>
          </EmptyState>
          <EmptyState v-else-if="appliedSearch" :icon="Search" :title="t('teamsPage.emptySearch.title')" :text="t('teamsPage.emptySearch.text')">
            <button class="ui-btn ui-btn--outline ui-btn--sm" type="button" @click="resetSearch"><X :size="15" />{{ t('teamsPage.search.reset') }}</button>
          </EmptyState>
          <EmptyState v-else :icon="Users" :title="t('teams.empty')" :text="t('teamsPage.empty.text')">
            <button v-if="canCreateTeam" class="ui-btn ui-btn--primary ui-btn--sm" type="button" @click="createOpen = true"><Plus :size="15" />{{ t('teams.createTeam') }}</button>
          </EmptyState>
        </div>
      </Transition>
    </div>

    <TeamCreateDialog
      v-model:form="createForm"
      :open="createOpen && canCreateTeam"
      :saving="createSaving"
      :error="createOpen ? error : ''"
      :limit="config.member_limit"
      @close="createOpen = false"
      @submit="createTeam"
    />

    <!-- The create sheet and the empty grid show errors in place; everywhere else they float. -->
    <TeamToasts :error="createOpen || !(teams.length || selectedTeam) ? '' : error" :saved="saved" @dismiss="error = ''" />

    <Teleport to="body">
      <AvatarViewer
        class="teams__viewer"
        :open="teamAvatarViewerOpen"
        :src="selectedTeam?.avatar_url"
        :label="selectedTeam?.name || t('teams.newTeam')"
        :fallback-color="selectedTeam?.avatar_color"
        team
        @close="teamAvatarViewerOpen = false"
      />
    </Teleport>
  </div>
</template>

<style scoped>
.teams {
  position: relative;
}

.teams__pending {
  min-height: 34px;
  padding: 0 14px;
}

/* ---------- Stage ---------- */
.teams__stage {
  display: grid;
  gap: 18px;
  min-width: 0;
}

.teams__browse,
.teams__detail {
  display: grid;
  gap: clamp(16px, 2vw, 22px);
  min-width: 0;
}

.teams__guest {
  align-items: center;
}

.teams__guest span {
  flex: 1 1 auto;
}

/* ---------- Grid ---------- */
.teams__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 290px), 1fr));
  gap: clamp(14px, 1.6vw, 20px);
  margin: 0;
  padding: 0;
  list-style: none;
  transition: opacity var(--dur-2) var(--ease-out);
}

.teams__grid.is-loading {
  opacity: 0.6;
}

/* ---------- Detail ---------- */
.teams__detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-items: start;
  gap: clamp(16px, 2vw, 22px);
}

.teams__detail-grid.has-tools {
  grid-template-columns: minmax(0, 1fr) minmax(360px, 460px);
}

/* ---------- View transitions: push into a team, slide back to the grid ---------- */
.teams-forward-enter-active,
.teams-back-enter-active {
  transition:
    opacity 420ms var(--ease-out),
    transform 560ms var(--ease-ios),
    filter 420ms var(--ease-out);
}

.teams-forward-leave-active,
.teams-back-leave-active {
  transition:
    opacity 180ms ease-in,
    transform 200ms ease-in,
    filter 180ms ease-in;
}

.teams-forward-enter-from {
  opacity: 0;
  filter: blur(8px);
  transform: translate3d(32px, 0, 0) scale(0.99);
}

.teams-forward-leave-to {
  opacity: 0;
  filter: blur(4px);
  transform: translate3d(-18px, 0, 0) scale(0.99);
}

.teams-back-enter-from {
  opacity: 0;
  filter: blur(8px);
  transform: translate3d(-32px, 0, 0) scale(0.99);
}

.teams-back-leave-to {
  opacity: 0;
  filter: blur(4px);
  transform: translate3d(18px, 0, 0) scale(0.99);
}

/* AvatarViewer is a shared legacy overlay; lift it above the sticky header. */
.teams__viewer {
  z-index: 120;
}

@media (max-width: 1180px) {
  .teams__detail-grid.has-tools {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (prefers-reduced-motion: reduce) {
  .teams-forward-enter-active,
  .teams-forward-leave-active,
  .teams-back-enter-active,
  .teams-back-leave-active {
    transition: opacity var(--dur-1);
  }

  .teams-forward-enter-from,
  .teams-forward-leave-to,
  .teams-back-enter-from,
  .teams-back-leave-to {
    filter: none;
    transform: none;
  }
}
</style>
