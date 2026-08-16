<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight, ClipboardCheck, Eye, Flag, HeartHandshake, Mail, Maximize2, MessageCircle, Minimize2, Music2, PlayCircle, Plus, Radio, Send, ShieldCheck, Users, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import PaginationControls from '../components/PaginationControls.vue'
import { gameLabel, gameOptions, isExternalRace, raceOpenHref, statusLabel } from '../i18nLabels'
import { isVideoUrl } from '../media'
import { state } from '../store'
import { formatDayPart, formatInTimeZone, formatMonthPart, formatTimeOnly } from '../timezone'

const { t } = useI18n()
const stats = ref({ pilots: 0, completed_races: 0, open_races: 0, staff: 0 })
const races = ref([])
const setups = ref([])
const banners = ref([])
const news = ref([])
const registrationChampionships = ref([])
const donationSettings = ref({ donation_url: '', top_donations: [] })
const newsTrack = ref(null)
const activeNewsIndex = ref(0)
const isNewsViewerOpen = ref(false)
const isNewsTextHidden = ref(false)
const error = ref('')
const raceGameFilter = ref('all')
const raceStatusFilter = ref('not_finished')
const myGamesOnly = ref(false)
const racePage = ref(1)
const racePageSize = 5
const defaultTwitchStatus = {
  channel_login: 'bmrlracing',
  channel_url: 'https://www.twitch.tv/bmrlracing',
  is_configured: false,
  is_live: false,
  status: 'channel',
  embed_type: 'channel',
  embed_value: 'bmrlracing',
  external_url: 'https://www.twitch.tv/bmrlracing',
  title: '',
  game_name: '',
  thumbnail_url: '',
  viewer_count: null
}
const savedTwitchCollapsed = typeof localStorage === 'undefined' ? null : localStorage.getItem('twitchWidgetCollapsed')
const twitchStatus = ref({ ...defaultTwitchStatus })
const twitchError = ref('')
const isTwitchViewerOpen = ref(false)
const isTwitchCollapsed = ref(savedTwitchCollapsed === null ? true : savedTwitchCollapsed === 'true')
const twitchWidgetPosition = ref({ x: 24, y: 120 })
const twitchDragState = ref(null)
const twitchWasDragged = ref(false)
const twitchPreviewStartSecond = Math.floor(Math.random() * 900) + 15
const currentNews = computed(() => news.value[activeNewsIndex.value] || null)
const featuredChampionship = computed(() => registrationChampionships.value[0] || null)
const featuredChampionshipStageCount = computed(() => featuredChampionship.value?.stage_count ?? featuredChampionship.value?.stages?.length ?? 0)
const featuredChampionshipStageText = computed(() => stageCount(featuredChampionshipStageCount.value))
const featuredChampionshipRegistered = computed(() => featuredChampionship.value?.my_registration_status === 'approved')
const topDonations = computed(() => (donationSettings.value.top_donations || [])
  .filter((donation) => donation?.name || donation?.amount)
  .slice(0, 3))
const contactEmailLinks = [
  { text: 'dronzoll320@gmail.com', href: 'mailto:dronzoll320@gmail.com' },
  { text: '37foneziazaz0909@gmail.com', href: 'mailto:37foneziazaz0909@gmail.com' }
]
const directContactItems = computed(() => [
  {
    key: 'email',
    icon: Mail,
    label: t('main.contactMail'),
    links: contactEmailLinks
  },
  { key: 'discord-direct', icon: MessageCircle, label: t('main.contactDiscord'), value: 'pianino22' }
])
const socialItems = computed(() => [
  { key: 'discord-server', icon: Users, label: t('main.discordServer'), href: 'https://discord.gg/bmrlac', text: 'discord.gg/bmrlac' },
  { key: 'telegram', icon: Send, label: t('main.telegramChannel'), href: 'https://t.me/bmrlleague', text: '@bmrlleague' },
  { key: 'tiktok', icon: Music2, label: t('main.tiktok'), href: 'https://www.tiktok.com/@beamngrl', text: '@beamngrl' },
  { key: 'twitch', icon: Radio, label: 'Twitch', href: 'https://www.twitch.tv/bmrlracing', text: 'bmrlracing' }
])
const raceGameOptions = computed(() => gameOptions(t, true))
const canFilterMyGames = computed(() => Boolean(state.user?.games?.length))
const racesHasNextPage = computed(() => races.value.length === racePageSize)
const canEmbedTwitch = computed(() => {
  if (twitchStatus.value.is_live && twitchStatus.value.embed_type === 'channel') return true
  return twitchStatus.value.status === 'vod' && twitchStatus.value.embed_type === 'video' && Boolean(twitchStatus.value.embed_value)
})
const canEmbedTwitchPreview = computed(() => twitchStatus.value.is_live && canEmbedTwitch.value)
const twitchWidgetStyle = computed(() => ({
  transform: `translate3d(${twitchWidgetPosition.value.x}px, ${twitchWidgetPosition.value.y}px, 0)`
}))
const twitchParent = computed(() => (typeof window === 'undefined' ? 'localhost' : window.location.hostname))
const twitchEmbedSrc = computed(() => createTwitchEmbedSrc({ autoplay: twitchStatus.value.is_live }))
const twitchPreviewSrc = computed(() => createTwitchEmbedSrc({ preview: true }))

function formatTwitchTime(totalSeconds) {
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  return `${hours}h${minutes}m${seconds}s`
}

function createTwitchEmbedSrc({ autoplay = false, preview = false } = {}) {
  const params = new URLSearchParams({
    parent: twitchParent.value,
    muted: 'true',
    autoplay: autoplay ? 'true' : 'false',
  })
  if (twitchStatus.value.embed_type === 'video' && twitchStatus.value.embed_value) {
    params.set('video', twitchStatus.value.embed_value)
    if (preview) {
      params.set('time', formatTwitchTime(twitchPreviewStartSecond))
    }
  } else {
    params.set('channel', twitchStatus.value.channel_login || defaultTwitchStatus.channel_login)
  }
  return `https://player.twitch.tv/?${params.toString()}`
}
const twitchStatusText = computed(() => {
  if (twitchStatus.value.is_live) return t('twitch.live')
  if (twitchStatus.value.status === 'vod') return t('twitch.latestVideo')
  return t('twitch.channel')
})
const twitchDisplayTitle = computed(() => {
  if (twitchStatus.value.title) return twitchStatus.value.title
  if (twitchStatus.value.status === 'vod') return t('twitch.latestVideo')
  return t('twitch.channel')
})

function getTwitchWidgetSize() {
  if (typeof window === 'undefined') return 420
  return window.innerWidth <= 520 ? Math.max(280, window.innerWidth - 32) : 420
}

function getTwitchWidgetDimensions() {
  if (isTwitchCollapsed.value) return { width: 270, height: 58 }
  const width = getTwitchWidgetSize()
  return { width, height: Math.max(300, Math.round(width * 0.76)) }
}

function banner(position) {
  return banners.value.find((item) => item.position === position && item.image_url)
}

function formatRaceDate(value) {
  return formatInTimeZone(value, {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23'
  })
}

function formatRaceDay(value) {
  return formatDayPart(value)
}

function formatRaceMonth(value) {
  return formatMonthPart(value)
}

function formatRaceTime(value) {
  return formatTimeOnly(value)
}

function stagePluralSuffix(count) {
  if (state.locale !== 'ru') return count === 1 ? 'One' : 'Many'
  const mod10 = count % 10
  const mod100 = count % 100
  if (mod10 === 1 && mod100 !== 11) return 'One'
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return 'Few'
  return 'Many'
}

function stageCount(count) {
  return `${count} ${t(`championships.stageWord${stagePluralSuffix(count)}`)}`
}

function registeredCount(race) {
  if (race.game === 'LMU') return 0
  return race.registered_pilots?.length || 0
}

function isRaceRegistered(race) {
  if (race.game === 'LMU') return false
  return Boolean(state.user && race.registered_pilots?.some((item) => item.user_id === state.user.id))
}

function fillPercent(race) {
  if (race.game === 'LMU') return 0
  if (!race.max_pilots) return 0
  return Math.min(100, Math.round((registeredCount(race) / race.max_pilots) * 100))
}

function clampNewsIndex(index) {
  if (!news.value.length) return 0
  return Math.min(Math.max(index, 0), news.value.length - 1)
}

function goToNews(index, behavior = 'smooth') {
  const nextIndex = clampNewsIndex(index)
  activeNewsIndex.value = nextIndex
  const track = newsTrack.value
  if (!track) return
  track.scrollTo({
    left: nextIndex * track.clientWidth,
    behavior
  })
}

function scrollNews(direction) {
  goToNews(activeNewsIndex.value + direction)
}

function syncNewsIndex() {
  const track = newsTrack.value
  if (!track || !track.clientWidth) return
  activeNewsIndex.value = clampNewsIndex(Math.round(track.scrollLeft / track.clientWidth))
}

function openNews(index) {
  goToNews(index, 'auto')
  isNewsTextHidden.value = false
  isNewsViewerOpen.value = true
}

function closeNewsViewer() {
  isNewsViewerOpen.value = false
  isNewsTextHidden.value = false
}

function moveNewsFromViewer(direction) {
  goToNews(activeNewsIndex.value + direction)
}

function handleNewsKeydown(event) {
  if (event.key === 'Escape' && isTwitchViewerOpen.value) {
    event.preventDefault()
    closeTwitchViewer()
    return
  }
  if (!isNewsViewerOpen.value) return
  if (event.key === 'Escape') {
    event.preventDefault()
    closeNewsViewer()
    return
  }
  if (event.key === 'ArrowLeft') {
    event.preventDefault()
    moveNewsFromViewer(-1)
    return
  }
  if (event.key === 'ArrowRight') {
    event.preventDefault()
    moveNewsFromViewer(1)
  }
}

async function loadRaces() {
  const params = new URLSearchParams({
    limit: String(racePageSize),
    offset: String((racePage.value - 1) * racePageSize),
    game_filter: raceGameFilter.value,
    status_filter: raceStatusFilter.value
  })
  if (myGamesOnly.value && canFilterMyGames.value) {
    params.set('my_games_only', 'true')
  }
  races.value = await api(`/races?${params.toString()}`)
}

async function resetRacePageAndLoad() {
  if (racePage.value === 1) {
    await loadRaces()
    return
  }
  racePage.value = 1
}

async function loadTwitchStatus() {
  try {
    twitchStatus.value = { ...defaultTwitchStatus, ...(await api('/twitch/status')) }
    twitchError.value = ''
  } catch (err) {
    twitchStatus.value = { ...defaultTwitchStatus }
    twitchError.value = err.message
  }
}

function openTwitchViewer() {
  isTwitchViewerOpen.value = true
}

function closeTwitchViewer() {
  isTwitchViewerOpen.value = false
}

function clampTwitchWidgetPosition(position = twitchWidgetPosition.value) {
  if (typeof window === 'undefined') return position
  const size = getTwitchWidgetDimensions()
  const margin = 16
  const maxX = Math.max(margin, window.innerWidth - size.width - margin)
  const maxY = Math.max(margin, window.innerHeight - size.height - margin)
  const nextPosition = {
    x: Math.min(Math.max(margin, position.x), maxX),
    y: Math.min(Math.max(margin, position.y), maxY)
  }
  twitchWidgetPosition.value = nextPosition
  return nextPosition
}

function placeTwitchWidget() {
  if (typeof window === 'undefined') return
  const size = getTwitchWidgetDimensions()
  const margin = 16
  clampTwitchWidgetPosition({
    x: window.innerWidth - size.width - margin,
    y: window.innerHeight - size.height - margin
  })
}

function handleTwitchResize() {
  clampTwitchWidgetPosition()
}

function startTwitchDrag(event) {
  if (event.button !== undefined && event.button !== 0) return
  twitchDragState.value = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    baseX: twitchWidgetPosition.value.x,
    baseY: twitchWidgetPosition.value.y
  }
  try {
    event.currentTarget.setPointerCapture?.(event.pointerId)
  } catch {
    // Pointer capture can fail for synthetic events; dragging still works through window listeners.
  }
  window.addEventListener('pointermove', dragTwitchWidget)
  window.addEventListener('pointerup', stopTwitchDrag, { once: true })
}

function dragTwitchWidget(event) {
  const drag = twitchDragState.value
  if (!drag || drag.pointerId !== event.pointerId) return
  const dx = event.clientX - drag.startX
  const dy = event.clientY - drag.startY
  if (Math.abs(dx) + Math.abs(dy) > 5) {
    twitchWasDragged.value = true
  }
  clampTwitchWidgetPosition({ x: drag.baseX + dx, y: drag.baseY + dy })
}

function stopTwitchDrag() {
  twitchDragState.value = null
  window.removeEventListener('pointermove', dragTwitchWidget)
}

function openTwitchFromWidget() {
  if (twitchWasDragged.value) {
    twitchWasDragged.value = false
    return
  }
  openTwitchViewer()
}

function toggleTwitchCollapsed(event) {
  event?.stopPropagation()
  isTwitchCollapsed.value = !isTwitchCollapsed.value
  localStorage.setItem('twitchWidgetCollapsed', isTwitchCollapsed.value ? 'true' : 'false')
  requestAnimationFrame(() => clampTwitchWidgetPosition())
}

onMounted(async () => {
  window.addEventListener('keydown', handleNewsKeydown)
  window.addEventListener('resize', handleTwitchResize)
  placeTwitchWidget()
  loadTwitchStatus()
  try {
    const [statsData, setupsData, bannerData, newsData, championshipData, donationData] = await Promise.all([
      api('/dashboard/stats'),
      api('/setups?limit=6'),
      api('/banners'),
      api('/news'),
      api('/championships?status_filter=registration_open&limit=3'),
      api('/app-settings/donations')
    ])
    stats.value = statsData
    setups.value = setupsData
    banners.value = bannerData
    news.value = newsData
    registrationChampionships.value = championshipData
    donationSettings.value = donationData
    activeNewsIndex.value = 0
    await loadRaces()
  } catch (err) {
    error.value = err.message
  }
})

watch(racePage, async () => {
  try {
    await loadRaces()
  } catch (err) {
    error.value = err.message
  }
})

watch([raceGameFilter, raceStatusFilter, myGamesOnly], async () => {
  try {
    await resetRacePageAndLoad()
  } catch (err) {
    error.value = err.message
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleNewsKeydown)
  window.removeEventListener('resize', handleTwitchResize)
  window.removeEventListener('pointermove', dragTwitchWidget)
})
</script>

<template>
  <div class="main-menu">
    <a v-if="banner('top')" class="banner main-menu-top-banner" :href="banner('top').link_url">
      <video v-if="isVideoUrl(banner('top').image_url)" :src="banner('top').image_url" autoplay muted loop playsinline preload="metadata"></video>
      <img v-else :src="banner('top').image_url" alt="" />
    </a>

    <div class="main-menu-layout">
      <a v-if="banner('left')" class="banner side main-menu-side-banner left" :href="banner('left').link_url">
        <video v-if="isVideoUrl(banner('left').image_url)" :src="banner('left').image_url" autoplay muted loop playsinline preload="metadata"></video>
        <img v-else :src="banner('left').image_url" alt="" />
      </a>

      <div class="main-menu-content">
        <section v-if="news.length" class="section news-strip main-news-strip">
          <div ref="newsTrack" class="news-track" @scroll="syncNewsIndex">
            <article
              v-for="(item, index) in news"
              :key="item.id"
              class="news-card"
              role="button"
              tabindex="0"
              :aria-label="t('news.openFullscreen')"
              @click="openNews(index)"
              @keydown.enter.prevent="openNews(index)"
              @keydown.space.prevent="openNews(index)"
            >
              <video v-if="isVideoUrl(item.image_url)" :src="item.image_url" autoplay muted loop playsinline preload="metadata"></video>
              <img v-else :src="item.image_url" alt="" />
              <div class="news-card-topline">
                <span>{{ t('news.title') }}</span>
                <span>{{ index + 1 }} / {{ news.length }}</span>
              </div>
              <span class="news-card-open"><Maximize2 :size="16" /></span>
              <div class="news-card-content">
                <h3>{{ item.title }}</h3>
                <p>{{ item.body }}</p>
              </div>
            </article>
          </div>
          <button v-if="news.length > 1" class="icon-button news-strip-nav prev" type="button" :title="t('news.scrollLeft')" @click.stop="scrollNews(-1)">
            <ChevronLeft :size="22" />
          </button>
          <button v-if="news.length > 1" class="icon-button news-strip-nav next" type="button" :title="t('news.scrollRight')" @click.stop="scrollNews(1)">
            <ChevronRight :size="22" />
          </button>
          <div v-if="news.length > 1" class="news-dots" :aria-label="t('news.indicators')">
            <button
              v-for="(_, index) in news"
              :key="index"
              class="news-dot"
              :class="{ 'is-active': index === activeNewsIndex }"
              type="button"
              :title="t('news.goTo', { number: index + 1 })"
              @click="goToNews(index)"
            >
              <span class="visually-hidden">{{ t('news.goTo', { number: index + 1 }) }}</span>
            </button>
          </div>
        </section>

        <section class="section main-overview-section">
          <div class="grid cols-4 main-stat-grid">
            <div class="card stat main-stat-card main-stat-card--pilots">
              <span class="main-stat-icon"><Users :size="22" /></span>
              <span class="muted">{{ t('main.pilots') }}</span>
              <strong>{{ stats.pilots }}</strong>
            </div>
            <div class="card stat main-stat-card main-stat-card--completed">
              <span class="main-stat-icon"><Flag :size="22" /></span>
              <span class="muted">{{ t('main.completed') }}</span>
              <strong>{{ stats.completed_races }}</strong>
            </div>
            <div class="card stat main-stat-card main-stat-card--open">
              <span class="main-stat-icon"><ClipboardCheck :size="22" /></span>
              <span class="muted">{{ t('main.open') }}</span>
              <strong>{{ stats.open_races }}</strong>
            </div>
            <div class="card stat main-stat-card main-stat-card--staff">
              <span class="main-stat-icon"><ShieldCheck :size="22" /></span>
              <span class="muted">{{ t('main.staff') }}</span>
              <strong>{{ stats.staff }}</strong>
            </div>
          </div>
        </section>

        <p v-if="error" class="error">{{ error }}</p>

        <RouterLink v-if="featuredChampionship" class="card main-championship-callout" to="/championships">
          <span class="main-championship-icon"><Flag :size="20" /></span>
          <span>
            <small>{{ t('main.championshipOpen') }}</small>
            <strong>{{ featuredChampionship.name }}</strong>
          </span>
          <span class="main-championship-meta">
            <span class="pill">{{ featuredChampionship.game }}</span>
            <span class="pill">{{ featuredChampionshipStageText }}</span>
            <span v-if="featuredChampionshipRegistered" class="pill is-registered">{{ t('championships.requestApproved') }}</span>
          </span>
        </RouterLink>

        <section class="section main-races-section">
          <div class="section-header main-races-header">
            <h2>{{ t('main.races') }}</h2>
            <RouterLink v-if="['admin', 'moder'].includes(state.user?.role)" class="button primary" to="/races/new"><Plus :size="16" />{{ t('common.create') }}</RouterLink>
          </div>
          <div class="race-filter-bar main-race-filter-bar card">
            <div class="race-status-toggle" role="group" :aria-label="t('raceFilters.statusGroup')">
              <button type="button" :class="{ active: raceStatusFilter === 'not_finished' }" @click="raceStatusFilter = 'not_finished'">
                {{ t('raceFilters.notFinished') }}
              </button>
              <button type="button" :class="{ active: raceStatusFilter === 'finished' }" @click="raceStatusFilter = 'finished'">
                {{ t('raceFilters.finished') }}
              </button>
            </div>
            <label class="field race-game-filter">
              <span class="visually-hidden">{{ t('fields.game') }}</span>
              <select v-model="raceGameFilter" :aria-label="t('fields.game')">
                <option v-for="option in raceGameOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
              </select>
            </label>
            <label class="toggle-field">
              <input v-model="myGamesOnly" type="checkbox" :disabled="!canFilterMyGames" />
              <span>{{ t('raceFilters.myGamesOnly') }}</span>
            </label>
          </div>
          <div class="main-race-grid">
            <article v-for="race in races" :key="race.id" class="card main-race-card">
              <div class="main-race-date-tile">
                <strong>{{ formatRaceDay(race.datetime_start) }}</strong>
                <span>{{ formatRaceMonth(race.datetime_start) }}</span>
                <small>{{ formatRaceTime(race.datetime_start) }}</small>
              </div>

              <div class="main-race-card-main">
                <div class="main-race-card-head">
                  <div class="main-race-title">
                    <a v-if="isExternalRace(race)" :href="raceOpenHref(race)">{{ race.name }}</a>
                    <RouterLink v-else :to="raceOpenHref(race)">{{ race.name }}</RouterLink>
                    <p class="muted main-race-subtitle">
                      <span>{{ gameLabel(t, race.game) }}</span>
                      <span v-if="race.track">{{ race.track }}</span>
                      <span v-if="race.car_class">{{ race.car_class }}</span>
                    </p>
                  </div>
                </div>

                <div class="main-race-meta">
                  <span>
                    <small>{{ t('fields.date') }}</small>
                    <strong>{{ formatRaceDate(race.datetime_start) }}</strong>
                  </span>
                  <span v-if="race.game !== 'LMU'">
                    <small>{{ t('fields.participants') }}</small>
                    <strong>{{ registeredCount(race) }} / {{ race.max_pilots }}</strong>
                  </span>
                </div>

                <span v-if="race.game !== 'LMU'" class="race-registration-meter">
                  <span :style="{ width: `${fillPercent(race)}%` }"></span>
                </span>
              </div>

              <div class="main-race-action-panel">
                <span v-if="isRaceRegistered(race)" class="status-badge main-registered-badge">{{ t('main.registeredForRace') }}</span>
                <span class="status-badge race-status-badge" :class="`race-status-${race.status}`">{{ statusLabel(t, race.status) }}</span>
                <span v-if="race.game !== 'LMU'" class="main-race-fill">{{ fillPercent(race) }}%</span>
                <a v-if="isExternalRace(race)" class="button main-race-open" :href="raceOpenHref(race)">
                  <Eye :size="16" />
                  {{ t('common.open') }}
                </a>
                <RouterLink v-else class="button main-race-open" :to="raceOpenHref(race)">
                  <Eye :size="16" />
                  {{ t('common.open') }}
                </RouterLink>
              </div>
            </article>
          </div>
          <PaginationControls v-model:page="racePage" :page-size="racePageSize" :loaded-count="races.length" :has-next="racesHasNextPage" />
        </section>

        <section class="section main-setups-section">
          <div class="section-header"><h2>{{ t('main.setups') }}</h2></div>
          <div class="grid cols-2 main-setup-grid">
            <article v-for="setup in setups" :key="setup.id" class="card main-setup-card">
              <strong>{{ setup.car_model }}</strong>
              <p class="muted">{{ setup.description || setup.setup_data }}</p>
            </article>
          </div>
        </section>

      </div>

      <a v-if="banner('right')" class="banner side main-menu-side-banner right" :href="banner('right').link_url">
        <video v-if="isVideoUrl(banner('right').image_url)" :src="banner('right').image_url" autoplay muted loop playsinline preload="metadata"></video>
        <img v-else :src="banner('right').image_url" alt="" />
      </a>
    </div>

    <a v-if="banner('bottom')" class="banner main-menu-bottom-banner" :href="banner('bottom').link_url">
      <video v-if="isVideoUrl(banner('bottom').image_url)" :src="banner('bottom').image_url" autoplay muted loop playsinline preload="metadata"></video>
      <img v-else :src="banner('bottom').image_url" alt="" />
    </a>

    <section class="section main-menu-floor">
      <div class="main-menu-floor-inner">
        <div class="main-menu-floor-main">
          <div class="main-footer-column main-footer-column-primary">
            <strong class="main-footer-title">{{ t('main.contacts') }}</strong>
            <p>{{ t('main.contactSubtitle') }}</p>
            <div class="main-footer-list">
              <div v-for="item in directContactItems" :key="item.key" class="main-footer-contact-group">
                <span class="main-footer-label"><component :is="item.icon" :size="15" />{{ item.label }}</span>
                <span v-if="item.links" class="main-footer-link-stack">
                  <a v-for="link in item.links" :key="link.href" :href="link.href">{{ link.text }}</a>
                </span>
                <span v-else class="main-footer-value">{{ item.value }}</span>
              </div>
            </div>
          </div>

          <div class="main-footer-column">
            <strong class="main-footer-column-title">{{ t('main.community') }}</strong>
            <div class="main-social-list">
              <a v-for="item in socialItems" :key="item.key" class="main-social-link" :href="item.href" target="_blank" rel="noreferrer">
                <span><component :is="item.icon" :size="16" /></span>
                <span>
                  <b>{{ item.label }}</b>
                  <em>{{ item.text }}</em>
                </span>
              </a>
            </div>
          </div>
        </div>

        <aside class="main-menu-support" :aria-label="t('main.supportProject')">
          <div class="main-support-copy">
            <strong>{{ t('main.supportProject') }}</strong>
            <span>{{ t('main.supportHint') }}</span>
          </div>
          <a v-if="donationSettings.donation_url" class="button primary main-support-button" :href="donationSettings.donation_url" target="_blank" rel="noreferrer">
            <HeartHandshake :size="16" />
            {{ t('main.supportProject') }}
          </a>
          <div class="main-donations-card">
            <span class="main-donations-title">{{ t('main.topDonations') }}</span>
            <div class="main-donations-top">
              <span v-if="!topDonations.length" class="muted">{{ t('main.noTopDonations') }}</span>
              <span v-for="donation in topDonations" :key="`${donation.name}-${donation.amount}`" class="main-donation-chip">
                <span class="main-donation-copy">
                  <b>{{ donation.name }}</b>
                  <small>{{ donation.message || t('main.donationCommentSpace') }}</small>
                </span>
                <em>{{ donation.amount }}</em>
              </span>
            </div>
          </div>
        </aside>
      </div>
    </section>
  </div>

  <Teleport to="body">
    <div
      class="twitch-floating-widget"
      :class="{ 'is-collapsed': isTwitchCollapsed }"
      role="button"
      tabindex="0"
      :style="twitchWidgetStyle"
      :title="t('twitch.dragHint')"
      @click="openTwitchFromWidget"
      @keydown.enter.prevent="openTwitchViewer"
      @keydown.space.prevent="openTwitchViewer"
      @pointerdown="startTwitchDrag"
    >
      <span class="twitch-floating-head">
        <Radio :size="14" />
        <span class="status-badge twitch-status" :class="{ 'is-live': twitchStatus.is_live, 'is-vod': twitchStatus.status === 'vod' }">{{ twitchStatusText }}</span>
        <button
          class="icon-button twitch-collapse-button"
          type="button"
          :title="isTwitchCollapsed ? t('twitch.expandWidget') : t('twitch.collapseWidget')"
          :aria-label="isTwitchCollapsed ? t('twitch.expandWidget') : t('twitch.collapseWidget')"
          @click.stop="toggleTwitchCollapsed"
          @pointerdown.stop
        >
          <Maximize2 v-if="isTwitchCollapsed" :size="14" />
          <Minimize2 v-else :size="14" />
        </button>
      </span>
      <span v-if="!isTwitchCollapsed" class="twitch-floating-preview">
        <iframe
          v-if="canEmbedTwitchPreview"
          class="twitch-preview-player"
          :src="twitchPreviewSrc"
          title="BMRL Twitch preview"
          allow="autoplay; fullscreen; picture-in-picture"
          scrolling="no"
        ></iframe>
        <img v-else-if="twitchStatus.thumbnail_url" :src="twitchStatus.thumbnail_url" alt="" />
        <PlayCircle :size="34" />
      </span>
      <strong v-if="!isTwitchCollapsed">{{ twitchDisplayTitle }}</strong>
    </div>

    <div v-if="isTwitchViewerOpen" class="twitch-viewer" role="dialog" aria-modal="true" @click="closeTwitchViewer">
      <div class="twitch-viewer-dialog" @click.stop>
        <div class="twitch-viewer-header">
          <div>
            <span class="twitch-window-kicker"><Radio :size="16" />Twitch</span>
            <h2>{{ twitchDisplayTitle }}</h2>
          </div>
          <button class="icon-button" type="button" :title="t('twitch.closePlayer')" @click="closeTwitchViewer">
            <X :size="20" />
          </button>
        </div>
        <div v-if="canEmbedTwitch" class="twitch-player-shell twitch-viewer-player">
          <iframe
            class="twitch-player"
            :src="twitchEmbedSrc"
            title="BMRL Twitch"
            allow="autoplay; fullscreen; picture-in-picture"
            allowfullscreen
            scrolling="no"
          ></iframe>
        </div>
        <div v-else class="twitch-player-empty">
          <Radio :size="34" />
          <strong>{{ t('twitch.unavailable') }}</strong>
          <p class="muted">{{ t('twitch.playerUnavailable') }}</p>
        </div>
      </div>
    </div>

    <div v-if="isNewsViewerOpen && currentNews" class="news-viewer" :class="{ 'is-video': isVideoUrl(currentNews.image_url) }" role="dialog" aria-modal="true" @click="closeNewsViewer">
      <video v-if="isVideoUrl(currentNews.image_url)" class="news-viewer-image" :src="currentNews.image_url" controls autoplay playsinline @click.stop></video>
      <img v-else class="news-viewer-image" :src="currentNews.image_url" alt="" />
      <button class="icon-button news-viewer-close" type="button" :title="t('news.closeFullscreen')" @click.stop="closeNewsViewer">
        <X :size="20" />
      </button>
      <button v-if="news.length > 1" class="icon-button news-viewer-nav prev" type="button" :title="t('news.scrollLeft')" @click.stop="moveNewsFromViewer(-1)">
        <ChevronLeft :size="24" />
      </button>
      <button v-if="news.length > 1" class="icon-button news-viewer-nav next" type="button" :title="t('news.scrollRight')" @click.stop="moveNewsFromViewer(1)">
        <ChevronRight :size="24" />
      </button>
      <button class="button small news-viewer-text-toggle" type="button" @click.stop="isNewsTextHidden = !isNewsTextHidden">
        {{ isNewsTextHidden ? t('news.showText') : t('news.hideText') }}
      </button>
      <div v-if="!isNewsTextHidden" class="news-viewer-content" @click.stop>
        <span class="pill news-viewer-count">{{ activeNewsIndex + 1 }} / {{ news.length }}</span>
        <h2>{{ currentNews.title }}</h2>
        <p>{{ currentNews.body }}</p>
      </div>
      <div v-if="news.length > 1" class="news-dots news-viewer-dots" :aria-label="t('news.indicators')">
        <button
          v-for="(_, index) in news"
          :key="index"
          class="news-dot"
          :class="{ 'is-active': index === activeNewsIndex }"
          type="button"
          :title="t('news.goTo', { number: index + 1 })"
          @click.stop="goToNews(index)"
        >
          <span class="visually-hidden">{{ t('news.goTo', { number: index + 1 }) }}</span>
        </button>
      </div>
    </div>
  </Teleport>
</template>
