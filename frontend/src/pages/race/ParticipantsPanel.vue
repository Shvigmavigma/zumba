<script setup>
// Entry list. Collapsed it shows a stack of avatars; expanded, a searchable,
// sortable grid of driver cards (number plate, licence, roles, team, car).
// Moderators can withdraw a driver before the race starts.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowUpDown, Car, ChevronDown, ChevronUp, RefreshCw, Search, UserMinus, Users } from 'lucide-vue-next'
import LicenseBadge from '../../components/LicenseBadge.vue'
import PaginationControls from '../../components/PaginationControls.vue'
import PilotRoles from '../../components/PilotRoles.vue'
import UserAvatar from '../../components/UserAvatar.vue'
import EmptyState from '../../ui/EmptyState.vue'
import { countryLabel } from '../../i18nLabels'
import { filterPilots, formatPilotNumber, formatRating, ratingForGame, sortPilots, teamHref, teamShortName } from '../../pilotDisplay'
import { state } from '../../store'
import { personName } from './raceFormat'
import RankAura from '../../ui/rank/RankAura.vue'
import { useRanks } from '../../useRanks'
import RankEmblem from '../../ui/rank/RankEmblem.vue'

const PAGE_SIZE = 12
const STACK_SIZE = 9

const props = defineProps({
  participants: { type: Array, default: () => [] },
  teamRegistrations: { type: Array, default: () => [] },
  isTeamEvent: { type: Boolean, default: false },
  maxPilots: { type: Number, default: 0 },
  game: { type: String, default: 'ACC' },
  canRemove: { type: Boolean, default: false },
  /** Staff may hand every pilot the number from their profile. */
  canAssignNumbers: { type: Boolean, default: false },
  pending: { type: Boolean, default: false }
})
const emit = defineEmits(['remove', 'assign-numbers'])
const { t } = useI18n()
const { rankOf } = useRanks()

const expanded = ref(false)
const search = ref('')
const sort = ref('rating_desc')
const page = ref(1)

const sortOptions = computed(() => [
  { value: 'rating_desc', label: t('sort.ratingDesc') },
  { value: 'rating_asc', label: t('sort.ratingAsc') },
  { value: 'sr_desc', label: t('sort.srDesc') },
  { value: 'sr_asc', label: t('sort.srAsc') },
  { value: 'alpha_asc', label: t('sort.alphaAsc') },
  { value: 'alpha_desc', label: t('sort.alphaDesc') }
])
const visible = computed(() => sortPilots(filterPilots(props.participants, search.value), sort.value, props.game))
const totalPages = computed(() => Math.max(1, Math.ceil(visible.value.length / PAGE_SIZE)))
const paged = computed(() => visible.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE))
const total = computed(() => (props.isTeamEvent ? props.teamRegistrations.length : props.participants.length))
const stack = computed(() => {
  if (props.isTeamEvent) {
    return props.teamRegistrations.slice(0, STACK_SIZE).map((item) => ({ key: `team-${item.id}`, src: item.team_avatar_url, color: item.team_avatar_color, label: item.team_name }))
  }
  return sortPilots(props.participants, 'rating_desc', props.game).slice(0, STACK_SIZE)
    .map((item) => ({ key: item.user_id, src: item.avatar_url, color: item.avatar_color, label: name(item) }))
})

function name(item) {
  return personName(item, `${t('roles.pilot')} ${item.user_id}`)
}

function includesMe(registration) {
  return Boolean(state.user) && (registration.drivers || []).some((driver) => Number(driver.user_id) === Number(state.user.id))
}

function pilotHref(item) {
  const userId = Number(item?.user_id || item?.id)
  return Number.isInteger(userId) && userId > 0 ? `/pilots/${userId}` : ''
}

function team(item) {
  const short = teamShortName(item?.team_name, item?.team_abbreviation)
  return short === '-' ? '' : short
}

watch([search, sort], () => {
  page.value = 1
})
watch(visible, () => {
  if (page.value > totalPages.value) page.value = totalPages.value
})
</script>

<template>
  <section class="entries ui-card" aria-labelledby="race-grid-title">
    <header class="ui-card__head">
      <div class="ui-card__title">
        <p class="ui-eyebrow ui-eyebrow--accent">{{ t('racePage.grid.eyebrow') }}</p>
        <h2 id="race-grid-title">{{ isTeamEvent ? t('raceDetails.teams') : t('raceDetails.participants') }}</h2>
        <p class="entries__sub">
          {{ isTeamEvent ? t('raceDetails.registeredTeams', { count: teamRegistrations.length }) : t('raceDetails.registeredPilots', { count: participants.length }) }}
        </p>
      </div>
      <div class="entries__head-side">
        <span class="entries__count ui-num"><b>{{ total }}</b><span v-if="maxPilots"> / {{ maxPilots }}</span></span>
        <button v-if="canAssignNumbers" class="ui-btn ui-btn--ghost ui-btn--sm" type="button" :disabled="pending" @click="emit('assign-numbers')">
          <RefreshCw :size="15" />{{ t('raceDetails.assignProfileNumbers') }}
        </button>
        <button
          v-if="total"
          class="ui-btn ui-btn--outline ui-btn--sm"
          type="button"
          :aria-expanded="expanded"
          :aria-label="expanded ? t('raceDetails.collapseParticipants') : t('raceDetails.expandParticipants')"
          @click="expanded = !expanded"
        >
          {{ expanded ? t('racePage.grid.collapse') : t('racePage.grid.expand') }}
          <ChevronUp v-if="expanded" :size="16" />
          <ChevronDown v-else :size="16" />
        </button>
      </div>
    </header>

    <EmptyState v-if="!total" :icon="Users" compact :title="isTeamEvent ? t('raceDetails.noRegisteredTeams') : t('raceDetails.noRegisteredPilots')" :text="t('racePage.grid.emptyText')" />

    <Transition v-else name="race-swap" mode="out-in">
      <button v-if="!expanded" key="stack" class="entries__stack" type="button" @click="expanded = true">
        <span class="entries__avatars">
          <UserAvatar v-for="(item, index) in stack" :key="item.key" class="entries__stack-avatar" :style="{ '--i': index }" :src="item.src || ''" :color="item.color" :label="item.label" />
          <span v-if="total > stack.length" class="entries__more ui-num">+{{ total - stack.length }}</span>
        </span>
        <span class="entries__stack-text">{{ t('racePage.grid.stackHint') }}</span>
      </button>

      <div v-else key="list" class="entries__body">
        <template v-if="isTeamEvent">
          <div class="entries__cards entries__cards--teams">
            <article v-for="(item, index) in teamRegistrations" :key="item.id" v-reveal="{ delay: Math.min(index, 8) * 50, y: 14, blur: 4 }" class="team" :class="{ 'is-me': includesMe(item) }">
              <UserAvatar class="team__avatar" :src="item.team_avatar_url || ''" :color="item.team_avatar_color" :label="item.team_name" />
              <div class="team__main">
                <strong>{{ item.team_name }} <span v-if="item.team_abbreviation" class="ui-faint">({{ item.team_abbreviation }})</span></strong>
                <ol class="team__drivers">
                  <li v-for="(driver, order) in item.drivers || []" :key="driver.user_id || order">
                    <b class="ui-num">{{ order + 1 }}</b>{{ name(driver) }}<PilotRoles :roles="driver.pilot_roles" />
                  </li>
                </ol>
                <span class="team__car"><Car :size="14" />{{ item.car_model }}</span>
              </div>
              <span class="plate ui-num">{{ formatPilotNumber(item.race_number) }}</span>
            </article>
          </div>
        </template>

        <template v-else>
          <div class="entries__tools">
            <label class="entries__search">
              <Search :size="16" aria-hidden="true" />
              <input v-model="search" class="ui-input" type="search" :placeholder="t('raceDetails.participantSearch')" :aria-label="t('raceDetails.participantSearch')" />
            </label>
            <label class="entries__sort">
              <ArrowUpDown :size="16" aria-hidden="true" />
              <select v-model="sort" class="ui-select" :aria-label="t('common.sort')">
                <option v-for="option in sortOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
              </select>
            </label>
            <span class="entries__found ui-num">{{ visible.length }} / {{ participants.length }}</span>
          </div>

          <TransitionGroup v-if="visible.length" tag="div" name="ui-list" class="entries__cards">
            <article v-for="item in paged" :key="item.user_id" class="pc rank-surface" :class="{ 'is-me': item.user_id === state.user?.id }" :data-rank="rankOf(item)">
              <RankAura :rank="rankOf(item)" :seed="item.user_id" />
              <RankEmblem v-if="rankOf(item) !== 'rookie'" class="pc__crest" :rank="rankOf(item)" :size="132" />
              <div class="pc__top">
                <UserAvatar class="pc__avatar rank-avatar" :data-rank="rankOf(item)" :src="item.avatar_url || ''" :color="item.avatar_color" :label="name(item)" />
                <span class="plate plate--sm ui-num">{{ formatPilotNumber(item.pilot_number) }}</span>
              </div>
              <div class="pc__id">
                <RouterLink v-if="pilotHref(item)" class="pc__name rank-name" :data-rank="rankOf(item)" :to="pilotHref(item)">{{ name(item) }}</RouterLink>
                <strong v-else class="pc__name rank-name" :data-rank="rankOf(item)">{{ name(item) }}</strong>
                <span v-if="item.nickname" class="pc__nick">{{ item.nickname }}</span>
                <span v-if="item.user_id === state.user?.id" class="ui-chip ui-chip--blue pc__me">{{ t('racePage.grid.you') }}</span>
              </div>
              <div class="pc__badges">
                <LicenseBadge :user="item" :game="game" />
                <PilotRoles :roles="item.pilot_roles" />
                <RouterLink v-if="team(item) && item.team_id" class="ui-chip pc__team" :to="teamHref(item.team_id)">{{ team(item) }}</RouterLink>
                <span v-else-if="team(item)" class="ui-chip pc__team">{{ team(item) }}</span>
              </div>
              <dl class="pc__stats">
                <div><dt>RER</dt><dd class="ui-num">{{ formatRating(ratingForGame(item, game)) }}</dd></div>
                <div><dt>SR</dt><dd class="ui-num">{{ item.sr ?? '-' }}</dd></div>
                <div><dt>{{ t('fields.country') }}</dt><dd>{{ countryLabel(t, item.country) }}</dd></div>
              </dl>
              <p class="pc__car"><Car :size="14" /><span>{{ item.car_model }}</span></p>
              <button
                v-if="canRemove"
                class="pc__remove"
                type="button"
                :title="t('raceDetails.removePilot')"
                :aria-label="`${t('raceDetails.removePilot')}: ${name(item)}`"
                :disabled="pending"
                @click="emit('remove', item)"
              >
                <UserMinus :size="16" />
              </button>
            </article>
          </TransitionGroup>
          <EmptyState v-else :icon="Search" compact :title="t('common.noMatches')" />

          <PaginationControls v-if="visible.length" v-model:page="page" :page-size="PAGE_SIZE" :total-items="visible.length" />
        </template>
      </div>
    </Transition>
  </section>
</template>

<style scoped>
.entries__sub {
  margin: 0;
  color: var(--c-text-3);
  font-size: 13px;
}

.entries__head-side {
  display: flex;
  align-items: center;
  gap: 14px;
}

.entries__count {
  color: var(--c-text-3);
  font-size: 15px;
}

.entries__count b {
  color: var(--c-text);
  font-size: 26px;
  font-weight: 700;
}

.entries__stack {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  width: 100%;
  padding: 14px 16px;
  border: 1px dashed var(--c-line-strong);
  border-radius: var(--r-lg);
  background: var(--c-sunken);
  color: var(--c-text-2);
  cursor: pointer;
  font: inherit;
  text-align: left;
  transition: border-color var(--dur-2), background-color var(--dur-2);
}

.entries__stack:hover {
  border-color: var(--c-blue-line);
  background: var(--c-blue-soft);
}

.entries__avatars {
  display: flex;
  align-items: center;
  padding-left: 10px;
}

.entries__stack-avatar,
.entries__more {
  width: 40px;
  height: 40px;
  margin-left: -10px;
  border: 2px solid var(--c-surface-solid);
  transition: transform var(--dur-3) var(--ease-spring);
  transition-delay: calc(var(--i, 0) * 25ms);
}

.entries__stack:hover .entries__stack-avatar {
  transform: translateX(calc(var(--i, 0) * 3px));
}

.entries__more {
  display: inline-grid;
  place-items: center;
  border-radius: 50%;
  background: var(--bm-blue);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
}

.entries__stack-text {
  font-size: 13.5px;
  font-weight: 600;
}

.entries__body {
  display: grid;
  gap: 16px;
}

.entries__tools {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(170px, 230px) auto;
  align-items: center;
  gap: 10px;
}

.entries__search,
.entries__sort {
  position: relative;
  display: grid;
}

.entries__search svg,
.entries__sort svg {
  position: absolute;
  top: 50%;
  left: 14px;
  z-index: 1;
  color: var(--c-text-3);
  pointer-events: none;
  transform: translateY(-50%);
}

.entries__search .ui-input,
.entries__sort .ui-select {
  min-height: 44px;
  padding-left: 42px;
}

.entries__found {
  color: var(--c-text-3);
  font-size: 12.5px;
  white-space: nowrap;
}

.entries__cards {
  position: relative;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 12px;
}

.entries__cards--teams {
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
}

/* Race number board in mono, like a GT door plate. */
.plate {
  display: inline-grid;
  place-items: center;
  min-width: 58px;
  height: 36px;
  padding: 0 10px;
  border: 1.5px solid #0a0f1a;
  border-radius: 9px;
  background: linear-gradient(180deg, #fff, #e6ebf4);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--bm-blue) 60%, transparent);
  color: #070c18;
  font-size: 17px;
  font-weight: 800;
}

/* Ranked entries: a big faint crest in the corner; from silver up the number
   plate is struck in the rank's metal. */
.pc__crest {
  position: absolute;
  top: -26px;
  right: -30px;
  z-index: -1;
  opacity: 0.16;
  transform: rotate(14deg);
}

.pc[data-rank]:not([data-rank='rookie']):not([data-rank='bronze']) .plate {
  border-color: transparent;
  background: var(--rank-metal);
  color: var(--rank-ink);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.5), 0 6px 18px -6px var(--rank-glow);
}

.plate--sm {
  min-width: 52px;
  height: 32px;
  font-size: 15px;
}

.pc {
  position: relative;
  /* Own stacking context: the rank crest sits behind the content. */
  isolation: isolate;
  overflow: hidden;
  display: grid;
  align-content: start;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-lg);
  background: var(--c-surface-solid);
  transition: transform var(--dur-3) var(--ease-ios), border-color var(--dur-2), box-shadow var(--dur-3);
}

.pc:hover {
  border-color: var(--c-blue-line);
  box-shadow: 0 14px 34px color-mix(in srgb, var(--bm-blue) 16%, transparent);
  transform: translateY(-3px);
}

.pc.is-me {
  border-color: var(--c-blue-line);
  background: linear-gradient(160deg, var(--c-blue-soft), var(--c-surface-solid) 60%);
}

.pc__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-right: 34px;
}

.pc__avatar {
  width: 48px;
  height: 48px;
}

.pc__id {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 8px;
  min-width: 0;
}

.pc__name {
  min-width: 0;
  overflow: hidden;
  color: var(--c-text);
  font-size: 15px;
  font-weight: 700;
  text-decoration: none;
  text-overflow: ellipsis;
  white-space: nowrap;
}

a.pc__name:hover {
  color: var(--c-accent-text);
}

.pc__nick {
  color: var(--c-text-3);
  font-size: 12.5px;
}

.pc__me {
  min-height: 20px;
  font-size: 10px;
}

.pc__badges {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.pc__badges :deep(.pilot-roles) {
  margin-inline-start: 0;
}

.pc__team {
  text-decoration: none;
}

a.pc__team:hover {
  border-color: var(--c-blue-line);
  color: var(--c-accent-text);
}

.pc__stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1px;
  margin: 0;
  overflow: hidden;
  border: 1px solid var(--c-line);
  border-radius: var(--r-sm);
  background: var(--c-line);
}

.pc__stats div {
  display: grid;
  gap: 3px;
  padding: 7px 9px;
  background: var(--c-sunken);
}

.pc__stats dt {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 9.5px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.pc__stats dd {
  margin: 0;
  overflow: hidden;
  color: var(--c-text);
  font-size: 13px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pc__car {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 0;
  color: var(--c-text-2);
  font-size: 13px;
}

.pc__car span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pc__remove {
  position: absolute;
  top: 12px;
  right: 12px;
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border: 1px solid color-mix(in srgb, var(--bm-red) 34%, transparent);
  border-radius: 10px;
  background: color-mix(in srgb, var(--bm-red) 10%, transparent);
  color: color-mix(in srgb, var(--bm-red) 80%, var(--c-text));
  cursor: pointer;
  transition: background-color var(--dur-2), transform var(--dur-2) var(--ease-ios);
}

.pc__remove:hover {
  background: color-mix(in srgb, var(--bm-red) 22%, transparent);
}

.pc__remove:active {
  transform: scale(0.94);
}

.pc__remove:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.team {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: start;
  gap: 14px;
  padding: 16px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-lg);
  background: var(--c-surface-solid);
  transition: border-color var(--dur-2), transform var(--dur-3) var(--ease-ios);
}

.team.is-me {
  border-color: var(--c-blue-line);
  background: linear-gradient(160deg, var(--c-blue-soft), var(--c-surface-solid) 60%);
}

.team:hover {
  border-color: var(--c-blue-line);
  transform: translateY(-2px);
}

.team__avatar {
  width: 48px;
  height: 48px;
  border-radius: 14px;
}

.team__main {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.team__main strong {
  font-size: 15px;
}

.team__drivers {
  display: grid;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 13.5px;
}

.team__drivers li {
  display: flex;
  align-items: center;
  gap: 8px;
}

.team__drivers b {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--c-blue-soft);
  color: var(--c-accent-text);
  font-size: 10.5px;
}

.team__car {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--c-text-2);
  font-size: 13px;
}

.race-swap-enter-active,
.race-swap-leave-active {
  transition: opacity var(--dur-2) var(--ease-out), transform var(--dur-3) var(--ease-ios), filter var(--dur-2) var(--ease-out);
}

.race-swap-enter-from {
  opacity: 0;
  filter: blur(6px);
  transform: translateY(10px);
}

.race-swap-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

@media (max-width: 760px) {
  .entries__tools {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .entries__search {
    grid-column: 1 / -1;
  }

  .entries__cards,
  .entries__cards--teams {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (prefers-reduced-motion: reduce) {
  .race-swap-enter-active,
  .race-swap-leave-active {
    transition: none;
  }
}
</style>
