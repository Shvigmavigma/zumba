<script setup>
// Shared pilot profile: hero, then Overview (licences + details) and
// Statistics tabs. The own-profile page adds actions, alerts and an Account tab.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { BarChart3, LayoutGrid, UserCog } from 'lucide-vue-next'
import AvatarViewer from '../../components/AvatarViewer.vue'
import PilotLiveryPanel from '../../components/PilotLiveryPanel.vue'
import PilotLicenseCard from '../../components/PilotLicenseCard.vue'
import ProfileAnalytics from '../../components/ProfileAnalytics.vue'
import SegmentedControl from '../../ui/SegmentedControl.vue'
import PilotHero from './PilotHero.vue'
import { countryLabel, gameLabel, roleLabel, statusLabel } from '../../i18nLabels'
import { DEFAULT_LICENSE_TIERS, ratedGames, ratingForGame, ratingLicenseTier } from '../../pilotDisplay'
import { isRerExcluded } from '../../ranks'
import { state } from '../../store'
import { formatShortDate } from '../../timezone'

const props = defineProps({
  pilot: { type: Object, required: true },
  tiers: { type: Array, default: () => DEFAULT_LICENSE_TIERS },
  own: { type: Boolean, default: false }
})

// Who may upload a livery: an active account with a racing or staff role, on its own page.
const LIVERY_ROLES = ['admin', 'moder', 'marshall', 'smm', 'pilot']

const { t } = useI18n()
const tab = ref('overview')
const avatarOpen = ref(false)
const peaks = ref({})

const tabs = computed(() => [
  { value: 'overview', label: t('profilePage.tabs.overview'), icon: LayoutGrid },
  { value: 'stats', label: t('profilePage.tabs.stats'), icon: BarChart3 },
  ...(props.own ? [{ value: 'account', label: t('profilePage.tabs.account'), icon: UserCog }] : [])
])
const canManageLivery = computed(() => Number(state.user?.id) === Number(props.pilot.id)
  && props.pilot.status === 'active'
  && LIVERY_ROLES.includes(state.user?.role))
// No licences for a pilot outside the rating: there is no RER behind them.
const licenceGames = computed(() => (isRerExcluded(props.pilot) ? [] : ratedGames(props.pilot)))
const licences = computed(() => licenceGames.value.map((game) => {
  const rating = ratingForGame(props.pilot, game)
  return { game, rating, tier: ratingLicenseTier(rating, props.tiers) }
}))
const details = computed(() => [
  { label: t('fields.team'), value: props.pilot.team_name || t('profilePage.about.noTeam') },
  { label: t('fields.country'), value: countryLabel(t, props.pilot.country) },
  { label: t('fields.discord'), value: props.pilot.discord || t('common.none') },
  { label: t('profilePage.about.games'), value: props.pilot.games?.length ? props.pilot.games.map((game) => gameLabel(t, game)).join(' · ') : t('common.none') },
  { label: t('profile.favoriteCar'), value: props.pilot.favorite_car || t('common.none') },
  { label: 'SR', value: Number.isFinite(Number(props.pilot.sr)) ? Number(props.pilot.sr).toFixed(1) : t('common.none') },
  { label: t('common.role'), value: roleLabel(t, props.pilot.role) },
  { label: t('common.status'), value: statusLabel(t, props.pilot.status) },
  { label: t('fields.joinedAt'), value: formatShortDate(props.pilot.created_at, { month: 'long' }) }
])

function onAnalytics(analytics) {
  const result = {}
  for (const point of analytics?.rating_history || []) {
    const value = Math.round(Number(point.rating))
    if (Number.isFinite(value) && (!result[point.game] || value > result[point.game])) result[point.game] = value
  }
  peaks.value = result
}
</script>

<template>
  <div class="profile">
    <PilotHero :pilot="pilot" :tiers="tiers" :peaks="peaks" :own="own" @open-avatar="avatarOpen = true">
      <template v-if="$slots.actions" #actions><slot name="actions" /></template>
    </PilotHero>

    <slot name="alerts" />

    <div class="profile__tabs">
      <SegmentedControl v-model="tab" :options="tabs" :aria-label="t('profilePage.tabs.overview')" />
    </div>

    <div v-show="tab === 'overview'" class="profile__panel" :class="{ 'is-active': tab === 'overview' }">
      <section v-if="licences.length" class="ui-card">
        <header class="ui-card__head">
          <div class="ui-card__title">
            <h2>{{ t('profilePage.licences.title') }}</h2>
          </div>
          <p class="profile__hint">{{ t('profilePage.licences.hint') }}</p>
        </header>
        <div class="profile__licences">
          <PilotLicenseCard v-for="(licence, index) in licences" :key="licence.game" v-reveal="{ delay: index * 90 }" :pilot="pilot" :game="licence.game" :rating="licence.rating" :tier="licence.tier" />
        </div>
      </section>

      <PilotLiveryPanel :user-id="pilot.id" :can-manage="canManageLivery" />

      <section class="ui-card">
        <header class="ui-card__title">
          <h2>{{ t('profilePage.about.title') }}</h2>
        </header>
        <dl class="ui-kv">
          <div v-for="item in details" :key="item.label">
            <dt>{{ item.label }}</dt>
            <dd :title="String(item.value)">{{ item.value }}</dd>
          </div>
        </dl>
      </section>
    </div>

    <div v-show="tab === 'stats'" class="profile__panel" :class="{ 'is-active': tab === 'stats' }">
      <ProfileAnalytics :user-id="pilot.id" :favorite-car="pilot.favorite_car" :user="pilot" @loaded="onAnalytics" />
    </div>

    <div v-if="own" v-show="tab === 'account'" class="profile__panel" :class="{ 'is-active': tab === 'account' }">
      <slot name="account" />
    </div>

    <AvatarViewer
      :open="avatarOpen"
      :src="pilot.avatar_url"
      :label="pilot.nickname || pilot.login || t('roles.pilot')"
      :fallback-color="pilot.avatar_color"
      @close="avatarOpen = false"
    />
  </div>
</template>

<style scoped>
.profile {
  display: grid;
  gap: clamp(16px, 2vw, 22px);
}

.profile__tabs {
  display: flex;
}

.profile__panel {
  display: grid;
  gap: clamp(16px, 2vw, 22px);
}

.profile__panel.is-active {
  animation: profile-panel 520ms var(--ease-ios);
}

@keyframes profile-panel {
  from {
    opacity: 0;
    filter: blur(6px);
    transform: translateY(10px);
  }
}

.profile__hint {
  max-width: 46ch;
  margin: 0;
  color: var(--c-text-3);
  font-size: 13px;
}

/* Licences need room for the name, the plate and the tier row. */
.profile__licences {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 400px), 1fr));
  gap: 16px;
}

@media (prefers-reduced-motion: reduce) {
  .profile__panel.is-active {
    animation: none;
  }
}
</style>
