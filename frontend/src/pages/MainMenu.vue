<script setup>
import { onMounted, ref } from 'vue'
import { Plus } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { state } from '../store'

const { t } = useI18n()
const stats = ref({ pilots: 0, completed_races: 0, open_races: 0, staff: 0 })
const races = ref([])
const setups = ref([])
const banners = ref([])
const error = ref('')

function banner(position) {
  return banners.value.find((item) => item.position === position)
}

onMounted(async () => {
  try {
    const [statsData, racesData, setupsData, bannerData] = await Promise.all([
      api('/dashboard/stats'),
      api('/races?limit=8'),
      api('/setups?limit=6'),
      api('/banners')
    ])
    stats.value = statsData
    races.value = racesData
    setups.value = setupsData
    banners.value = bannerData
  } catch (err) {
    error.value = err.message
  }
})
</script>

<template>
  <div class="banner-layout">
    <a v-if="banner('left')" class="banner side" :href="banner('left').link_url"><img :src="banner('left').image_url" alt="" /></a>
    <div>
      <a v-if="banner('top')" class="banner" :href="banner('top').link_url"><img :src="banner('top').image_url" alt="" /></a>

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
        <div class="race-list">
          <article v-for="race in races" :key="race.id" class="card race-item">
            <div>
              <h3>{{ race.name }}</h3>
              <p class="muted">{{ race.track }} · {{ race.car_class }} · {{ new Date(race.datetime_start).toLocaleString(state.locale) }}</p>
            </div>
            <RouterLink class="button" :to="`/races/${race.id}`">{{ t('common.open') }}</RouterLink>
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
        <p class="muted">Discord: BRML · Email: race-control@example.com</p>
      </section>
    </div>
    <a v-if="banner('right')" class="banner side" :href="banner('right').link_url"><img :src="banner('right').image_url" alt="" /></a>
  </div>
</template>
