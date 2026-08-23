<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import AvatarViewer from '../components/AvatarViewer.vue'
import ProfileAnalytics from '../components/ProfileAnalytics.vue'
import UserAvatar from '../components/UserAvatar.vue'
import { countryLabel, gameLabel, roleLabel, statusLabel } from '../i18nLabels'
import { DEFAULT_LICENSE_TIERS, RATING_GAMES, formatPilotNumber, formatRating, licenseBadgeStyle, normalizeLicenseTiers, ratingForGame, ratingLicenseTier, ratingRaceCountForGame, teamShortName } from '../pilotDisplay'
import { formatShortDate } from '../timezone'

const { t } = useI18n()
const route = useRoute()
const pilot = ref(null)
const error = ref('')
const avatarViewerOpen = ref(false)
const licenseTiers = ref(DEFAULT_LICENSE_TIERS)

function formatDate(value) {
  return formatShortDate(value, { month: 'long' })
}

function gameList(user) {
  return user.games?.length ? user.games.map((game) => gameLabel(t, game)) : [t('common.none')]
}

function pilotLicense() {
  return ratingLicenseTier(ratingForGame(pilot.value, 'ACC'), licenseTiers.value)
}

const ratingRows = computed(() => RATING_GAMES.map((game) => ({
  game,
  rating: ratingForGame(pilot.value, game),
  races: ratingRaceCountForGame(pilot.value, game),
  license: ratingLicenseTier(ratingForGame(pilot.value, game), licenseTiers.value)
})))

onMounted(async () => {
  try {
    const [loadedPilot, loadedLicenses] = await Promise.all([
      api(`/users/${route.params.id}`),
      api('/app-settings/licenses').catch(() => null)
    ])
    pilot.value = loadedPilot
    licenseTiers.value = normalizeLicenseTiers(loadedLicenses)
  } catch (err) {
    error.value = err.message
  }
})
</script>

<template>
  <section class="section pilot-profile-page">
    <p v-if="error" class="error">{{ error }}</p>
    <section v-if="pilot" class="card pilot-profile-card">
      <button class="avatar-open-button pilot-profile-avatar-button" type="button" :title="t('avatar.open')" @click="avatarViewerOpen = true">
        <UserAvatar class="pilot-profile-avatar" :src="pilot.avatar_url" :color="pilot.avatar_color" :label="pilot.nickname || pilot.login" />
      </button>

      <div class="pilot-profile-main">
        <div class="section-header pilot-profile-head">
          <div>
            <h1>{{ pilot.first_name }} {{ pilot.last_name }}</h1>
            <p class="muted">{{ pilot.nickname }} - {{ pilot.login }}</p>
          </div>
          <div class="toolbar">
            <span class="pill">ACC RER {{ formatRating(ratingForGame(pilot, 'ACC')) }}</span>
            <span class="license-badge" :style="licenseBadgeStyle(pilotLicense())">{{ pilotLicense().name }}</span>
            <span class="pill">SR {{ pilot.sr }}</span>
          </div>
        </div>

        <div class="pilot-profile-badges">
          <span class="pill">#{{ formatPilotNumber(pilot.pilot_number) }}</span>
          <span class="pill" :title="pilot.team_name || t('common.none')">{{ t('fields.team') }} {{ teamShortName(pilot.team_name, pilot.team_abbreviation) }}</span>
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
            <dd>{{ formatRating(ratingForGame(pilot, 'ACC')) }}</dd>
          </div>
          <div>
            <dt>{{ t('fields.license') }}</dt>
            <dd><span class="license-badge" :style="licenseBadgeStyle(pilotLicense())">{{ pilotLicense().name }}</span></dd>
          </div>
          <div>
            <dt>{{ t('fields.ratingRaces') }}</dt>
            <dd>{{ ratingRaceCountForGame(pilot, 'ACC') }}</dd>
          </div>
          <div>
            <dt>{{ t('fields.joinedAt') }}</dt>
            <dd>{{ formatDate(pilot.created_at) }}</dd>
          </div>
        </dl>

        <div class="pilot-games">
          <span>RER</span>
          <div>
            <span v-for="row in ratingRows" :key="row.game" class="pill">
              {{ row.game }} {{ formatRating(row.rating) }} · {{ row.license.name }} · {{ row.races }}
            </span>
          </div>
        </div>

        <div class="pilot-games">
          <span>{{ t('fields.games') }}</span>
          <div>
            <span v-for="game in gameList(pilot)" :key="game" class="pill">{{ game }}</span>
          </div>
        </div>

        <div class="pilot-games profile-favorite-car-row">
          <span>{{ t('profile.favoriteCar') }}</span>
          <strong>{{ pilot.favorite_car || t('common.none') }}</strong>
        </div>
      </div>
    </section>
    <ProfileAnalytics v-if="pilot" :user-id="pilot.id" :favorite-car="pilot.favorite_car" :user="pilot" />
    <AvatarViewer
      :open="avatarViewerOpen"
      :src="pilot?.avatar_url"
      :label="pilot?.nickname || pilot?.login || t('roles.pilot')"
      :fallback-color="pilot?.avatar_color"
      @close="avatarViewerOpen = false"
    />
  </section>
</template>
