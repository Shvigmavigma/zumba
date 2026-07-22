<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight, Eye, Maximize2, Plus, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { gameLabel, gameOptions, statusLabel } from '../i18nLabels'
import { state } from '../store'

const { t } = useI18n()
const stats = ref({ pilots: 0, completed_races: 0, open_races: 0, staff: 0 })
const races = ref([])
const setups = ref([])
const banners = ref([])
const news = ref([])
const newsTrack = ref(null)
const activeNewsIndex = ref(0)
const isNewsViewerOpen = ref(false)
const error = ref('')
const raceGameFilter = ref('all')
const myGamesOnly = ref(false)
const currentNews = computed(() => news.value[activeNewsIndex.value] || null)
const raceGameOptions = computed(() => gameOptions(t, true))
const canFilterMyGames = computed(() => Boolean(state.user?.games?.length))

function banner(position) {
  return banners.value.find((item) => item.position === position && item.image_url)
}

function formatRaceDate(value) {
  return new Date(value).toLocaleString(state.locale, {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function registeredCount(race) {
  return race.registered_pilots?.length || 0
}

function fillPercent(race) {
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
  isNewsViewerOpen.value = true
}

function closeNewsViewer() {
  isNewsViewerOpen.value = false
}

function moveNewsFromViewer(direction) {
  goToNews(activeNewsIndex.value + direction)
}

function handleNewsKeydown(event) {
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
  const params = new URLSearchParams({ limit: '8', game_filter: raceGameFilter.value })
  if (myGamesOnly.value && canFilterMyGames.value) {
    params.set('my_games_only', 'true')
  }
  races.value = await api(`/races?${params.toString()}`)
}

onMounted(async () => {
  window.addEventListener('keydown', handleNewsKeydown)
  try {
    const [statsData, setupsData, bannerData, newsData] = await Promise.all([
      api('/dashboard/stats'),
      api('/setups?limit=6'),
      api('/banners'),
      api('/news')
    ])
    stats.value = statsData
    setups.value = setupsData
    banners.value = bannerData
    news.value = newsData
    activeNewsIndex.value = 0
    await loadRaces()
  } catch (err) {
    error.value = err.message
  }
})

watch([raceGameFilter, myGamesOnly], async () => {
  try {
    await loadRaces()
  } catch (err) {
    error.value = err.message
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleNewsKeydown)
})
</script>

<template>
  <div class="main-menu">
    <a v-if="banner('top')" class="banner main-menu-top-banner" :href="banner('top').link_url"><img :src="banner('top').image_url" alt="" /></a>

    <div class="main-menu-layout">
      <a v-if="banner('left')" class="banner side main-menu-side-banner left" :href="banner('left').link_url"><img :src="banner('left').image_url" alt="" /></a>

      <div class="main-menu-content">
        <section v-if="news.length" class="section news-strip">
          <div class="section-header news-strip-header">
            <h2>{{ t('news.title') }}</h2>
            <div class="toolbar">
              <button class="icon-button" type="button" :title="t('news.scrollLeft')" @click="scrollNews(-1)">
                <ChevronLeft :size="18" />
              </button>
              <button class="icon-button" type="button" :title="t('news.scrollRight')" @click="scrollNews(1)">
                <ChevronRight :size="18" />
              </button>
            </div>
          </div>
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
              <img :src="item.image_url" alt="" />
              <span class="news-card-open"><Maximize2 :size="16" /></span>
              <div>
                <h3>{{ item.title }}</h3>
                <p>{{ item.body }}</p>
              </div>
            </article>
          </div>
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

        <section class="section">
          <div class="grid cols-4">
            <div class="card stat"><span class="muted">{{ t('main.pilots') }}</span><strong>{{ stats.pilots }}</strong></div>
            <div class="card stat"><span class="muted">{{ t('main.completed') }}</span><strong>{{ stats.completed_races }}</strong></div>
            <div class="card stat"><span class="muted">{{ t('main.open') }}</span><strong>{{ stats.open_races }}</strong></div>
            <div class="card stat"><span class="muted">{{ t('main.staff') }}</span><strong>{{ stats.staff }}</strong></div>
          </div>
        </section>

        <p v-if="error" class="error">{{ error }}</p>

        <section class="section">
          <div class="section-header">
            <h2>{{ t('main.races') }}</h2>
            <RouterLink v-if="['admin', 'moder'].includes(state.user?.role)" class="button primary" to="/races/new"><Plus :size="16" />{{ t('common.create') }}</RouterLink>
          </div>
          <div class="race-filter-bar card">
            <label class="field">
              <span>{{ t('fields.game') }}</span>
              <select v-model="raceGameFilter">
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
              <div class="main-race-card-head">
                <div class="main-race-title">
                  <RouterLink :to="`/races/${race.id}`">{{ race.name }}</RouterLink>
                  <p class="muted">{{ gameLabel(t, race.game) }} - {{ race.track }} - {{ race.car_class }}</p>
                </div>
                <span class="status-badge race-status-badge" :class="`race-status-${race.status}`">{{ statusLabel(t, race.status) }}</span>
              </div>

              <div class="main-race-meta">
                <span>{{ formatRaceDate(race.datetime_start) }}</span>
                <span>{{ registeredCount(race) }} / {{ race.max_pilots }}</span>
              </div>

              <span class="race-registration-meter">
                <span :style="{ width: `${fillPercent(race)}%` }"></span>
              </span>

              <RouterLink class="button main-race-open" :to="`/races/${race.id}`">
                <Eye :size="16" />
                {{ t('common.open') }}
              </RouterLink>
            </article>
          </div>
        </section>

        <section class="section">
          <div class="section-header"><h2>{{ t('main.setups') }}</h2></div>
          <div class="grid cols-2">
            <article v-for="setup in setups" :key="setup.id" class="card">
              <strong>{{ setup.car_model }}</strong>
              <p class="muted">{{ setup.description || setup.setup_data }}</p>
            </article>
          </div>
        </section>

        <a v-if="banner('bottom')" class="banner" :href="banner('bottom').link_url"><img :src="banner('bottom').image_url" alt="" /></a>

        <section class="section card">
          <strong>{{ t('main.contacts') }}</strong>
          <p class="muted">Discord: BMRL - {{ t('fields.email') }}: race-control@example.com</p>
        </section>
      </div>

      <a v-if="banner('right')" class="banner side main-menu-side-banner right" :href="banner('right').link_url"><img :src="banner('right').image_url" alt="" /></a>
    </div>
  </div>

  <Teleport to="body">
    <div v-if="isNewsViewerOpen && currentNews" class="news-viewer" role="dialog" aria-modal="true" @click="closeNewsViewer">
      <img class="news-viewer-image" :src="currentNews.image_url" alt="" />
      <button class="icon-button news-viewer-close" type="button" :title="t('news.closeFullscreen')" @click.stop="closeNewsViewer">
        <X :size="20" />
      </button>
      <button v-if="news.length > 1" class="icon-button news-viewer-nav prev" type="button" :title="t('news.scrollLeft')" @click.stop="moveNewsFromViewer(-1)">
        <ChevronLeft :size="24" />
      </button>
      <button v-if="news.length > 1" class="icon-button news-viewer-nav next" type="button" :title="t('news.scrollRight')" @click.stop="moveNewsFromViewer(1)">
        <ChevronRight :size="24" />
      </button>
      <div class="news-viewer-content" @click.stop>
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
