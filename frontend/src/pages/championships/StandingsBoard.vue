<script setup>
// Championship standings as a timing screen: podium plates for the top three,
// then the full table with points, gap to the leader, pole points, starts and
// best finish. The signed-in pilot's row is highlighted. Each plate wears its
// medal: gold, silver or bronze light, and its place as a big outlined numeral
// in the corner (the same drawn type as the teams' watermarks). The board opens
// folded, on the three plates alone, so that the season's stages below stay in
// sight; the full table unfolds under them on request.
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronDown, Trophy } from 'lucide-vue-next'
import EmptyState from '../../ui/EmptyState.vue'
import CountUp from '../../ui/fx/CountUp.vue'
import LicenseBadge from '../../components/LicenseBadge.vue'
import PaginationControls from '../../components/PaginationControls.vue'
import PilotRoles from '../../components/PilotRoles.vue'
import UserAvatar from '../../components/UserAvatar.vue'
import { formatPilotNumber, formatRating, pilotName, ratingForGame, teamHref, teamShortName } from '../../pilotDisplay'
import { state } from '../../store'
import { STANDINGS_PAGE_SIZE, pluralBucket, rankStandings } from './helpers'
import { useRanks } from '../../useRanks'
import RankAura from '../../ui/rank/RankAura.vue'

const props = defineProps({
  standings: { type: Array, default: () => [] },
  game: { type: String, default: 'ACC' },
  /** Approved registrations: the car each pilot entered with. */
  registrations: { type: Array, default: () => [] }
})
const page = defineModel('page', { type: Number, default: 1 })
const expanded = defineModel('expanded', { type: Boolean, default: false })

const { t } = useI18n()
const { rankOf } = useRanks()
const pageSize = STANDINGS_PAGE_SIZE

const ranked = computed(() => rankStandings(props.standings))
const totalPages = computed(() => Math.max(1, Math.ceil(ranked.value.length / pageSize)))
const rows = computed(() => ranked.value.slice((page.value - 1) * pageSize, page.value * pageSize))
const podium = computed(() => ranked.value.slice(0, 3))
const cars = computed(() => new Map(props.registrations.map((item) => [item.user_id, item.car_model])))
const countLabel = computed(() => `${ranked.value.length} ${t(`champPage.standings.pilot${pluralBucket(ranked.value.length, state.locale)}`)}`)

watch(() => props.standings, () => {
  if (page.value > totalPages.value) page.value = totalPages.value
})

function title(pilot) {
  return pilotName(pilot, pilot.login)
}

function carOf(userId) {
  return cars.value.get(userId) || '—'
}

function isMe(pilot) {
  return Boolean(state.user && state.user.id === pilot.user_id)
}
</script>

<template>
  <section class="board ui-card" aria-labelledby="champ-standings-title">
    <header class="ui-card__head">
      <div class="ui-card__title">
        <span class="ui-eyebrow ui-eyebrow--accent">{{ t('champPage.standings.eyebrow') }}</span>
        <h3 id="champ-standings-title">{{ t('championships.standings') }}</h3>
      </div>
      <div v-if="ranked.length" class="board__tools">
        <span class="ui-chip">{{ countLabel }}</span>
        <button
          class="ui-btn ui-btn--sm board__toggle"
          :class="expanded ? 'ui-btn--outline' : 'ui-btn--primary'"
          type="button"
          :aria-expanded="expanded"
          aria-controls="champ-standings-table"
          @click="expanded = !expanded"
        >
          {{ expanded ? t('champPage.standings.collapse') : t('champPage.standings.expand') }}
          <ChevronDown class="board__chevron" :size="15" aria-hidden="true" />
        </button>
      </div>
    </header>

    <template v-if="ranked.length">
      <ol class="board__podium" :aria-label="t('champPage.standings.podium')">
        <li
          v-for="pilot in podium"
          :key="pilot.user_id"
          v-reveal="{ delay: (pilot.rank === 1 ? 0 : pilot.rank) * 110, y: 22 }"
          class="board__step"
          :class="`is-p${pilot.rank}`"
        >
          <RouterLink v-tilt="5" class="plate" :class="[`plate--p${pilot.rank}`, { 'is-me': isMe(pilot) }]" :to="`/pilots/${pilot.user_id}`">
            <span class="ui-glare"></span>
            <span class="plate__numeral ui-outline-text" aria-hidden="true">{{ pilot.rank }}</span>
            <span class="plate__top">
              <span class="plate__place">
                <Trophy v-if="pilot.rank === 1" class="plate__trophy" :size="15" aria-hidden="true" />
                {{ t(`champPage.standings.place${pilot.rank}`) }}
              </span>
            </span>
            <span class="plate__who">
              <UserAvatar mini class="ui-avatar-md plate__avatar rank-avatar" :data-rank="rankOf(pilot)" :src="pilot.avatar_url" :color="pilot.avatar_color" :label="title(pilot)" />
              <span class="plate__name">
                <strong>{{ title(pilot) }}</strong>
                <small><LicenseBadge :user="pilot" :game="game" /> #{{ formatPilotNumber(pilot.pilot_number) }} · {{ teamShortName(pilot.team_name, pilot.team_abbreviation) !== '-' ? teamShortName(pilot.team_name, pilot.team_abbreviation) : t('championships.noTeam') }}</small>
              </span>
            </span>
            <span class="plate__score">
              <span class="plate__points"><CountUp :value="pilot.points" /><small>{{ t('champPage.standings.pts') }}</small></span>
              <span class="plate__gap ui-num">{{ pilot.rank === 1 ? t('champPage.standings.leader') : `−${pilot.gap}` }}</span>
            </span>
          </RouterLink>
        </li>
      </ol>

      <div id="champ-standings-table" class="board__more" :class="{ 'is-open': expanded }" :inert="!expanded || null">
        <div class="board__more-in">
          <div class="ui-table-wrap board__wrap">
            <table class="ui-table board__table">
              <thead>
                <tr>
                  <th class="is-center" scope="col">{{ t('champPage.standings.pos') }}</th>
                  <th scope="col">{{ t('championships.pilot') }}</th>
                  <th class="col-sm" scope="col">{{ t('championships.team') }}</th>
                  <th class="col-md" scope="col">{{ t('championships.car') }}</th>
                  <th class="is-num col-sm" scope="col">{{ t('championships.starts') }}</th>
                  <th class="is-num col-sm" scope="col">{{ t('champPage.standings.best') }}</th>
                  <th class="is-num col-sm" scope="col">{{ t('championships.pole') }}</th>
                  <th class="is-num col-md" scope="col">RER</th>
                  <th class="is-num col-md" scope="col">SR</th>
                  <th class="is-num col-xs" scope="col">{{ t('champPage.standings.gap') }}</th>
                  <th class="is-num" scope="col">{{ t('championships.points') }}</th>
                </tr>
              </thead>
              <!-- A new tbody on every unfold, so the rows fade in one after another again. -->
              <tbody :key="`${page}-${expanded}`">
                <tr v-for="(pilot, index) in rows" :key="pilot.user_id" class="board__row rank-surface" :class="{ 'is-me': isMe(pilot), [`is-p${pilot.rank}`]: pilot.rank <= 3 }" :data-rank="rankOf(pilot)" :style="{ '--i': index }">
                  <td class="is-center"><RankAura :rank="rankOf(pilot)" :seed="pilot.user_id" />
                    <span class="ui-pos" :class="pilot.rank <= 3 ? `ui-pos--${pilot.rank}` : ''">{{ pilot.rank }}</span>
                  </td>
                  <td>
                    <div class="board__person">
                      <UserAvatar mini class="ui-avatar-sm rank-avatar" :data-rank="rankOf(pilot)" :src="pilot.avatar_url" :color="pilot.avatar_color" :label="title(pilot)" />
                      <RouterLink class="board__name" :to="`/pilots/${pilot.user_id}`">
                        <span class="board__name-line">
                          <strong class="rank-name" :data-rank="rankOf(pilot)">{{ title(pilot) }}</strong>
                          <LicenseBadge :user="pilot" :game="game" />
                          <PilotRoles :roles="pilot.pilot_roles" />
                          <span v-if="isMe(pilot)" class="ui-chip ui-chip--blue board__me">{{ t('champPage.standings.you') }}</span>
                        </span>
                        <span class="board__sub ui-num">#{{ formatPilotNumber(pilot.pilot_number) }} · {{ pilot.nickname || pilot.login }}</span>
                      </RouterLink>
                    </div>
                  </td>
                  <td class="col-sm">
                    <RouterLink v-if="pilot.team_id" class="ui-chip ui-chip--blue board__team" :to="teamHref(pilot.team_id)" :title="pilot.team_name || ''">
                      {{ teamShortName(pilot.team_name, pilot.team_abbreviation) }}
                    </RouterLink>
                    <span v-else class="board__faint">{{ t('championships.noTeam') }}</span>
                  </td>
                  <td class="col-md board__car">{{ carOf(pilot.user_id) }}</td>
                  <td class="is-num col-sm">{{ pilot.starts }}</td>
                  <td class="is-num col-sm">{{ pilot.best_finish ? `P${pilot.best_finish}` : '—' }}</td>
                  <td class="is-num col-sm">{{ pilot.pole_points }}</td>
                  <td class="is-num col-md">{{ formatRating(ratingForGame(pilot, game)) }}</td>
                  <td class="is-num col-md">{{ Number(pilot.sr).toFixed(1) }}</td>
                  <td class="is-num col-xs board__gap">{{ pilot.rank === 1 ? '—' : `−${pilot.gap}` }}</td>
                  <td class="is-num board__points">{{ pilot.points }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <PaginationControls v-model:page="page" class="board__pages" :page-size="pageSize" :total-items="ranked.length" />
        </div>
      </div>
    </template>

    <EmptyState v-else :icon="Trophy" :title="t('champPage.standings.emptyTitle')" :text="t('championships.standingsEmpty')" compact />
  </section>
</template>

<style scoped>
.board {
  min-width: 0;
}

/* ---------- Podium ---------- */
.board__podium {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  align-items: end;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.board__step.is-p1 {
  order: 2;
}

.board__step.is-p2 {
  order: 1;
}

.board__step.is-p3 {
  order: 3;
}

/* Silver by default; gold and bronze below. --light is where the medal's light falls from. */
.plate {
  --medal: var(--bm-silver);
  --light: 0% 0%;
  position: relative;
  /* The outlined numeral blends against the plate's own background, not the page. */
  isolation: isolate;
  display: grid;
  gap: 14px;
  min-height: 176px;
  padding: 18px 20px 16px;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--medal) 34%, var(--c-line));
  border-radius: var(--r-lg);
  background:
    radial-gradient(120% 90% at var(--light), color-mix(in srgb, var(--medal) 20%, transparent), transparent 62%),
    repeating-linear-gradient(118deg, transparent 0 16px, color-mix(in srgb, var(--medal) 5%, transparent) 16px 17px),
    var(--c-surface-solid);
  color: var(--c-text);
  text-decoration: none;
  transition: border-color var(--dur-2), box-shadow var(--dur-3) var(--ease-out);
}

/* The medal's band along the top edge. */
.plate::before {
  position: absolute;
  inset: 0 0 auto;
  z-index: 1;
  height: 3px;
  background: linear-gradient(90deg, var(--medal), color-mix(in srgb, var(--medal) 15%, transparent) 85%);
  content: '';
}

.plate > :not(.plate__numeral, .ui-glare) {
  position: relative;
  z-index: 1;
}

/* The place, drawn in outline, leaning forward like a race number and just touching the plate's top edge.
   Unbounded has no italic of its own: the slant is a skew, so it is the same in every browser. */
.plate__numeral {
  --outline-color: color-mix(in srgb, var(--medal) 62%, transparent);
  --outline-width: 1.5px;
  --lean: skewX(-12deg);
  position: absolute;
  top: -0.06em;
  right: 0.14em;
  z-index: 0;
  font-family: var(--font-display);
  font-size: clamp(116px, 10vw, 156px);
  font-weight: 800;
  line-height: 1;
  pointer-events: none;
  user-select: none;
  transform: var(--lean);
  transform-origin: 50% 100%;
  transition: transform var(--dur-4) var(--ease-out);
}

:root[data-theme='light'] .plate__numeral {
  color: #fff;
  mix-blend-mode: multiply;
}

.plate:hover .plate__numeral {
  transform: translate(-4px, 4px) var(--lean);
}

.plate:hover {
  border-color: color-mix(in srgb, var(--medal) 60%, transparent);
  box-shadow: 0 18px 40px color-mix(in srgb, var(--medal) 18%, transparent);
}

/* The leader: gold, the tallest, light from above and a warm glow underneath. */
.plate--p1 {
  --medal: var(--bm-gold);
  --light: 60% 0%;
  min-height: 212px;
  border-color: color-mix(in srgb, var(--bm-gold) 52%, var(--c-line));
  background:
    radial-gradient(120% 90% at var(--light), color-mix(in srgb, var(--medal) 26%, transparent), transparent 62%),
    radial-gradient(70% 60% at 0% 100%, color-mix(in srgb, var(--medal) 12%, transparent), transparent 70%),
    repeating-linear-gradient(118deg, transparent 0 16px, color-mix(in srgb, var(--medal) 6%, transparent) 16px 17px),
    var(--c-surface-solid);
  box-shadow: 0 22px 56px color-mix(in srgb, var(--bm-gold) 18%, transparent), inset 0 1px 0 color-mix(in srgb, var(--bm-gold) 30%, transparent);
}

.plate--p1 .plate__numeral {
  --outline-color: color-mix(in srgb, var(--bm-gold) 78%, transparent);
  font-size: clamp(136px, 12vw, 188px);
}

/* Silver: cool light from the left. */
.plate--p2 {
  --light: 0% 0%;
}

/* Bronze: warm light from the right. */
.plate--p3 {
  --medal: var(--bm-bronze);
  --light: 100% 0%;
}

.plate__place {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: color-mix(in srgb, var(--medal) 78%, var(--c-text));
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.plate.is-me {
  outline: 2px solid var(--bm-blue-bright);
  outline-offset: 2px;
}

.plate__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.plate__trophy {
  color: var(--bm-gold);
  filter: drop-shadow(0 0 10px color-mix(in srgb, var(--bm-gold) 60%, transparent));
}

.plate__who {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 12px;
}

.plate__name {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.plate__name strong {
  overflow: hidden;
  font-size: 15px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.plate__name small {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow: hidden;
  color: var(--c-text-3);
  font-size: 12px;
  white-space: nowrap;
}

.plate__score {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  align-self: end;
}

.plate__points {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  color: var(--c-text);
  font-size: 34px;
  font-weight: 600;
  line-height: 1;
}

.plate--p1 .plate__points {
  font-size: 42px;
}

.plate__points small {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

/* Points behind the leader, or the leader's own mark, as a pill in the medal's colour. */
.plate__gap {
  padding: 3px 10px;
  border: 1px solid color-mix(in srgb, var(--medal) 38%, transparent);
  border-radius: var(--r-pill);
  background: color-mix(in srgb, var(--medal) 10%, transparent);
  color: var(--c-text-2);
  font-family: var(--font-mono);
  font-size: 12.5px;
  font-weight: 700;
}

.plate--p1 .plate__gap {
  border-color: color-mix(in srgb, var(--bm-gold) 60%, transparent);
  background: color-mix(in srgb, var(--bm-gold) 22%, transparent);
  color: color-mix(in srgb, var(--bm-gold) 85%, var(--c-text));
  font-size: 10.5px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

/* ---------- Table ---------- */
/* Only opacity, and nothing left on the row afterwards: see the race results table (ResultsTable.vue). */
.board__row {
  animation: board-row-in 560ms var(--ease-out) backwards;
  animation-delay: calc(var(--i) * 28ms);
}

.board__row.is-p1 td:first-child {
  box-shadow: inset 3px 0 0 var(--bm-gold);
}

.board__row.is-p2 td:first-child {
  box-shadow: inset 3px 0 0 var(--bm-silver);
}

.board__row.is-p3 td:first-child {
  box-shadow: inset 3px 0 0 var(--bm-bronze);
}

.board__row.is-me {
  background: color-mix(in srgb, var(--bm-blue) 12%, transparent);
}

.board__person {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 220px;
}

.board__name {
  display: grid;
  gap: 2px;
  min-width: 0;
  color: var(--c-text);
  text-decoration: none;
}

.board__name:hover strong {
  color: var(--c-accent-text);
}

.board__name-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 8px;
}

.board__name-line strong {
  font-size: 14px;
  font-weight: 650;
  transition: color var(--dur-2);
}

.board__me {
  min-height: 20px;
  padding: 0 8px;
  font-size: 10px;
}

.board__sub {
  color: var(--c-text-3);
  font-size: 12px;
}

.board__team {
  min-height: 24px;
  text-decoration: none;
}

.board__faint {
  color: var(--c-text-3);
  font-size: 12.5px;
  white-space: nowrap;
}

.board__car {
  max-width: 220px;
  color: var(--c-text-2);
  font-size: 13px;
}

.board__gap {
  color: var(--c-text-2);
}

.board__points {
  color: var(--c-text);
  font-size: 17px;
  font-weight: 700;
}

.board__pages {
  justify-self: center;
}

.board__tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.board__chevron {
  transition: transform var(--dur-3) var(--ease-ios);
}

.board__toggle[aria-expanded='true'] .board__chevron {
  transform: rotate(180deg);
}

/* The table under the plates: folded to nothing (the card's gap included) until asked for. */
.board__more {
  display: grid;
  /* Not stretched over the gap it takes back with the negative margin. */
  align-self: start;
  grid-template-rows: 0fr;
  margin-top: -16px;
  opacity: 0;
  transition:
    grid-template-rows var(--dur-4) var(--ease-ios),
    margin-top var(--dur-4) var(--ease-ios),
    opacity var(--dur-3) var(--ease-out);
}

.board__more.is-open {
  grid-template-rows: 1fr;
  margin-top: 0;
  opacity: 1;
}

.board__more-in {
  display: grid;
  gap: 16px;
  min-height: 0;
  overflow: clip;
}

.board__more.is-open .board__more-in {
  overflow-clip-margin: 6px;
}

.board :deep(.license-badge) {
  flex: 0 0 auto;
  font-size: 10px;
}

@keyframes board-row-in {
  from {
    opacity: 0;
  }
}

@media (max-width: 1100px) {
  .col-md {
    display: none;
  }
}

@media (max-width: 860px) {
  .board__podium {
    grid-template-columns: minmax(0, 1fr);
  }

  .board__step.is-p1,
  .board__step.is-p2,
  .board__step.is-p3 {
    order: 0;
  }

  .plate,
  .plate--p1 {
    min-height: 0;
  }

  .plate__points,
  .plate--p1 .plate__points {
    font-size: 30px;
  }

  .plate__numeral,
  .plate--p1 .plate__numeral {
    font-size: 104px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .plate__numeral,
  .board__more,
  .board__chevron {
    transition: none;
  }
}

@media (max-width: 760px) {
  .col-sm {
    display: none;
  }

  .board__person {
    min-width: 0;
  }
}

@media (max-width: 420px) {
  .col-xs {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .board__row {
    animation: none;
  }
}
</style>
