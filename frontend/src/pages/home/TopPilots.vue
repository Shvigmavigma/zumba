<script setup>
// The five highest-rated ACC pilots, timing-screen style.
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowRight, Trophy } from 'lucide-vue-next'
import { api } from '../../api'
import EmptyState from '../../ui/EmptyState.vue'
import CountUp from '../../ui/fx/CountUp.vue'
import LicenseBadge from '../../components/LicenseBadge.vue'
import UserAvatar from '../../components/UserAvatar.vue'
import { pilotName, ratingForGame, teamShortName } from '../../pilotDisplay'
import RankAura from '../../ui/rank/RankAura.vue'
import { useRanks } from '../../useRanks'

const { t } = useI18n()
const { rankOf } = useRanks()
const pilots = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    pilots.value = await api('/users/pilots?sort=rating_desc&rating_game=ACC&limit=5&offset=0')
  } catch {
    pilots.value = []
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="top ui-glass" aria-labelledby="home-top-title">
    <header class="top__head">
      <div>
        <p class="ui-eyebrow ui-eyebrow--accent">{{ t('home.top.eyebrow') }}</p>
        <h2 id="home-top-title" class="ui-title top__title">{{ t('home.top.title') }}</h2>
      </div>
      <Trophy class="top__icon" :size="22" />
    </header>

    <ol v-if="pilots.length" class="top__list">
      <li v-for="(pilot, index) in pilots" :key="pilot.id" v-reveal="{ delay: index * 70, y: 10, blur: 0 }">
        <RouterLink class="top__row rank-surface" :to="`/pilots/${pilot.id}`" :data-rank="rankOf(pilot)">
          <RankAura :rank="rankOf(pilot)" :seed="pilot.id" />
          <span class="top__place ui-num" :class="`is-p${index + 1}`">{{ index + 1 }}</span>
          <UserAvatar mini class="top__avatar rank-avatar" :data-rank="rankOf(pilot)" :src="pilot.avatar_url" :color="pilot.avatar_color" :label="pilot.nickname || pilot.login" />
          <span class="top__who">
            <strong class="rank-name" :data-rank="rankOf(pilot)">{{ pilotName(pilot, pilot.login) }}</strong>
            <small><LicenseBadge :user="pilot" game="ACC" /> {{ pilot.nickname || pilot.login }}<template v-if="pilot.team_name"> · {{ teamShortName(pilot.team_name, pilot.team_abbreviation) }}</template></small>
          </span>
          <span class="top__rating"><CountUp :value="Math.round(Number(ratingForGame(pilot, 'ACC')) || 0)" /></span>
        </RouterLink>
      </li>
    </ol>
    <EmptyState v-else :loading="loading" :title="loading ? t('ui.common.loading') : t('home.top.empty')" compact />

    <RouterLink class="ui-link top__all" to="/pilots">{{ t('home.top.all') }}<ArrowRight :size="16" /></RouterLink>
  </section>
</template>

<style scoped>
.top {
  display: grid;
  align-content: start;
  gap: 16px;
  padding: 22px;
  border-radius: var(--r-xl);
}

.top__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.top__head > div {
  display: grid;
  gap: 8px;
}

.top__title {
  font-size: 20px;
}

.top__icon {
  color: var(--bm-gold);
}

.top__list {
  display: grid;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.top__row {
  position: relative;
  display: grid;
  grid-template-columns: 30px 36px minmax(0, 1fr) 64px;
  align-items: center;
  gap: 12px;
  padding: 8px 10px 8px 6px;
  border-radius: var(--r-md);
  color: var(--c-text);
  text-decoration: none;
  transition: background-color var(--dur-2), transform var(--dur-3) var(--ease-ios);
}

.top__row:hover {
  background: var(--c-blue-soft);
  transform: translateX(3px);
}

.top__place {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 9px;
  background: var(--c-sunken);
  color: var(--c-text-2);
  font-size: 13px;
  font-weight: 700;
}

.top__place.is-p1 {
  background: var(--bm-gold);
  color: #1b1300;
}

.top__place.is-p2 {
  background: var(--bm-silver);
  color: #0e141f;
}

.top__place.is-p3 {
  background: var(--bm-bronze);
  color: #1d0d02;
}

.top__avatar {
  width: 36px;
  height: 36px;
  border-width: 1px;
  box-shadow: none;
}

.top__who {
  display: grid;
  min-width: 0;
}

.top__who strong {
  overflow: hidden;
  font-size: 14px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.top__who small {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow: hidden;
  color: var(--c-text-3);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.top__rating {
  color: var(--c-text);
  font-size: 16px;
  font-weight: 600;
  text-align: right;
}

.top__all {
  justify-self: start;
  font-size: 14px;
}

.top__who :deep(.license-badge) {
  flex: 0 0 auto;
  font-size: 10px;
}
</style>
