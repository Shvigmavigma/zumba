<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import UserAvatar from '../components/UserAvatar.vue'
import { countryLabel, gameLabel, roleLabel, statusLabel } from '../i18nLabels'
import { formatRating, teamShortName } from '../pilotDisplay'
import { state } from '../store'

const { t } = useI18n()
const route = useRoute()
const pilot = ref(null)
const error = ref('')

function formatDate(value) {
  return new Date(value).toLocaleDateString(state.locale, {
    day: '2-digit',
    month: 'long',
    year: 'numeric'
  })
}

function gameList(user) {
  return user.games?.length ? user.games.map((game) => gameLabel(t, game)) : [t('common.none')]
}

onMounted(async () => {
  try {
    pilot.value = await api(`/users/${route.params.id}`)
  } catch (err) {
    error.value = err.message
  }
})
</script>

<template>
  <section class="section pilot-profile-page">
    <p v-if="error" class="error">{{ error }}</p>
    <section v-if="pilot" class="card pilot-profile-card">
      <UserAvatar class="pilot-profile-avatar" :color="pilot.avatar_color" :label="pilot.nickname || pilot.login" />

      <div class="pilot-profile-main">
        <div class="section-header pilot-profile-head">
          <div>
            <h1>{{ pilot.first_name }} {{ pilot.last_name }}</h1>
            <p class="muted">{{ pilot.nickname }} - {{ pilot.login }}</p>
          </div>
          <div class="toolbar">
            <span class="pill">RER {{ formatRating(pilot.rating) }}</span>
            <span class="pill">SR {{ pilot.sr }}</span>
          </div>
        </div>

        <div class="pilot-profile-badges">
          <span class="pill">#{{ pilot.pilot_number }}</span>
          <span class="pill" :title="pilot.team_name || t('common.none')">{{ t('fields.team') }} {{ teamShortName(pilot.team_name) }}</span>
          <span class="pill">{{ countryLabel(t, pilot.country) }}</span>
          <span class="status-badge" :class="`status-${pilot.status}`">{{ statusLabel(t, pilot.status) }}</span>
          <span class="pill">{{ roleLabel(t, pilot.role) }}</span>
        </div>

        <dl class="pilot-public-grid">
          <div>
            <dt>{{ t('fields.steam') }}</dt>
            <dd>{{ pilot.steam_id }}</dd>
          </div>
          <div>
            <dt>{{ t('fields.discord') }}</dt>
            <dd>{{ pilot.discord || t('common.none') }}</dd>
          </div>
          <div>
            <dt>{{ t('fields.country') }}</dt>
            <dd>{{ countryLabel(t, pilot.country) }}</dd>
          </div>
          <div>
            <dt>{{ t('fields.team') }}</dt>
            <dd>{{ pilot.team_name || t('common.none') }}</dd>
          </div>
          <div>
            <dt>{{ t('fields.rating') }}</dt>
            <dd>{{ formatRating(pilot.rating) }}</dd>
          </div>
          <div>
            <dt>{{ t('fields.ratingRaces') }}</dt>
            <dd>{{ pilot.rating_race_count ?? 0 }}</dd>
          </div>
          <div>
            <dt>{{ t('fields.joinedAt') }}</dt>
            <dd>{{ formatDate(pilot.created_at) }}</dd>
          </div>
        </dl>

        <div class="pilot-games">
          <span>{{ t('fields.games') }}</span>
          <div>
            <span v-for="game in gameList(pilot)" :key="game" class="pill">{{ game }}</span>
          </div>
        </div>
      </div>
    </section>
  </section>
</template>
