<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Check, ChevronLeft, ChevronRight, Copy, Download, ExternalLink, ImagePlus, Play, Plus, Save, Trash2, Trophy, Users, Vote, X } from 'lucide-vue-next'
import { api, apiDownload } from '../api'

const route = useRoute()
const router = useRouter()
const isPublic = computed(() => route.name === 'competition-view')
const items = ref([])
const selected = ref(null)
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')
const newForm = ref({ name: '', kind: 'vote' })
const participantName = ref('')
const nameDrafts = ref({})
const variant = ref('direct')
const groupCount = ref(2)
const advancingPlaces = ref([1])
const pollTimer = ref(null)
let pollingActive = false
const viewer = ref(null)
const imageViewer = ref(null)
const carouselIndexes = ref({})
const captchaAnswer = ref('')
const voting = ref(false)
const newVoterToken = () => globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`
const voterToken = ref(localStorage.getItem('competition-voter-token') || newVoterToken())

localStorage.setItem('competition-voter-token', voterToken.value)

const statusLabels = { draft: 'Черновик', 'in-progress': 'Идёт', complete: 'Завершено' }
const kindLabels = { vote: 'Голосование', tournament: 'Турнир' }
const selectionSystemLabel = (variant) => ({
  direct: 'Прямой плей-офф',
  qualifying: 'Отбор + плей-офф',
  groups: 'Группы + плей-офф',
  double_elimination: 'Верхняя + нижняя сетка (8 → 4)',
}[variant] || 'Прямой плей-офф')
const competitionMatchStageLabel = (match) => ({
  group: `Группа ${match?.group || 1}`,
  qualifying: 'Отбор',
  upper: 'Верхняя сетка',
  lower: 'Нижняя сетка',
  semifinal: 'Полуфинал',
  third_place: 'Матч за 3-е место',
  playoff: 'Плей-офф',
}[match?.stage] || 'Плей-офф')
const publicUrl = (path) => `${window.location.origin}${path}`
const mediaUrl = (value) => {
  const raw = String(value || '').trim()
  if (!raw) return ''
  if (/^(?:https?:|data:|blob:)/i.test(raw)) return raw
  return raw.startsWith('/') ? raw : `/${raw}`
}
const carouselKey = (scope, id) => `${scope}:${id}`
const carouselImages = (images) => (Array.isArray(images) ? images : []).map(mediaUrl).filter(Boolean)
const carouselIndex = (images, key) => {
  const list = carouselImages(images)
  if (!list.length) return 0
  const value = Number(carouselIndexes.value[key])
  return Number.isInteger(value) ? Math.max(0, Math.min(value, list.length - 1)) : 0
}
const carouselImage = (images, key) => carouselImages(images)[carouselIndex(images, key)] || ''
const carouselHasNavigation = (images) => carouselImages(images).length > 1
const carouselPosition = (images, key) => {
  const list = carouselImages(images)
  return list.length ? `${carouselIndex(images, key) + 1} / ${list.length}` : ''
}
function shiftCarousel(images, key, delta) {
  const list = carouselImages(images)
  if (list.length < 2) return
  const next = (carouselIndex(images, key) + delta + list.length) % list.length
  carouselIndexes.value = { ...carouselIndexes.value, [key]: next }
}
const imageViewerImage = computed(() => imageViewer.value?.images?.[imageViewer.value.index] || '')
const imageViewerHasPrevious = computed(() => Boolean(imageViewer.value && imageViewer.value.images.length > 1))
const imageViewerHasNext = computed(() => Boolean(imageViewer.value && imageViewer.value.images.length > 1))
const publicOverviewPath = (item) => item?.kind === 'tournament'
  ? (item.public_bracket_path || `/competitions/bracket/${item.public_token}`)
  : item?.public_path
const shownMatches = computed(() => {
  if (!viewer.value?.matches) return []
  const matchId = String(route.query.match || '')
  return matchId ? viewer.value.matches.filter((match) => match.id === matchId) : viewer.value.matches
})
const publicOpenMatches = computed(() => (viewer.value?.matches || []).filter((match) => match.status === 'open'))
const publicBracketColumns = computed(() => {
  const columns = []
  const byKey = new Map()
  for (const match of viewer.value?.matches || []) {
    const type = match.stage === 'group' ? 'group' : ['upper', 'lower', 'semifinal', 'third_place'].includes(match.stage) ? match.stage : 'round'
    const number = Number(match.stage === 'group' ? match.group : match.round) || 1
    const key = `${type}-${number}`
    let column = byKey.get(key)
    if (!column) {
      column = { key, type, number, label: competitionMatchStageLabel(match), matches: [] }
      byKey.set(key, column)
      columns.push(column)
    }
    column.matches.push(match)
  }
  const order = { group: 0, upper: 1, lower: 2, semifinal: 3, round: 4, third_place: 5 }
  return columns.sort((left, right) => order[left.type] - order[right.type] || left.number - right.number)
})
const publicMatchPath = (match) => `/competitions/view/${encodeURIComponent(route.params.token)}?match=${encodeURIComponent(match.id)}`
const publicBracketPath = computed(() => `/competitions/bracket/${encodeURIComponent(route.params.token || '')}`)
const formatVotes = (value) => {
  const amount = Number(value || 0)
  return `${amount} ${amount === 1 ? 'голос' : amount >= 2 && amount <= 4 ? 'голоса' : 'голосов'}`
}
const participantInitials = (participant) => String(participant?.name || '?').trim().slice(0, 2).toUpperCase()
const publicTotalVotes = computed(() => (viewer.value?.participants || []).reduce((sum, participant) => sum + Number(participant.votes || 0), 0))
const publicLeader = computed(() => [...(viewer.value?.participants || [])].sort((left, right) => Number(right.votes || 0) - Number(left.votes || 0))[0] || null)
const publicVoteShare = (participant) => {
  const total = publicTotalVotes.value
  return total ? Math.round((Number(participant.votes || 0) / total) * 100) : 0
}
const hasMyVote = (participant) => viewer.value?.my_vote === participant?.id
const hasMyMatchVote = (match, participant) => match?.my_vote === participant?.id
const publicPairLabel = computed(() => route.query.match ? 'Голосование пары' : 'Публичное голосование')
const groupPlaceOptions = computed(() => {
  const participantCount = selected.value?.participants?.length || 0
  const groups = Math.max(2, Number(groupCount.value) || 2)
  const maxPlaces = Math.max(1, Math.ceil(participantCount / groups))
  return Array.from({ length: maxPlaces }, (_, index) => index + 1)
})

function openImageViewer(images, index = 0, title = 'Изображение') {
  const list = (Array.isArray(images) ? images : [images]).map(mediaUrl).filter(Boolean)
  if (!list.length) return
  const nextIndex = Math.max(0, Math.min(Number(index) || 0, list.length - 1))
  imageViewer.value = { images: list, index: nextIndex, title: String(title || 'Изображение') }
}

function closeImageViewer() {
  imageViewer.value = null
}

function shiftImageViewer(delta) {
  if (!imageViewer.value || imageViewer.value.images.length < 2) return
  const count = imageViewer.value.images.length
  imageViewer.value.index = (imageViewer.value.index + delta + count) % count
}

function handleImageClick(event) {
  const image = event.target?.closest?.('.competition-images img')
  if (!image) return
  const container = image.closest('.competition-images')
  const images = Array.from(container?.querySelectorAll('img') || [])
    .map((entry) => mediaUrl(entry.currentSrc || entry.src))
    .filter(Boolean)
  const current = mediaUrl(image.currentSrc || image.src)
  const index = Math.max(0, images.indexOf(current))
  const title = image.closest('.competition-participant-card, .competition-public-card, .competition-duel-side, .competition-public-roster-item')
    ?.querySelector('h2, strong')?.textContent?.trim() || 'Изображение'
  event.preventDefault()
  event.stopPropagation()
  openImageViewer(images.length ? images : [current], index, title)
}

function flash(message) {
  notice.value = message
  window.setTimeout(() => { notice.value = '' }, 2600)
}

async function loadStaff() {
  loading.value = true
  error.value = ''
  try {
    items.value = await api('/competitions')
    const id = Number(route.query.id)
    if (id) await openCompetition(items.value.find((item) => item.id === id) || items.value[0])
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function openCompetition(item) {
  if (!item) return
  try {
    selected.value = await api(`/competitions/${item.id}`)
    variant.value = selected.value.settings?.variant || 'direct'
    groupCount.value = Number(selected.value.settings?.group_count || 2)
    advancingPlaces.value = (selected.value.settings?.advancing_places || [1]).map(Number).filter((place) => Number.isInteger(place) && place > 0)
    if (!advancingPlaces.value.length) advancingPlaces.value = [1]
    router.replace({ query: { id: String(item.id) } })
  } catch (err) { error.value = err.message }
}

async function createCompetition() {
  if (!newForm.value.name.trim()) return
  saving.value = true
  try {
    const created = await api('/competitions', { method: 'POST', body: newForm.value })
    items.value = [created, ...items.value]
    newForm.value = { name: '', kind: 'vote' }
    await openCompetition(created)
  } catch (err) { error.value = err.message } finally { saving.value = false }
}

async function saveVariant() {
  if (!selected.value || selected.value.kind !== 'tournament') return
  if (variant.value === 'groups' && !advancingPlaces.value.length) {
    error.value = 'Отметьте хотя бы одно место, выходящее в плей-офф'
    return
  }
  if (variant.value === 'double_elimination' && selected.value.participants.length !== 8) {
    error.value = 'Для верхней и нижней сетки добавьте ровно 8 участников'
    return
  }
  try {
    selected.value = await api(`/competitions/${selected.value.id}`, { method: 'PATCH', body: { variant: variant.value, group_count: Number(groupCount.value), advancing_places: variant.value === 'groups' ? [...advancingPlaces.value].map(Number).sort((left, right) => left - right) : [1] } })
    syncList(selected.value)
    flash('Настройки сохранены')
  } catch (err) { error.value = err.message }
}

function syncList(updated) {
  items.value = items.value.map((item) => item.id === updated.id ? updated : item)
}

async function addParticipant() {
  if (!participantName.value.trim() || !selected.value) return
  try {
    const participant = await api(`/competitions/${selected.value.id}/participants`, { method: 'POST', body: { name: participantName.value } })
    selected.value.participants.push(participant)
    participantName.value = ''
  } catch (err) { error.value = err.message }
}

async function saveParticipant(participant) {
  const name = String(nameDrafts.value[participant.id] || participant.name).trim()
  if (!name) return
  try {
    const updated = await api(`/competitions/${selected.value.id}/participants/${participant.id}`, { method: 'PATCH', body: { name } })
    Object.assign(participant, updated)
    nameDrafts.value[participant.id] = updated.name
  } catch (err) { error.value = err.message }
}

async function removeParticipant(participant) {
  if (!window.confirm(`Удалить карточку «${participant.name}»?`)) return
  try {
    await api(`/competitions/${selected.value.id}/participants/${participant.id}`, { method: 'DELETE' })
    selected.value.participants = selected.value.participants.filter((item) => item.id !== participant.id)
  } catch (err) { error.value = err.message }
}

async function uploadImage(participant, event) {
  const files = Array.from(event.target.files || [])
  event.target.value = ''
  if (!files.length) return
  const freeSlots = Math.max(0, 4 - (participant.images?.length || 0))
  if (!freeSlots) {
    error.value = 'На карточке можно разместить не более 4 изображений'
    return
  }
  try {
    const selectedFiles = files.slice(0, freeSlots)
    const body = new FormData()
    selectedFiles.forEach((file) => body.append('file', file))
    const updated = await api(`/competitions/${selected.value.id}/participants/${participant.id}/media`, { method: 'POST', body })
    Object.assign(participant, updated)
    if (files.length > freeSlots) {
      flash(`Добавлено ${selectedFiles.length} из ${files.length}: максимум 4 изображения`)
    } else {
      flash(`Добавлено изображений: ${selectedFiles.length}`)
    }
  } catch (err) { error.value = err.message }
}

async function removeImage(participant, index) {
  try {
    await api(`/competitions/${selected.value.id}/participants/${participant.id}/media/${index}`, { method: 'DELETE' })
    participant.images.splice(index, 1)
  } catch (err) { error.value = err.message }
}

async function startCompetition() {
  try {
    selected.value = await api(`/competitions/${selected.value.id}/start`, { method: 'POST' })
    syncList(selected.value)
    flash('Соревнование запущено')
  } catch (err) { error.value = err.message }
}

async function closeCompetition() {
  try {
    selected.value = await api(`/competitions/${selected.value.id}/close`, { method: 'POST' })
    syncList(selected.value)
    flash('Результаты опубликованы')
  } catch (err) { error.value = err.message }
}

async function closeMatch(match) {
  try {
    selected.value = await api(`/competitions/${selected.value.id}/matches/${match.id}/close`, { method: 'POST' })
    syncList(selected.value)
    flash('Пара завершена')
  } catch (err) { error.value = err.message }
}

async function exportCompetition(item = selected.value) {
  if (!item) return
  try {
    const blob = await apiDownload(`/competitions/${item.id}/export`)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `competition-${item.id}.json`
    link.click()
    URL.revokeObjectURL(url)
  } catch (err) { error.value = err.message }
}

async function deleteCompetition(item) {
  if (!window.confirm(`Удалить соревнование «${item.name}»?`)) return
  try {
    await api(`/competitions/${item.id}`, { method: 'DELETE' })
    items.value = items.value.filter((entry) => entry.id !== item.id)
    if (selected.value?.id === item.id) selected.value = null
  } catch (err) { error.value = err.message }
}

async function copyLink(path) {
  try { await navigator.clipboard.writeText(publicUrl(path)); flash('Ссылка скопирована') } catch { error.value = 'Не удалось скопировать ссылку' }
}

async function loadViewer({ refreshCaptcha = false } = {}) {
  try {
    const query = new URLSearchParams({ voter_token: voterToken.value })
    const nextViewer = await api(`/competitions/public/${route.params.token}?${query.toString()}`)
    if (nextViewer.kind === 'tournament' && !route.query.match) {
      await router.replace({ name: 'competition-bracket', params: { token: String(route.params.token || '') } })
      return
    }
    const previousCaptcha = viewer.value?.captcha
    viewer.value = nextViewer
    error.value = ''
    if (!refreshCaptcha && previousCaptcha) viewer.value.captcha = previousCaptcha
    else captchaAnswer.value = ''
  } catch (err) {
    // Keep an already-rendered viewer usable during a transient poll failure.
    // A first-load failure still gets a clear invalid-link error state.
    if (!viewer.value) error.value = err.message
  }
}

async function submitVote(participantId, matchId = null) {
  if (!captchaAnswer.value) return
  voting.value = true
  const previousVote = matchId
    ? viewer.value?.matches?.find((match) => match.id === matchId)?.my_vote
    : viewer.value?.my_vote
  try {
    const path = matchId ? `/competitions/public/${route.params.token}/match/${matchId}/vote` : `/competitions/public/${route.params.token}/vote`
    await api(path, { method: 'POST', body: { participant_id: participantId, voter_token: voterToken.value, captcha_token: viewer.value.captcha.token, captcha_answer: Number(captchaAnswer.value) } })
    await loadViewer({ refreshCaptcha: true })
    flash(previousVote ? 'Голос изменён' : 'Голос принят')
  } catch (err) {
    error.value = err.message
    if (err.message === 'Неверная проверка на бота') {
      // A challenge can expire while a viewer is left open for a long time;
      // issue a fresh one instead of leaving the form stuck on a dead token.
      await loadViewer({ refreshCaptcha: true })
    }
  } finally { voting.value = false }
}

function startPolling() {
  if (!isPublic.value) return
  pollingActive = true
  const tick = async () => {
    if (!pollingActive || !isPublic.value) return
    await loadViewer()
    if (pollingActive && isPublic.value && viewer.value?.status !== 'complete') pollTimer.value = window.setTimeout(tick, 5000)
  }
  pollTimer.value = window.setTimeout(tick, 5000)
}

function stopPolling() {
  pollingActive = false
  if (pollTimer.value) {
    window.clearTimeout(pollTimer.value)
    pollTimer.value = null
  }
}

watch(() => `${route.name}:${route.params.token || ''}:${route.query.match || ''}`, (next, previous) => {
  if (next === previous || !isPublic.value) return
  stopPolling()
  viewer.value = null
  closeImageViewer()
  captchaAnswer.value = ''
  error.value = ''
  loadViewer({ refreshCaptcha: true })
  startPolling()
})

onMounted(() => {
  document.addEventListener('click', handleImageClick, true)
  if (isPublic.value) { loadViewer({ refreshCaptcha: true }); startPolling() } else loadStaff()
})
onBeforeUnmount(() => {
  document.removeEventListener('click', handleImageClick, true)
  stopPolling()
})
</script>

<template>
  <section v-if="!isPublic" class="section competitions-page" @keydown.esc.window="closeImageViewer" @keydown.left.window="shiftImageViewer(-1)" @keydown.right.window="shiftImageViewer(1)">
    <div class="section-header">
      <div><h1>Голосования и турниры</h1><p class="muted">Медиа-соревнования для модераторов и администраторов</p></div>
      <span class="pill">{{ items.length }} / 10</span>
    </div>
    <p v-if="error" class="error">{{ error }}</p><p v-if="notice" class="success">{{ notice }}</p>
    <div class="competition-layout">
      <aside class="card competition-sidebar">
        <h2>Новое соревнование</h2>
        <form class="competition-create" @submit.prevent="createCompetition">
          <label class="field"><span>Название</span><input v-model="newForm.name" maxlength="160" placeholder="Например, Лучший ливрей" required /></label>
          <label class="field"><span>Тип</span><select v-model="newForm.kind"><option value="vote">Голосование</option><option value="tournament">Турнирная сетка</option></select></label>
          <button class="button primary" :disabled="saving"><Plus :size="16" />Создать</button>
        </form>
        <div class="competition-list">
          <button v-for="item in items" :key="item.id" type="button" class="competition-list-item" :class="{ 'is-selected': selected?.id === item.id }" @click="openCompetition(item)">
            <span><strong>{{ item.name }}</strong><small>{{ kindLabels[item.kind] }} · {{ statusLabels[item.status] }}</small></span><ExternalLink :size="15" />
          </button>
          <p v-if="!items.length && !loading" class="empty-row">Пока нет соревнований.</p>
        </div>
      </aside>

      <main v-if="selected" class="competition-workspace">
        <article class="card competition-card-head">
          <div><span class="pill">{{ kindLabels[selected.kind] }}</span><h2>{{ selected.name }}</h2><p class="muted">Статус: {{ statusLabels[selected.status] }} · {{ selected.participants.length }} карточек<span v-if="selected.kind === 'tournament'"> · Система отбора: {{ selectionSystemLabel(selected.settings?.variant) }}</span></p></div>
          <div class="competition-head-actions">
            <button class="button" type="button" @click="copyLink(publicOverviewPath(selected))"><Copy :size="16" />{{ selected.kind === 'tournament' ? 'Ссылка на обзор' : 'Ссылка' }}</button>
            <a class="button" :href="publicUrl(publicOverviewPath(selected))" target="_blank" rel="noopener noreferrer"><ExternalLink :size="16" />{{ selected.kind === 'tournament' ? 'Открыть обзор' : 'Открыть' }}</a>
            <a v-if="selected.kind === 'tournament'" class="button primary" :href="publicUrl(publicOverviewPath(selected))" target="_blank" rel="noopener noreferrer"><Trophy :size="16" />Открыть сетку</a>
            <button class="button" type="button" @click="exportCompetition()"><Download :size="16" />Выгрузить</button>
            <button v-if="selected.status === 'draft'" class="button primary" type="button" @click="startCompetition"><Play :size="16" />Запустить</button>
            <button v-else-if="selected.status === 'in-progress'" class="button primary" type="button" @click="closeCompetition"><Check :size="16" />Закрыть</button>
            <button class="icon-button danger-icon" type="button" title="Удалить" @click="deleteCompetition(selected)"><Trash2 :size="16" /></button>
          </div>
        </article>

        <article v-if="selected.kind === 'tournament' && selected.status === 'draft'" class="card competition-settings-card">
          <label class="field"><span>Вариант турнирной сетки</span><select v-model="variant"><option value="direct">Прямой плей-офф</option><option value="qualifying">С отбором</option><option value="groups">Группы</option><option value="double_elimination">Верхняя + нижняя сетка (ровно 8)</option></select></label>
          <label v-if="variant === 'groups'" class="field"><span>Количество групп</span><input v-model.number="groupCount" type="number" min="2" max="8" /></label>
          <fieldset v-if="variant === 'groups'" class="competition-advancing-places"><legend>В плей-офф выходят места</legend><div class="competition-place-options"><label v-for="place in groupPlaceOptions" :key="place"><input v-model="advancingPlaces" type="checkbox" :value="place" /><span>{{ place }}-е место</span></label></div><small class="muted">Выбор применяется к каждой группе.</small></fieldset>
          <button class="button" type="button" @click="saveVariant"><Save :size="16" />Сохранить вариант</button>
        </article>

        <article class="card competition-participants-card">
          <div class="section-header"><div><h2>Карточки участников</h2><p class="muted">До 4 изображений на карточку. Они отображаются в админке и публичном просмотре.</p></div><span class="pill">{{ selected.participants.length }}</span></div>
          <form v-if="selected.status === 'draft'" class="competition-add-participant" @submit.prevent="addParticipant"><input v-model="participantName" placeholder="Имя участника" required /><button class="button primary" type="submit"><Plus :size="16" />Добавить карточку</button></form>
          <div class="competition-participant-grid">
            <article v-for="participant in selected.participants" :key="participant.id" class="competition-participant-card">
              <div class="competition-images"><div v-for="(image, index) in participant.images" :key="image" class="competition-image"><img :src="mediaUrl(image)" :alt="`Изображение ${participant.name}`" role="button" tabindex="0" @click.stop="openImageViewer(participant.images, index, participant.name)" @keydown.enter.stop.prevent="openImageViewer(participant.images, index, participant.name)" @keydown.space.stop.prevent="openImageViewer(participant.images, index, participant.name)" /><button v-if="selected.status === 'draft'" type="button" title="Удалить изображение" @click="removeImage(participant, index)"><X :size="12" /></button></div><label v-if="selected.status === 'draft' && participant.images.length < 4" class="competition-image-add"><ImagePlus :size="20" /><input type="file" multiple accept="image/png,image/jpeg,image/webp,image/gif" @change="uploadImage(participant, $event)" /></label><div v-if="!participant.images.length" class="competition-image-empty">Нет изображений</div></div>
              <input v-if="selected.status === 'draft'" v-model="nameDrafts[participant.id]" class="competition-participant-name" :placeholder="participant.name" @keyup.enter="saveParticipant(participant)" @blur="saveParticipant(participant)" /><strong v-else>{{ participant.name }}</strong>
              <button v-if="selected.status === 'draft'" class="button small" type="button" @click="removeParticipant(participant)"><Trash2 :size="14" />Удалить</button>
              <span v-if="selected.status !== 'draft'" class="muted">Голосов: {{ participant.votes }}</span>
            </article>
          </div>
        </article>

        <article v-if="selected.kind === 'tournament' && selected.matches.length" class="card competition-bracket-card">
          <div class="section-header"><div><h2>Турнирная сетка</h2><p class="muted">Для каждой пары создана отдельная ссылка.</p></div><Trophy :size="22" /></div>
          <div class="competition-match-list"><div v-for="match in selected.matches" :key="match.id" class="competition-match-row"><span>{{ competitionMatchStageLabel(match) }}</span><strong>{{ match.a_name || '—' }} — {{ match.b_name || 'автопроход' }}</strong><span class="muted">{{ match.status === 'open' ? 'Открыта' : 'Завершена' }}</span><button class="button small" type="button" @click="copyLink(match.public_path)"><Copy :size="14" />Ссылка пары</button><a class="button small" :href="publicUrl(match.public_path)" target="_blank" rel="noopener noreferrer"><ExternalLink :size="14" />Открыть</a><button v-if="match.status === 'open'" class="button small primary" type="button" @click="closeMatch(match)"><Check :size="14" />Закрыть пару</button></div></div>
        </article>

        <article v-if="selected.status === 'complete'" class="card competition-results-card"><h2>Результаты</h2><ol><li v-for="result in selected.results" :key="result.participant_id"><strong>{{ selected.participants.find((item) => item.id === result.participant_id)?.name || 'Участник' }}</strong><span>{{ result.votes }} голосов</span></li></ol></article>
      </main>
      <div v-else class="card competition-empty"><Trophy :size="34" /><h2>Выберите соревнование</h2><p class="muted">Создайте новое или откройте сохранённое.</p></div>
    </div>
  </section>

  <section v-else class="section competition-viewer-page" @keydown.esc.window="closeImageViewer" @keydown.left.window="shiftImageViewer(-1)" @keydown.right.window="shiftImageViewer(1)">
    <div v-if="error" class="card competition-empty"><h1>Ссылка недействительна</h1><p class="error">{{ error }}</p></div>
    <template v-else-if="viewer">
      <header class="competition-viewer-head"><div class="competition-viewer-kicker"><span class="competition-viewer-eyebrow"><Trophy :size="15" />{{ publicPairLabel }}</span><span class="competition-viewer-status" :class="`is-${viewer.status}`"><i></i>{{ statusLabels[viewer.status] }}</span></div><div class="competition-viewer-title-row"><h1>{{ viewer.name }}</h1><span v-if="viewer.kind === 'vote'" class="competition-viewer-total"><Vote :size="15" />{{ formatVotes(publicTotalVotes) }}</span><span v-else class="competition-viewer-total"><Users :size="15" />{{ viewer.matches.length }} пар</span></div><p class="muted">{{ viewer.status === 'complete' ? 'Голосование завершено. Итоговые результаты опубликованы.' : 'Промежуточные результаты обновляются автоматически.' }}<span v-if="viewer.kind === 'tournament'"> · Система отбора: {{ selectionSystemLabel(viewer.settings?.variant) }}</span></p></header>
      <div v-if="viewer.status === 'in-progress'" class="card competition-captcha"><div class="competition-captcha-copy"><span class="competition-captcha-kicker"><Check :size="14" />Защищённое голосование</span><strong>Подтвердите, что вы человек</strong><small class="muted">Один активный голос с этого устройства для каждой карточки или пары — его можно изменить.</small></div><label class="field competition-captcha-field"><span>{{ viewer.captcha.question }}</span><input v-model="captchaAnswer" inputmode="numeric" autocomplete="off" placeholder="Ответ" /></label></div>
       <div v-if="viewer.kind === 'vote'" class="competition-vote-list"><article v-for="(participant, index) in viewer.participants" :key="participant.id" class="card competition-vote-list-item" :class="{ 'is-leading': publicLeader?.id === participant.id, 'is-selected': hasMyVote(participant) }"><div class="competition-vote-list-rank">#{{ index + 1 }}</div><div class="competition-carousel competition-carousel-vote"><button v-if="carouselHasNavigation(participant.images)" type="button" class="competition-carousel-arrow" aria-label="Предыдущее изображение" title="Предыдущее изображение" @click.stop="shiftCarousel(participant.images, carouselKey('vote', participant.id), -1)"><ChevronLeft :size="20" /></button><button v-if="participant.images?.length" type="button" class="competition-carousel-image" :aria-label="`Открыть изображение ${participant.name}`" @click.stop="openImageViewer(participant.images, carouselIndex(participant.images, carouselKey('vote', participant.id)), participant.name)"><img :src="carouselImage(participant.images, carouselKey('vote', participant.id))" :alt="`Изображение ${participant.name}`" /></button><div v-else class="competition-image-empty"><span>{{ participantInitials(participant) }}</span></div><button v-if="carouselHasNavigation(participant.images)" type="button" class="competition-carousel-arrow" aria-label="Следующее изображение" title="Следующее изображение" @click.stop="shiftCarousel(participant.images, carouselKey('vote', participant.id), 1)"><ChevronRight :size="20" /></button><span v-if="carouselHasNavigation(participant.images)" class="competition-carousel-counter">{{ carouselPosition(participant.images, carouselKey('vote', participant.id)) }}</span></div><div class="competition-vote-list-content"><div class="competition-vote-list-heading"><div class="competition-public-card-name"><span class="competition-public-avatar">{{ participantInitials(participant) }}</span><h2>{{ participant.name }}</h2></div><div class="competition-vote-list-heading-meta"><span v-if="hasMyVote(participant)" class="competition-vote-selection">Ваш выбор</span><span v-if="publicLeader?.id === participant.id" class="competition-leader-badge">Лидер</span></div></div><div class="competition-public-score-row"><strong class="competition-vote-count">{{ formatVotes(participant.votes) }}</strong><span>{{ publicVoteShare(participant) }}%</span></div><div class="competition-public-progress" aria-hidden="true"><span :style="{ width: `${publicVoteShare(participant)}%` }"></span></div><button class="button primary competition-vote-button" type="button" :disabled="viewer.status !== 'in-progress' || voting" :aria-label="`${hasMyVote(participant) ? 'Переголосовать' : 'Голосовать'} за ${participant.name}`" @click="submitVote(participant.id)">{{ viewer.status === 'in-progress' ? (hasMyVote(participant) ? 'Переголосовать' : 'Голосовать') : 'Голосование завершено' }}</button></div></article><div v-if="!viewer.participants.length" class="competition-empty"><Trophy :size="30" /><h2>Карточки ещё не добавлены</h2><p class="muted">Организатор добавит участников перед стартом.</p></div></div>
      <template v-else>
         <div v-if="route.query.match" class="competition-public-matches"><div class="competition-pair-toolbar"><div><span class="competition-viewer-eyebrow"><Trophy :size="14" />{{ shownMatches.length ? 'Сражение пары' : 'Ссылка пары' }}</span><p class="muted">Выберите одного участника. Результат обновится автоматически.</p></div><a class="competition-back-link" :href="publicBracketPath"><ArrowLeft :size="15" />К сетке</a></div><p v-if="!shownMatches.length" class="empty-row">Пара ещё не создана или ссылка устарела.</p><article v-for="match in shownMatches" :key="match.id" class="card competition-public-match" :class="{ 'is-closed': match.status === 'closed' }"><div class="competition-match-head"><span class="pill">{{ match.stage === 'group' ? `Группа ${match.group}` : match.stage === 'qualifying' ? 'Отбор' : `Раунд ${match.round}` }}</span><span class="competition-match-state" :class="`is-${match.status}`"><i></i>{{ match.status === 'open' ? 'Голосование открыто' : match.status === 'bye' ? 'Автопроход' : `Победитель: ${match.winner_name || '—'}` }}</span></div><div class="competition-duel"><article class="competition-duel-side" :class="{ 'is-selected': hasMyMatchVote(match, match.a) }"><div class="competition-duel-side-header"><span class="pill">Кандидат 1</span><span>{{ formatVotes(match.votes_a) }}</span></div><div class="competition-carousel competition-carousel-duel"><button v-if="carouselHasNavigation(match.a?.images)" type="button" class="competition-carousel-arrow" aria-label="Предыдущее изображение" title="Предыдущее изображение" @click.stop="shiftCarousel(match.a?.images, carouselKey(`duel:${match.id}`, 'a'), -1)"><ChevronLeft :size="20" /></button><button v-if="match.a?.images?.length" type="button" class="competition-carousel-image" :aria-label="`Открыть изображение ${match.a.name}`" @click.stop="openImageViewer(match.a.images, carouselIndex(match.a.images, carouselKey(`duel:${match.id}`, 'a')), match.a.name)"><img :src="carouselImage(match.a.images, carouselKey(`duel:${match.id}`, 'a'))" :alt="`Изображение ${match.a.name}`" /></button><div v-else class="competition-image-empty"><span>{{ participantInitials(match.a) }}</span></div><button v-if="carouselHasNavigation(match.a?.images)" type="button" class="competition-carousel-arrow" aria-label="Следующее изображение" title="Следующее изображение" @click.stop="shiftCarousel(match.a?.images, carouselKey(`duel:${match.id}`, 'a'), 1)"><ChevronRight :size="20" /></button><span v-if="carouselHasNavigation(match.a?.images)" class="competition-carousel-counter">{{ carouselPosition(match.a?.images, carouselKey(`duel:${match.id}`, 'a')) }}</span></div><div class="competition-duel-side-footer"><strong>{{ match.a?.name || '—' }}</strong><button class="button primary competition-duel-vote" type="button" :disabled="!match.a || match.status !== 'open' || viewer.status !== 'in-progress' || voting" :aria-label="`Голосовать за ${match.a?.name || 'участника'}`" @click.stop="submitVote(match.a?.id, match.id)">{{ hasMyMatchVote(match, match.a) ? 'Переголосовать' : 'Голосовать' }}</button></div></article><div class="competition-duel-vs"><span>VS</span><small>{{ formatVotes(Number(match.votes_a || 0) + Number(match.votes_b || 0)) }}</small></div><article class="competition-duel-side" :class="{ 'is-selected': hasMyMatchVote(match, match.b) }"><div class="competition-duel-side-header"><span class="pill">Кандидат 2</span><span>{{ formatVotes(match.votes_b) }}</span></div><div class="competition-carousel competition-carousel-duel"><button v-if="carouselHasNavigation(match.b?.images)" type="button" class="competition-carousel-arrow" aria-label="Предыдущее изображение" title="Предыдущее изображение" @click.stop="shiftCarousel(match.b?.images, carouselKey(`duel:${match.id}`, 'b'), -1)"><ChevronLeft :size="20" /></button><button v-if="match.b?.images?.length" type="button" class="competition-carousel-image" :aria-label="`Открыть изображение ${match.b.name}`" @click.stop="openImageViewer(match.b.images, carouselIndex(match.b.images, carouselKey(`duel:${match.id}`, 'b')), match.b.name)"><img :src="carouselImage(match.b.images, carouselKey(`duel:${match.id}`, 'b'))" :alt="`Изображение ${match.b.name}`" /></button><div v-else class="competition-image-empty"><span>{{ participantInitials(match.b) }}</span></div><button v-if="carouselHasNavigation(match.b?.images)" type="button" class="competition-carousel-arrow" aria-label="Следующее изображение" title="Следующее изображение" @click.stop="shiftCarousel(match.b?.images, carouselKey(`duel:${match.id}`, 'b'), 1)"><ChevronRight :size="20" /></button><span v-if="carouselHasNavigation(match.b?.images)" class="competition-carousel-counter">{{ carouselPosition(match.b?.images, carouselKey(`duel:${match.id}`, 'b')) }}</span></div><div class="competition-duel-side-footer"><strong>{{ match.b?.name || 'Автопроход' }}</strong><button class="button primary competition-duel-vote" type="button" :disabled="!match.b || match.status !== 'open' || viewer.status !== 'in-progress' || voting" :aria-label="`Голосовать за ${match.b?.name || 'участника'}`" @click.stop="submitVote(match.b?.id, match.id)">{{ hasMyMatchVote(match, match.b) ? 'Переголосовать' : 'Голосовать' }}</button></div></article></div><div class="competition-pair-progress" aria-hidden="true"><span :style="{ width: `${(Number(match.votes_a || 0) + Number(match.votes_b || 0)) ? Math.round((Number(match.votes_a || 0) / (Number(match.votes_a || 0) + Number(match.votes_b || 0))) * 100) : 50}%` }"></span></div><div v-if="match.status !== 'open'" class="competition-pair-result"><Check :size="15" />{{ match.winner_name ? `Победитель: ${match.winner_name}` : 'Пара закрыта' }}</div></article></div>
        <div v-else class="competition-public-overview">
        <article class="card competition-public-roster"><div class="section-header"><div><h2>Все кандидаты</h2><p class="muted">Общая ссылка показывает полный список участников турнира.</p></div><span class="pill">{{ viewer.participants.length }}</span></div><div class="competition-public-roster-grid"><article v-for="participant in viewer.participants" :key="participant.id" class="competition-public-roster-item"><div class="competition-images roster"><img v-if="participant.images[0]" :src="mediaUrl(participant.images[0])" alt="" /><div v-else class="competition-image-empty">Нет изображения</div></div><strong>{{ participant.name }}</strong></article><p v-if="!viewer.participants.length" class="empty-row">Кандидаты ещё не добавлены.</p></div></article>
          <article class="card competition-public-bracket"><div class="section-header"><div><h2>Турнирная сетка</h2><p class="muted">Промежуточные результаты и ссылки на каждую пару.</p></div><Trophy :size="22" /></div><div v-if="!publicBracketColumns.length" class="empty-row">Сетка появится после запуска турнира.</div><div v-else class="competition-public-bracket-columns"><section v-for="column in publicBracketColumns" :key="column.key" class="competition-public-bracket-column"><h3>{{ column.label }}</h3><div v-for="match in column.matches" :key="match.id" class="competition-public-bracket-match" :class="{ 'is-closed': match.status === 'closed' }"><div class="competition-match-head"><span class="muted">{{ match.status === 'open' ? 'Открыта' : match.status === 'bye' ? 'Автопроход' : 'Завершена' }}</span><span v-if="match.stage === 'group'" class="muted">{{ `Группа ${match.group}` }}</span></div><strong>{{ match.a?.name || '—' }} — {{ match.b?.name || 'автопроход' }}</strong><span class="muted">{{ match.votes_a }} : {{ match.votes_b }}{{ match.winner_name ? ` · ${match.winner_name}` : '' }}</span><a class="button small" :href="publicUrl(publicMatchPath(match))" target="_blank" rel="noopener noreferrer">Открыть пару</a></div></section></div></article>
        <article v-if="publicOpenMatches.length" class="competition-public-matches"><h2>Открытые пары</h2><article v-for="match in publicOpenMatches" :key="match.id" class="card competition-public-match"><div class="competition-match-head"><span class="pill">{{ match.stage === 'group' ? `Группа ${match.group}` : `Раунд ${match.round}` }}</span><span class="muted">Голосование открыто</span></div><div class="competition-duel"><button class="competition-duel-side" :class="{ 'is-selected': hasMyMatchVote(match, match.a) }" type="button" :disabled="!match.a || viewer.status !== 'in-progress' || voting" @click="submitVote(match.a?.id, match.id)"><div class="competition-images large"><img v-for="image in (match.a?.images || [])" :key="image" :src="mediaUrl(image)" alt="" /><div v-if="!match.a?.images?.length" class="competition-image-empty">Нет изображения</div></div><strong>{{ match.a?.name || '—' }}</strong><span>{{ match.votes_a }} голосов<span v-if="hasMyMatchVote(match, match.a)"> · Ваш выбор</span></span></button><b>VS</b><button class="competition-duel-side" :class="{ 'is-selected': hasMyMatchVote(match, match.b) }" type="button" :disabled="!match.b || viewer.status !== 'in-progress' || voting" @click="submitVote(match.b?.id, match.id)"><div class="competition-images large"><img v-for="image in (match.b?.images || [])" :key="image" :src="mediaUrl(image)" alt="" /><div v-if="!match.b?.images?.length" class="competition-image-empty">Нет изображения</div></div><strong>{{ match.b?.name || 'Автопроход' }}</strong><span>{{ match.votes_b }} голосов<span v-if="hasMyMatchVote(match, match.b)"> · Ваш выбор</span></span></button></div></article></article>
        </div>
      </template>
      <article v-if="viewer.status === 'complete'" class="card competition-results-card"><h2>Итоги</h2><ol><li v-for="result in viewer.results" :key="result.participant_id"><strong>{{ viewer.participants.find((item) => item.id === result.participant_id)?.name || 'Участник' }}</strong><span>{{ result.votes }} голосов</span></li></ol></article>
    </template>
  </section>
  <div v-if="imageViewer" class="competition-image-viewer" role="dialog" aria-modal="true" :aria-label="imageViewer.title" @click.self="closeImageViewer">
    <div class="competition-image-viewer-backdrop" aria-hidden="true" @click="closeImageViewer"></div>
    <article class="competition-image-viewer-dialog" @click.stop>
      <header class="competition-image-viewer-toolbar">
        <strong>{{ imageViewer.title }}</strong>
        <button type="button" class="icon-button" aria-label="Закрыть просмотр" title="Закрыть" @click="closeImageViewer"><X :size="18" /></button>
      </header>
      <div class="competition-image-viewer-stage">
        <button type="button" class="icon-button competition-image-viewer-nav" aria-label="Предыдущее изображение" title="Предыдущее изображение" :disabled="!imageViewerHasPrevious" @click="shiftImageViewer(-1)"><ChevronLeft :size="22" /></button>
        <img :src="imageViewerImage" :alt="imageViewer.title" />
        <button type="button" class="icon-button competition-image-viewer-nav" aria-label="Следующее изображение" title="Следующее изображение" :disabled="!imageViewerHasNext" @click="shiftImageViewer(1)"><ChevronRight :size="22" /></button>
      </div>
      <footer class="competition-image-viewer-caption">{{ imageViewer.index + 1 }} / {{ imageViewer.images.length }} · Нажмите Esc для закрытия</footer>
    </article>
  </div>
</template>

<style scoped>
.competition-layout { display:grid; grid-template-columns:minmax(250px, 320px) minmax(0,1fr); gap:var(--layout-gap); align-items:start; }
.competition-sidebar,.competition-workspace { display:grid; gap:var(--layout-gap); min-width:0; }
.competition-create,.competition-settings-card,.competition-add-participant { display:grid; gap:12px; }
.competition-advancing-places { display:grid; gap:10px; margin:0; padding:12px; border:1px solid var(--border); border-radius:var(--control-radius); color:var(--text); }
.competition-advancing-places legend { padding:0 5px; color:var(--muted); font-size:var(--small-text-size); font-weight:800; }
.competition-place-options { display:flex; flex-wrap:wrap; gap:8px; }
.competition-place-options label { display:inline-flex; align-items:center; gap:7px; padding:7px 9px; border:1px solid var(--border); border-radius:var(--control-radius); background:var(--panel-muted); color:var(--text); font-size:var(--small-text-size); font-weight:750; cursor:pointer; }
.competition-place-options label:has(input:checked) { border-color:var(--accent); background:color-mix(in srgb,var(--accent) 10%,var(--panel)); }
.competition-place-options input { accent-color:var(--accent); }
.competition-list { display:grid; gap:8px; margin-top:18px; }
.competition-list-item { display:flex; align-items:center; justify-content:space-between; gap:12px; width:100%; padding:12px; border:1px solid var(--border); border-radius:var(--control-radius); background:var(--panel-muted); color:var(--text); text-align:left; cursor:pointer; transition:transform 150ms ease,border-color 150ms ease,background 150ms ease; }
.competition-list-item:hover,.competition-list-item:focus-visible { border-color:var(--accent); transform:translateY(-1px); }
.competition-list-item.is-selected { border-color:var(--accent); background:color-mix(in srgb,var(--accent) 12%,var(--panel)); }
.competition-list-item span { display:grid; gap:3px; min-width:0; }.competition-list-item small { color:var(--muted); }
.competition-card-head { display:flex; align-items:center; justify-content:space-between; gap:18px; }.competition-card-head h2 { margin:8px 0 2px; }.competition-head-actions { display:flex; flex-wrap:wrap; gap:8px; justify-content:flex-end; }
.competition-participants-card,.competition-bracket-card,.competition-results-card { display:grid; gap:16px; }.competition-add-participant { grid-template-columns:minmax(0,1fr) auto; }
.competition-participant-grid,.competition-public-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(190px,1fr)); gap:14px; }.competition-participant-card,.competition-public-card { display:grid; gap:10px; align-content:start; min-width:0; }.competition-participant-card strong,.competition-public-card h2 { margin:0; }
.competition-images { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:5px; min-height:86px; position:relative; }.competition-images.large { min-height:150px; }.competition-images img { width:100%; height:100px; object-fit:cover; border-radius:var(--control-radius); background:var(--panel-muted); }.competition-images.large img { height:150px; }.competition-image { position:relative; min-width:0; }.competition-image button { position:absolute; top:4px; right:4px; padding:3px; border:0; border-radius:50%; background:var(--panel); color:var(--danger); cursor:pointer; }.competition-image-add { display:grid; place-items:center; min-height:100px; border:1px dashed var(--border); border-radius:var(--control-radius); color:var(--muted); cursor:pointer; }.competition-image-add:hover { color:var(--accent); border-color:var(--accent); }.competition-image-add input { display:none; }.competition-image-empty { display:grid; place-items:center; min-height:86px; border:1px dashed var(--border); border-radius:var(--control-radius); color:var(--muted); font-size:var(--small-text-size); }
.competition-participant-name { min-height:var(--input-height); padding:8px 10px; border:1px solid var(--border); border-radius:var(--control-radius); background:var(--panel-muted); color:var(--text); }.competition-match-list { display:grid; gap:8px; }.competition-match-row { display:grid; grid-template-columns:90px minmax(0,1fr) auto auto; gap:10px; align-items:center; padding:10px; border:1px solid var(--border); border-radius:var(--control-radius); }.competition-results-card ol { display:grid; gap:8px; margin:0; padding-left:24px; }.competition-results-card li { display:flex; justify-content:space-between; gap:12px; padding:10px; background:var(--panel-muted); border-radius:var(--control-radius); }
 .competition-empty { min-height:260px; display:grid; place-items:center; align-content:center; gap:8px; text-align:center; }.competition-viewer-page { max-width:1100px; margin:0 auto; }.competition-viewer-head { margin-bottom:var(--layout-gap); }.competition-viewer-head h1 { margin:10px 0 4px; }.competition-captcha { display:flex; align-items:end; justify-content:space-between; gap:16px; margin-bottom:var(--layout-gap); }.competition-public-card { text-align:center; }.competition-public-card .competition-images { text-align:left; }.competition-vote-count { color:var(--primary-strong); }.competition-public-overview { display:grid; gap:var(--layout-gap); }.competition-public-roster,.competition-public-bracket { display:grid; gap:16px; }.competition-public-roster-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:12px; }.competition-public-roster-item { display:grid; gap:8px; min-width:0; text-align:center; }.competition-images.roster { min-height:110px; }.competition-images.roster img { height:110px; }.competition-public-bracket-columns { display:flex; align-items:flex-start; gap:14px; overflow-x:auto; padding:2px 2px 8px; }.competition-public-bracket-column { display:grid; align-content:start; gap:10px; min-width:220px; flex:1 0 220px; }.competition-public-bracket-column h3 { margin:0; color:var(--muted); font-size:var(--small-text-size); text-transform:uppercase; letter-spacing:.06em; }.competition-public-bracket-match { display:grid; gap:7px; padding:12px; border:1px solid var(--border); border-radius:var(--control-radius); background:var(--panel-muted); }.competition-public-bracket-match.is-closed { border-color:color-mix(in srgb,var(--success) 55%,var(--border)); }.competition-public-bracket-match strong { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.competition-public-matches { display:grid; gap:14px; }.competition-public-matches > h2 { margin:0; }.competition-public-match { display:grid; gap:14px; }.competition-public-match.is-closed { border-color:color-mix(in srgb,var(--success) 55%,var(--border)); }.competition-match-head { display:flex; align-items:center; justify-content:space-between; gap:12px; }.competition-duel { display:grid; grid-template-columns:minmax(0,1fr) auto minmax(0,1fr); gap:18px; align-items:center; }.competition-duel > b { display:grid; place-items:center; width:56px; height:56px; border-radius:50%; background:var(--accent); color:white; }.competition-duel-side { display:grid; gap:8px; min-width:0; padding:12px; border:1px solid var(--border); border-radius:var(--card-radius); background:var(--panel-muted); color:var(--text); cursor:pointer; text-align:center; }.competition-duel-side:hover:not(:disabled),.competition-duel-side:focus-visible:not(:disabled) { border-color:var(--accent); transform:translateY(-2px); }.competition-duel-side:disabled { cursor:not-allowed; opacity:.72; }
@media (max-width:800px) { .competition-layout { grid-template-columns:1fr; }.competition-card-head,.competition-captcha { align-items:stretch; flex-direction:column; }.competition-head-actions { justify-content:flex-start; }.competition-match-row { grid-template-columns:1fr; }.competition-duel { grid-template-columns:1fr; }.competition-duel > b { margin:auto; }.competition-images.large img { height:120px; } }

.competition-viewer-head { padding: clamp(20px, 3vw, 34px); border: 1px solid var(--border); border-radius: var(--card-radius); background: linear-gradient(135deg, color-mix(in srgb, var(--primary) 10%, var(--panel)), var(--panel)); box-shadow: var(--shadow); }
.competition-viewer-kicker,.competition-viewer-title-row,.competition-public-card-top,.competition-public-score-row,.competition-pair-toolbar { display:flex; align-items:center; justify-content:space-between; gap:12px; }
.competition-viewer-eyebrow,.competition-captcha-kicker { display:inline-flex; align-items:center; gap:7px; color:var(--primary-strong); font-size:var(--small-text-size); font-weight:850; letter-spacing:.08em; text-transform:uppercase; }
.competition-viewer-status,.competition-match-state { display:inline-flex; align-items:center; gap:7px; color:var(--muted); font-size:var(--small-text-size); font-weight:750; }
.competition-viewer-status i,.competition-match-state i { display:block; width:7px; height:7px; border-radius:50%; background:var(--muted); }
.competition-viewer-status.is-in-progress,.competition-match-state.is-open { color:var(--success); }.competition-viewer-status.is-in-progress i,.competition-match-state.is-open i { background:var(--success); box-shadow:0 0 0 4px color-mix(in srgb,var(--success) 14%,transparent); }.competition-viewer-status.is-complete,.competition-match-state.is-closed { color:var(--primary-strong); }.competition-viewer-status.is-complete i,.competition-match-state.is-closed i { background:var(--primary); }
.competition-viewer-title-row { align-items:end; margin-top:10px; }.competition-viewer-title-row h1 { margin:0; letter-spacing:-.025em; }.competition-viewer-total { display:inline-flex; align-items:center; gap:6px; padding:8px 11px; border:1px solid var(--border); border-radius:999px; background:var(--panel-muted); color:var(--primary-strong); font-size:var(--small-text-size); font-weight:850; white-space:nowrap; }
.competition-captcha { display:grid; grid-template-columns:minmax(0,1fr) minmax(220px,300px); align-items:end; padding:18px 20px; border-color:color-mix(in srgb,var(--accent) 32%,var(--border)); background:color-mix(in srgb,var(--accent) 5%,var(--panel)); }.competition-captcha-copy { display:grid; gap:5px; }.competition-captcha-copy strong { font-size:var(--h3-size); }.competition-captcha-field { margin:0; }.competition-captcha-field input { text-align:center; font-weight:850; letter-spacing:.08em; }
.competition-public-grid { align-items:stretch; gap:18px; }.competition-public-card { position:relative; overflow:hidden; padding:16px; border-color:var(--border); background:linear-gradient(180deg,var(--panel),color-mix(in srgb,var(--panel-muted) 65%,var(--panel))); text-align:left; transition:transform 180ms ease,border-color 180ms ease,box-shadow 180ms ease; }.competition-public-card:hover { border-color:color-mix(in srgb,var(--accent) 60%,var(--border)); box-shadow:0 16px 34px color-mix(in srgb,var(--primary) 14%,transparent); transform:translateY(-3px); }.competition-public-card.is-leading { border-color:color-mix(in srgb,var(--accent) 68%,var(--border)); box-shadow:inset 0 2px 0 var(--accent),var(--shadow); }.competition-public-card-top { min-height:24px; }.competition-public-rank { color:var(--muted); font-size:var(--small-text-size); font-weight:850; letter-spacing:.08em; }.competition-leader-badge { padding:4px 8px; border-radius:999px; background:color-mix(in srgb,var(--accent) 14%,var(--panel)); color:var(--primary-strong); font-size:var(--tiny-text-size); font-weight:850; text-transform:uppercase; }
.competition-public-media { margin:10px 0 12px; }.competition-public-media .competition-images.large { min-height:170px; }.competition-public-media .competition-images.large img { height:170px; }.competition-public-media .competition-image-empty { min-height:170px; border:1px solid var(--border); background:var(--panel-muted); }.competition-public-media .competition-image-empty span { display:grid; width:56px; height:56px; place-items:center; border-radius:50%; background:var(--primary); color:var(--panel); font-size:var(--h3-size); font-weight:900; }
.competition-public-card-name { display:flex; align-items:center; gap:9px; min-width:0; }.competition-public-card-name h2 { overflow:hidden; margin:0; text-overflow:ellipsis; white-space:nowrap; }.competition-public-avatar { display:grid; flex:none; width:30px; height:30px; place-items:center; border-radius:50%; background:var(--panel-muted); color:var(--primary-strong); font-size:var(--tiny-text-size); font-weight:900; }
.competition-public-score-row { margin-top:13px; }.competition-vote-count { font-size:1.05rem; }.competition-public-score-row > span { color:var(--muted); font-size:var(--small-text-size); font-weight:800; }.competition-public-progress,.competition-pair-progress { height:6px; overflow:hidden; margin:8px 0 14px; border-radius:999px; background:var(--panel-muted); }.competition-public-progress span,.competition-pair-progress span { display:block; height:100%; min-width:0; border-radius:inherit; background:linear-gradient(90deg,var(--accent),var(--primary)); transition:width 260ms ease; }.competition-vote-button { width:100%; justify-content:center; }.competition-vote-button:active { transform:translateY(1px); }
.competition-pair-toolbar { align-items:flex-end; margin-bottom:2px; }.competition-pair-toolbar p { margin:6px 0 0; }.competition-back-link { display:inline-flex; align-items:center; gap:6px; color:var(--primary-strong); font-size:var(--small-text-size); font-weight:850; }.competition-back-link:hover,.competition-back-link:focus-visible { color:var(--accent); text-decoration:underline; text-underline-offset:3px; }.competition-public-match { padding:clamp(16px,3vw,26px); }.competition-public-match .competition-match-head { margin-bottom:4px; }.competition-duel-vs { display:grid; justify-items:center; gap:6px; }.competition-duel-vs span { display:grid; width:58px; height:58px; place-items:center; border:1px solid color-mix(in srgb,var(--accent) 42%,var(--border)); border-radius:50%; background:color-mix(in srgb,var(--accent) 12%,var(--panel)); color:var(--primary-strong); font-size:var(--small-text-size); font-weight:950; }.competition-duel-vs small { color:var(--muted); font-size:var(--tiny-text-size); font-weight:800; white-space:nowrap; }.competition-duel-side { min-height:258px; align-content:start; padding:14px; transition:transform 160ms ease,border-color 160ms ease,box-shadow 160ms ease,background 160ms ease; }.competition-duel-side:hover:not(:disabled),.competition-duel-side:focus-visible:not(:disabled) { border-color:var(--accent); background:color-mix(in srgb,var(--accent) 7%,var(--panel-muted)); box-shadow:var(--shadow); transform:translateY(-3px); }.competition-duel-side:active:not(:disabled) { transform:translateY(-1px); }.competition-duel-side:disabled { cursor:not-allowed; opacity:.62; }.competition-duel-side strong { font-size:var(--h3-size); }.competition-duel-side .competition-image-empty span { font-size:var(--h2-size); font-weight:900; }.competition-pair-progress { margin:20px 0 10px; }.competition-pair-result { display:flex; align-items:center; gap:7px; color:var(--success); font-size:var(--small-text-size); font-weight:850; }
.competition-empty { border:1px dashed var(--border); background:var(--panel); }
@media (max-width:800px) { .competition-viewer-title-row { align-items:flex-start; flex-direction:column; gap:8px; }.competition-captcha { grid-template-columns:1fr; }.competition-pair-toolbar { align-items:flex-start; flex-direction:column; }.competition-duel-side { min-height:200px; }.competition-duel-vs { order:0; }.competition-public-media .competition-images.large img,.competition-public-media .competition-images.large .competition-image-empty { height:130px; min-height:130px; } }
@media (prefers-reduced-motion:reduce) { .competition-public-card,.competition-duel-side,.competition-public-progress span,.competition-pair-progress span { transition:none; } }
.competition-images img { cursor:zoom-in; }
.competition-images img[role="button"]:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
.competition-image-viewer { position:fixed; inset:0; z-index:1000; display:grid; place-items:center; padding:clamp(12px,3vw,28px); }
.competition-image-viewer-backdrop { position:absolute; inset:0; width:100%; height:100%; border:0; background:color-mix(in srgb,var(--bg) 84%,transparent); backdrop-filter:blur(8px); cursor:default; }
.competition-image-viewer-dialog { position:relative; z-index:1; display:grid; grid-template-rows:auto minmax(0,1fr) auto; width:min(980px,100%); max-height:calc(100dvh - 40px); padding:14px; border:1px solid var(--border); border-radius:var(--card-radius); background:var(--panel); box-shadow:var(--shadow); }
.competition-image-viewer-toolbar { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:2px 2px 12px; color:var(--text); }
.competition-image-viewer-toolbar strong { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.competition-image-viewer-stage { display:grid; grid-template-columns:auto minmax(0,1fr) auto; align-items:center; gap:10px; min-height:0; }
.competition-image-viewer-stage img { display:block; width:100%; max-height:calc(100dvh - 160px); object-fit:contain; border-radius:var(--control-radius); background:var(--panel-muted); }
.competition-image-viewer-nav { flex:none; }
.competition-image-viewer-nav:disabled { opacity:.35; cursor:not-allowed; }
.competition-image-viewer-caption { padding:12px 2px 2px; color:var(--muted); font-size:var(--small-text-size); text-align:center; }
@media (max-width:600px) { .competition-image-viewer { padding:8px; }.competition-image-viewer-dialog { max-height:calc(100dvh - 16px); padding:10px; }.competition-image-viewer-stage { gap:4px; }.competition-image-viewer-stage img { max-height:calc(100dvh - 128px); }.competition-image-viewer-nav { padding:6px; } }

.competition-vote-list { display:grid; gap:14px; }
.competition-vote-list-item { position:relative; display:grid; grid-template-columns:44px minmax(220px,300px) minmax(0,1fr); align-items:center; gap:18px; overflow:hidden; padding:16px 18px 16px 14px; border:1px solid var(--border); background:linear-gradient(110deg,var(--panel),color-mix(in srgb,var(--panel-muted) 72%,var(--panel))); transition:transform 180ms ease,border-color 180ms ease,box-shadow 180ms ease; }
.competition-vote-list-item::before { position:absolute; inset:0 auto 0 0; width:3px; content:""; background:var(--border); }
.competition-vote-list-item:hover,.competition-vote-list-item:focus-within { border-color:color-mix(in srgb,var(--accent) 55%,var(--border)); box-shadow:var(--shadow); transform:translateY(-2px); }
.competition-vote-list-item.is-leading { border-color:color-mix(in srgb,var(--accent) 68%,var(--border)); box-shadow:inset 0 2px 0 var(--accent),var(--shadow); }
.competition-vote-list-item.is-leading::before { background:var(--accent); }
.competition-vote-list-rank { align-self:start; padding-top:5px; color:var(--muted); font-size:var(--h3-size); font-weight:950; letter-spacing:-.04em; text-align:center; }
.competition-vote-list-content { display:grid; gap:8px; min-width:0; }
.competition-vote-list-heading { display:flex; align-items:center; justify-content:space-between; gap:12px; min-width:0; }
.competition-vote-list-heading .competition-public-card-name { min-width:0; }
.competition-vote-list-heading .competition-leader-badge { flex:none; }
.competition-vote-list .competition-public-score-row { margin-top:2px; }
.competition-vote-list .competition-vote-button { width:max-content; min-width:170px; }
.competition-carousel { position:relative; display:grid; grid-template-columns:auto minmax(0,1fr) auto; align-items:center; gap:8px; min-width:0; }
.competition-carousel-vote { min-height:178px; }
.competition-carousel-duel { min-height:220px; }
.competition-carousel-image { grid-column:2; display:block; width:100%; aspect-ratio:4 / 3; padding:0; overflow:hidden; border:1px solid var(--border); border-radius:var(--control-radius); background:var(--panel-muted); cursor:zoom-in; }
.competition-carousel-image:hover,.competition-carousel-image:focus-visible { border-color:var(--accent); box-shadow:0 10px 24px color-mix(in srgb,var(--primary) 14%,transparent); outline:none; }
.competition-carousel-image img { display:block; width:100%; height:100%; object-fit:cover; }
.competition-carousel-arrow { z-index:1; display:grid; flex:none; width:32px; height:32px; place-items:center; padding:0; border:1px solid var(--border); border-radius:50%; background:color-mix(in srgb,var(--panel) 86%,transparent); color:var(--text); cursor:pointer; transition:transform 150ms ease,border-color 150ms ease,background 150ms ease,color 150ms ease; }
.competition-carousel-arrow:hover,.competition-carousel-arrow:focus-visible { border-color:var(--accent); background:color-mix(in srgb,var(--accent) 12%,var(--panel)); color:var(--primary-strong); outline:none; transform:scale(1.06); }
.competition-carousel-arrow:active { transform:scale(.96); }
.competition-carousel-counter { position:absolute; right:50%; bottom:9px; z-index:2; transform:translateX(50%); padding:3px 8px; border:1px solid color-mix(in srgb,var(--border) 80%,transparent); border-radius:999px; background:color-mix(in srgb,var(--panel) 88%,transparent); color:var(--muted); font-size:var(--tiny-text-size); font-weight:850; line-height:1.1; pointer-events:none; }
.competition-carousel > .competition-image-empty { grid-column:1 / -1; width:100%; min-height:178px; border-style:solid; background:color-mix(in srgb,var(--panel-muted) 84%,var(--panel)); }
.competition-carousel-duel > .competition-image-empty { min-height:220px; }
.competition-duel-side { cursor:default; text-align:left; }
.competition-duel-side-header,.competition-duel-side-footer { display:flex; align-items:center; justify-content:space-between; gap:10px; min-width:0; }
.competition-duel-side-header > span:last-child { color:var(--muted); font-size:var(--small-text-size); font-weight:850; white-space:nowrap; }
.competition-duel-side-footer strong { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.competition-duel-vote { flex:none; justify-content:center; }
@media (max-width:900px) { .competition-vote-list-item { grid-template-columns:36px minmax(180px,240px) minmax(0,1fr); gap:14px; padding-right:14px; }.competition-carousel-vote { min-height:150px; }.competition-carousel-vote > .competition-image-empty { min-height:150px; } }
@media (max-width:600px) { .competition-vote-list-item { grid-template-columns:30px minmax(0,1fr); gap:8px 12px; padding:14px; }.competition-vote-list-rank { grid-row:1 / span 2; font-size:var(--h3-size); }.competition-vote-list-item .competition-carousel,.competition-vote-list-content { grid-column:2; }.competition-vote-list .competition-vote-button { width:100%; }.competition-carousel-duel { min-height:170px; }.competition-carousel-duel > .competition-image-empty { min-height:170px; }.competition-duel-side-header,.competition-duel-side-footer { align-items:flex-start; flex-direction:column; }.competition-duel-vote { width:100%; }.competition-carousel-arrow { width:30px; height:30px; } }
@media (prefers-reduced-motion:reduce) { .competition-vote-list-item,.competition-carousel-arrow,.competition-carousel-image { transition:none; } }
.competition-vote-list-heading-meta { display:flex; align-items:center; justify-content:flex-end; gap:8px; flex-wrap:wrap; }
.competition-vote-selection { padding:3px 8px; border:1px solid color-mix(in srgb,var(--success) 54%,var(--border)); border-radius:999px; background:color-mix(in srgb,var(--success) 12%,transparent); color:var(--success); font-size:var(--tiny-text-size); font-weight:850; white-space:nowrap; }
.competition-vote-list-item.is-selected { border-color:color-mix(in srgb,var(--success) 62%,var(--border)); box-shadow:inset 3px 0 0 var(--success),var(--shadow); }
.competition-duel-side.is-selected { border-color:color-mix(in srgb,var(--success) 66%,var(--border)); box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--success) 40%,transparent),var(--shadow); }
</style>
