<script setup>
// The most recently finished race: podium, the weekend's best lap (race or
// qualifying, as the track records count it) and a link to the full report.
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowRight, PlayCircle, Timer } from 'lucide-vue-next'
import { api } from '../../api'
import EmptyState from '../../ui/EmptyState.vue'
import UserAvatar from '../../components/UserAvatar.vue'
import { gameLabel } from '../../i18nLabels'
import { loadRaceAssets, trackImageFor } from '../../raceDisplay'
import { bestLapOf } from '../race/raceClassification'
import { formatShortDate } from '../../timezone'

const { t } = useI18n()
const race = ref(null)
const assets = ref(null)
const loading = ref(true)

const rows = computed(() => {
  const results = race.value?.results
  const list = Array.isArray(results) ? results : Array.isArray(results?.rows) ? results.rows : []
  return list.filter((row) => row && row.status !== 'missing' && Number.isFinite(Number(row.position)))
    .sort((a, b) => Number(a.position) - Number(b.position))
})
const podium = computed(() => {
  const [first, second, third] = rows.value
  return [second, first, third].map((row, index) => (row ? { row, place: [2, 1, 3][index] } : null)).filter(Boolean)
})
const fastest = computed(() => bestLapOf(rows.value))
const image = computed(() => trackImageFor(assets.value, race.value))

function driverName(row) {
  return [row.first_name, row.last_name].filter(Boolean).join(' ') || row.driver_name || row.nickname || row.login || '—'
}

function lapTime(ms) {
  const total = Math.round(Number(ms))
  const minutes = Math.floor(total / 60000)
  const seconds = Math.floor((total % 60000) / 1000)
  return `${minutes}:${String(seconds).padStart(2, '0')}.${String(total % 1000).padStart(3, '0')}`
}

onMounted(async () => {
  try {
    const [list, loadedAssets] = await Promise.all([
      api('/races?status_filter=finished&include_championship=true&limit=1&offset=0'),
      loadRaceAssets().catch(() => null)
    ])
    race.value = list[0] || null
    assets.value = loadedAssets
  } catch {
    race.value = null
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="latest ui-glass" aria-labelledby="home-latest-title">
    <div v-if="image" class="latest__bg" aria-hidden="true"><img v-track-art :src="image" alt="" loading="lazy" /></div>
    <header class="latest__head">
      <div>
        <p class="ui-eyebrow ui-eyebrow--accent">{{ t('home.latest.eyebrow') }}</p>
        <h2 id="home-latest-title" class="ui-title latest__title">{{ t('home.latest.title') }}</h2>
      </div>
    </header>

    <template v-if="race">
      <div class="latest__race">
        <strong class="latest__name">{{ race.name }}</strong>
        <span class="latest__meta">{{ race.track }} · {{ gameLabel(t, race.game) }} · {{ formatShortDate(race.datetime_start) }}</span>
      </div>

      <div v-if="podium.length" class="latest__podium">
        <RouterLink
          v-for="item in podium"
          :key="item.place"
          v-reveal="{ delay: item.place * 90, y: 18 }"
          class="latest__step"
          :class="`is-p${item.place}`"
          :to="item.row.user_id ? `/pilots/${item.row.user_id}` : `/races/${race.id}`"
        >
          <UserAvatar class="latest__avatar" :src="item.row.avatar_url" :color="item.row.avatar_color || '#1652d8'" :label="driverName(item.row)" />
          <span class="latest__driver">{{ driverName(item.row) }}</span>
          <span class="latest__block">
            <b class="ui-num">P{{ item.place }}</b>
          </span>
        </RouterLink>
      </div>

      <p v-if="fastest" class="latest__fastest">
        <Timer :size="15" />
        <span>{{ t('tracks.bestLap') }}</span>
        <strong class="ui-num">{{ lapTime(fastest.ms) }}</strong>
        <span class="latest__fastest-who">{{ driverName(fastest.row) }}<template v-if="fastest.session === 'qualification'"> · {{ t('home.latest.inQualifying') }}</template></span>
      </p>

      <footer class="latest__actions">
        <RouterLink class="ui-btn ui-btn--outline ui-btn--sm" :to="`/races/${race.id}`">{{ t('home.latest.open') }}<ArrowRight :size="15" /></RouterLink>
        <RouterLink v-if="race.video_url" class="ui-btn ui-btn--ghost ui-btn--sm" :to="`/races/${race.id}`"><PlayCircle :size="16" />{{ t('raceDetails.videoTitle') }}</RouterLink>
      </footer>
    </template>
    <EmptyState v-else :loading="loading" :title="loading ? t('ui.common.loading') : t('home.latest.empty')" compact />
  </section>
</template>

<style scoped>
.latest {
  position: relative;
  display: grid;
  align-content: start;
  gap: 16px;
  padding: 22px;
  overflow: hidden;
  border-radius: var(--r-xl);
}

.latest__bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  opacity: 0.22;
  -webkit-mask-image: linear-gradient(180deg, #000, transparent 75%);
  mask-image: linear-gradient(180deg, #000, transparent 75%);
}

.latest__bg img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.latest > :not(.latest__bg) {
  position: relative;
  z-index: 1;
}

.latest__head > div {
  display: grid;
  gap: 8px;
}

.latest__title {
  font-size: 20px;
}

.latest__race {
  display: grid;
  gap: 4px;
}

.latest__name {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  text-transform: uppercase;
}

.latest__meta {
  color: var(--c-text-3);
  font-size: 13px;
}

.latest__podium {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  align-items: end;
  gap: 8px;
}

.latest__step {
  display: grid;
  justify-items: center;
  gap: 8px;
  min-width: 0;
  color: var(--c-text);
  text-decoration: none;
}

.latest__avatar {
  width: 44px;
  height: 44px;
}

.latest__step.is-p1 .latest__avatar {
  width: 54px;
  height: 54px;
  box-shadow: 0 0 0 3px var(--bm-gold), 0 0 24px color-mix(in srgb, var(--bm-gold) 50%, transparent);
}

.latest__driver {
  max-width: 100%;
  overflow: hidden;
  font-size: 12.5px;
  font-weight: 600;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.latest__block {
  display: grid;
  place-items: start center;
  width: 100%;
  padding-top: 8px;
  border-radius: var(--r-sm) var(--r-sm) 4px 4px;
  font-size: 14px;
  transition: transform var(--dur-3) var(--ease-ios);
}

.latest__step:hover .latest__block {
  transform: translateY(-3px);
}

.is-p1 .latest__block {
  height: 74px;
  background: linear-gradient(180deg, color-mix(in srgb, var(--bm-gold) 70%, transparent), color-mix(in srgb, var(--bm-gold) 12%, transparent));
  color: #1b1300;
}

.is-p2 .latest__block {
  height: 54px;
  background: linear-gradient(180deg, color-mix(in srgb, var(--bm-silver) 60%, transparent), color-mix(in srgb, var(--bm-silver) 10%, transparent));
  color: #0e141f;
}

.is-p3 .latest__block {
  height: 40px;
  background: linear-gradient(180deg, color-mix(in srgb, var(--bm-bronze) 65%, transparent), color-mix(in srgb, var(--bm-bronze) 10%, transparent));
  color: #1d0d02;
}

.latest__fastest {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 10px;
  margin: 0;
  padding: 10px 12px;
  border: 1px solid color-mix(in srgb, #a855f7 35%, transparent);
  border-radius: var(--r-md);
  background: color-mix(in srgb, #a855f7 10%, transparent);
  color: var(--c-text-2);
  font-size: 13px;
}

.latest__fastest svg {
  color: #c084fc;
}

.latest__fastest strong {
  color: var(--c-text);
  font-size: 14px;
}

.latest__fastest-who {
  color: var(--c-text-3);
}

.latest__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
