<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RefreshCw } from 'lucide-vue-next'
import { api } from '../api'
import ChampionshipCallout from './home/ChampionshipCallout.vue'
import HomeHero from './home/HomeHero.vue'
import HomeRaceList from './home/HomeRaceList.vue'
import LatestRace from './home/LatestRace.vue'
import NewsCarousel from './home/NewsCarousel.vue'
import NextRaceCard from './home/NextRaceCard.vue'
import PilotSnapshot from './home/PilotSnapshot.vue'
import SetupsSection from './home/SetupsSection.vue'
import SponsorBanner from './home/SponsorBanner.vue'
import TopPilots from './home/TopPilots.vue'
import TwitchWidget from './home/TwitchWidget.vue'

const DEFAULT_NEWS_SETTINGS = { auto_rotate_seconds: 30, manual_pause_seconds: 300 }

const stats = ref({ pilots: 0, completed_races: 0, open_races: 0, staff: 0 })
const setups = ref([])
const showSetupsSection = ref(true)
const banners = ref([])
const news = ref([])
const newsSettings = ref(DEFAULT_NEWS_SETTINGS)
const weatherSettings = ref({})
const championships = ref([])
const { t } = useI18n()
const loadFailed = ref(false)
const loading = ref(false)
// The news banner waits for its data, so the empty state never flashes first.
const homeLoaded = ref(false)

// Open registration first (it asks for action), then a season under way; two plates at most.
const featuredChampionships = computed(() => [...championships.value]
  .sort((a, b) => Number(b.status === 'registration_open') - Number(a.status === 'registration_open'))
  .slice(0, 2))

function banner(position) {
  return banners.value.find((item) => item.position === position && item.image_url) || null
}

/**
 * Loads every home block. A block that fails keeps what it already shows, so
 * one bad request never blanks the page; the notice offers to try again.
 */
async function loadHome() {
  if (loading.value) return
  loading.value = true
  let anyFailed = false
  const loadOrKeep = async (path, current) => {
    try {
      return await api(path)
    } catch {
      anyFailed = true
      return current
    }
  }

  const [statsData, setupsData, bannerData, newsData, championshipData, loadedNewsSettings, loadedWeather, systemSettings] = await Promise.all([
    loadOrKeep('/dashboard/stats', stats.value),
    loadOrKeep('/setups?limit=6', setups.value),
    loadOrKeep('/banners', banners.value),
    loadOrKeep('/news', news.value),
    loadOrKeep('/championships?status_filter=active&limit=3', championships.value),
    loadOrKeep('/app-settings/news', newsSettings.value),
    loadOrKeep('/app-settings/weather', weatherSettings.value),
    loadOrKeep('/app-settings/system', { show_setups_section: showSetupsSection.value })
  ])
  stats.value = statsData || stats.value
  setups.value = setupsData || []
  banners.value = bannerData || []
  news.value = newsData || []
  championships.value = championshipData || []
  newsSettings.value = loadedNewsSettings || DEFAULT_NEWS_SETTINGS
  weatherSettings.value = loadedWeather || {}
  showSetupsSection.value = systemSettings?.show_setups_section !== false
  loadFailed.value = anyFailed
  loading.value = false
  homeLoaded.value = true
}

onMounted(loadHome)
</script>

<template>
  <div class="home">
    <HomeHero :stats="stats" />

    <div class="home__body ui-shell ui-shell--wide">
      <p v-if="loadFailed" class="ui-alert home__alert" role="alert">
        <span>{{ t('main.dataLoadError') }}</span>
        <button class="ui-btn ui-btn--outline ui-btn--sm" type="button" :disabled="loading" @click="loadHome">
          <RefreshCw :size="15" />{{ loading ? t('common.loading') : t('common.reload') }}
        </button>
      </p>

      <div class="home__lead">
        <NextRaceCard v-reveal="{ y: 28 }" :weather-settings="weatherSettings" />
        <PilotSnapshot v-reveal="{ delay: 120, y: 28 }" />
      </div>

      <ChampionshipCallout v-for="item in featuredChampionships" :key="item.id" v-reveal :championship="item" />

      <div class="home__pair">
        <TopPilots v-reveal />
        <LatestRace v-reveal="{ delay: 100 }" />
      </div>

      <!-- League news: a full-width banner right under the latest results, as on the original site. -->
      <NewsCarousel v-if="homeLoaded" :news="news" :settings="newsSettings" />

      <div class="home__rail" :class="{ 'has-left': banner('left'), 'has-right': banner('right') }">
        <SponsorBanner v-if="banner('left')" class="home__side" :banner="banner('left')" variant="side" />
        <HomeRaceList class="home__races" :weather-settings="weatherSettings" />
        <SponsorBanner v-if="banner('right')" class="home__side" :banner="banner('right')" variant="side" />
      </div>

      <SetupsSection v-if="showSetupsSection" v-reveal :setups="setups" />

      <SponsorBanner v-if="banner('bottom')" v-reveal :banner="banner('bottom')" />
    </div>

    <TwitchWidget />
  </div>
</template>

<style scoped>
.home {
  padding-bottom: clamp(32px, 5vw, 64px);
}

.home__body {
  display: grid;
  gap: clamp(18px, 2.4vw, 28px);
}

.home__alert {
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
}

/* The profile card is wide enough to carry a licence at about the size it has
   on the registration page. */
.home__lead {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 460px);
  gap: clamp(14px, 1.6vw, 20px);
  align-items: stretch;
}

/* Mirrors the lead row: the narrow card sits on the left here. */
.home__pair {
  display: grid;
  grid-template-columns: minmax(320px, 460px) minmax(0, 1fr);
  gap: clamp(14px, 1.6vw, 20px);
  align-items: start;
}

.home__rail {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: clamp(14px, 1.6vw, 20px);
  align-items: start;
  padding-top: clamp(8px, 2vw, 24px);
}

.home__rail.has-left {
  grid-template-columns: minmax(160px, 220px) minmax(0, 1fr);
}

.home__rail.has-right {
  grid-template-columns: minmax(0, 1fr) minmax(160px, 220px);
}

.home__rail.has-left.has-right {
  grid-template-columns: minmax(160px, 220px) minmax(0, 1fr) minmax(160px, 220px);
}

.home__side {
  position: sticky;
  top: calc(var(--header-h) + 16px);
}

@media (max-width: 1180px) {
  .home__lead,
  .home__pair {
    grid-template-columns: minmax(0, 1fr);
  }

  .home__rail.has-left,
  .home__rail.has-right,
  .home__rail.has-left.has-right {
    grid-template-columns: minmax(0, 1fr);
  }

  /* Relative, not static: the sponsor label is positioned against the banner. */
  .home__side {
    position: relative;
    top: auto;
    max-width: 420px;
  }

  .home__races {
    order: -1;
  }
}
</style>
