<script setup>
// A team "garage" card: livery band painted in the team colour, abbreviation
// in the wide display font, average rating and a seat meter. Also used as a
// live preview inside the team forms (`preview`).
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowUpRight, Bell, Crown } from 'lucide-vue-next'
import TeamAvatar from '../../components/TeamAvatar.vue'
import CountUp from '../../ui/fx/CountUp.vue'
import { formatRating, teamShortName } from '../../pilotDisplay'
import SeatMeter from './SeatMeter.vue'
import { isBrightTeamColor, isTeamFull, teamStyle } from './teamUtils'

const props = defineProps({
  team: { type: Object, required: true },
  busy: { type: Boolean, default: false },
  preview: { type: Boolean, default: false }
})
const emit = defineEmits(['open'])
const { t } = useI18n()

const abbreviation = computed(() => teamShortName(props.team.name, props.team.abbreviation))
const full = computed(() => isTeamFull(props.team))
const hasDarkInk = computed(() => isBrightTeamColor(props.team.avatar_color))
const owner = computed(() => props.team.owner_nickname || props.team.owner_login || t('teams.noOwner'))
const pendingTitle = computed(() => t('teams.pendingApplicationsNotice', { count: props.team.pending_application_count || 0 }))
const showApplication = computed(() => props.team.my_application_status === 'pending' && !props.team.is_member)
</script>

<template>
  <div v-tilt="5" class="tcard-tilt" :class="{ 'is-preview': preview }">
    <article
      v-spotlight
      class="tcard"
      :class="{ 'is-mine': team.is_member, 'is-full': full, 'is-busy': busy, 'is-preview': preview }"
      :style="teamStyle(team.avatar_color)"
      :aria-busy="busy || null"
    >
      <div class="tcard__livery" aria-hidden="true">
        <span class="tcard__stripes"></span>
        <span class="tcard__abbr ui-outline-text" :class="{ 'ui-outline-text--dark-ink': hasDarkInk }">{{ abbreviation }}</span>
        <span v-if="busy" class="tcard__progress"></span>
      </div>

      <div class="tcard__flags">
        <span v-if="team.pending_application_count > 0" class="ui-chip ui-chip--red tcard__bell" :title="pendingTitle" :aria-label="pendingTitle">
          <Bell :size="12" />{{ team.pending_application_count }}
        </span>
        <span v-if="team.is_owner" class="ui-chip ui-chip--blue">{{ t('teamsPage.card.owner') }}</span>
        <span v-else-if="team.is_member" class="ui-chip ui-chip--green">{{ t('teamsPage.card.mine') }}</span>
        <span v-else-if="showApplication" class="ui-chip ui-chip--amber">{{ t('teams.applicationStatuses.pending') }}</span>
        <span v-if="full && !preview" class="ui-chip">{{ t('teamsPage.card.full') }}</span>
      </div>

      <div class="tcard__who">
        <TeamAvatar class="tcard__avatar" :src="team.avatar_url" :color="team.avatar_color" :label="team.name || t('teams.newTeam')" />
        <span class="tcard__code">{{ abbreviation }}</span>
        <span v-if="!preview" class="tcard__go" aria-hidden="true"><ArrowUpRight :size="16" /></span>
      </div>

      <div class="tcard__text">
        <h3 class="tcard__name">{{ team.name || t('teams.newTeam') }}</h3>
        <p class="tcard__owner"><Crown :size="13" />{{ owner }}</p>
        <p class="tcard__desc">{{ team.description || t('teams.noDescription') }}</p>
      </div>

      <dl class="tcard__stats">
        <div class="tcard__stat">
          <dt>{{ t('teamsPage.card.rating') }}</dt>
          <dd class="tcard__rating"><CountUp :value="formatRating(team.average_rating)" /></dd>
        </div>
        <div class="tcard__stat tcard__stat--seats">
          <dt>{{ t('teamsPage.card.roster') }}</dt>
          <dd class="ui-num"><strong>{{ team.member_count }}</strong>/{{ team.member_limit }}</dd>
          <SeatMeter class="tcard__meter" :count="team.member_count" :limit="team.member_limit" :label="t('teams.membersCount', { count: team.member_count, limit: team.member_limit })" />
        </div>
      </dl>

      <button
        v-if="!preview"
        class="tcard__hit"
        type="button"
        :disabled="busy"
        :aria-label="t('teamsPage.card.open', { name: team.name })"
        @click="emit('open', team)"
      ></button>
    </article>
    <span class="ui-glare" aria-hidden="true"></span>
  </div>
</template>

<style scoped>
.tcard-tilt {
  position: relative;
  height: 100%;
  border-radius: var(--r-xl);
}

.tcard {
  --team-vis: color-mix(in srgb, var(--team) 74%, var(--c-text) 26%);
  position: relative;
  display: grid;
  grid-template-rows: auto auto auto 1fr auto;
  height: 100%;
  padding-bottom: 18px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-xl);
  background: var(--c-surface);
  box-shadow: var(--shadow-1);
  -webkit-backdrop-filter: var(--glass-filter);
  backdrop-filter: var(--glass-filter);
  transition:
    transform var(--dur-3) var(--ease-ios),
    box-shadow var(--dur-3) var(--ease-out),
    border-color var(--dur-3) var(--ease-out);
}

.tcard:not(.is-preview):hover {
  border-color: color-mix(in srgb, var(--team-vis) 45%, var(--c-line));
  box-shadow:
    var(--shadow-1),
    0 22px 48px -18px color-mix(in srgb, var(--team) 60%, transparent);
  transform: translateY(-4px);
}

.tcard.is-mine {
  border-color: color-mix(in srgb, var(--bm-green) 40%, var(--c-line));
}

/* ---------- Livery band ---------- */
.tcard__livery {
  position: relative;
  height: 104px;
  overflow: hidden;
  border-radius: calc(var(--r-xl) - 1px) calc(var(--r-xl) - 1px) 0 0;
  background:
    radial-gradient(130% 160% at 100% 0%, color-mix(in srgb, var(--team) 42%, transparent), transparent 62%),
    color-mix(in srgb, var(--team) 12%, var(--c-surface-solid));
}

.tcard__livery::after {
  position: absolute;
  inset: auto 0 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, color-mix(in srgb, var(--team-vis) 60%, transparent), transparent);
  content: '';
}

.tcard__stripes {
  position: absolute;
  inset: 0 -60px 0 -20px;
  background: linear-gradient(
    116deg,
    transparent 0 44%,
    var(--team) 44% 61%,
    transparent 61% 64.5%,
    color-mix(in srgb, var(--team) 70%, #fff 30%) 64.5% 68%,
    transparent 68%
  );
  opacity: 0.92;
  transition: transform 900ms var(--ease-ios);
}

.tcard:not(.is-preview):hover .tcard__stripes {
  transform: translateX(-36px);
}

.tcard__abbr {
  position: absolute;
  right: 14px;
  bottom: -18px;
  /* Drawn by .ui-outline-text: the livery band behind it is opaque. */
  --outline-color: color-mix(in srgb, var(--team-ink) 55%, transparent);
  font-family: var(--font-display);
  font-size: 78px;
  font-weight: 800;
  letter-spacing: 0.02em;
  line-height: 1;
  transition: transform 900ms var(--ease-ios), letter-spacing 900ms var(--ease-ios);
}

.tcard:not(.is-preview):hover .tcard__abbr {
  letter-spacing: 0.08em;
  transform: translateX(-6px);
}

.tcard__progress {
  position: absolute;
  inset: auto 0 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--bm-cyan), transparent);
  animation: tcard-progress 1s linear infinite;
}

/* ---------- Flags ---------- */
.tcard__flags {
  position: absolute;
  top: 12px;
  left: 12px;
  right: 12px;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
  pointer-events: none;
}

.tcard__flags .ui-chip {
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
}

.tcard__flags .ui-chip:not(.ui-chip--red):not(.ui-chip--blue):not(.ui-chip--green):not(.ui-chip--amber) {
  --chip-bg: color-mix(in srgb, var(--c-surface-solid) 70%, transparent);
}

.tcard__bell {
  animation: tcard-ring 2.8s var(--ease-out) infinite;
}

/* ---------- Identity ---------- */
.tcard__who {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  margin-top: -30px;
  padding: 0 18px;
}

.tcard__avatar {
  position: relative;
  z-index: 1;
}

.tcard :deep(.tcard__avatar.team-avatar) {
  width: 60px;
  height: 60px;
  border: 2px solid color-mix(in srgb, var(--team-vis) 60%, var(--c-line-strong));
  border-radius: 18px;
  box-shadow: 0 0 0 4px var(--c-surface-solid), 0 12px 24px -8px color-mix(in srgb, var(--team) 70%, transparent);
  transition: transform var(--dur-3) var(--ease-spring);
}

.tcard:not(.is-preview):hover :deep(.tcard__avatar.team-avatar) {
  transform: translateY(-3px) rotate(-3deg);
}

.tcard__code {
  padding: 4px 9px;
  border-radius: 8px;
  background: var(--team);
  color: var(--team-ink);
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  line-height: 1.1;
}

.tcard__go {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  margin-left: auto;
  border: 1px solid var(--c-line-strong);
  border-radius: 50%;
  color: var(--c-text-2);
  transition:
    transform var(--dur-3) var(--ease-spring),
    background-color var(--dur-2),
    color var(--dur-2),
    border-color var(--dur-2);
}

.tcard:hover .tcard__go {
  border-color: transparent;
  background: var(--bm-blue);
  color: #fff;
  transform: rotate(45deg);
}

/* ---------- Text ---------- */
.tcard__text {
  display: grid;
  align-content: start;
  gap: 6px;
  min-width: 0;
  padding: 14px 18px 0;
}

.tcard__name {
  margin: 0;
  overflow: hidden;
  color: var(--c-text);
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0;
  line-height: 1.2;
  text-overflow: ellipsis;
  text-transform: uppercase;
  white-space: nowrap;
}

.tcard__owner {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  overflow: hidden;
  color: var(--c-text-2);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tcard__owner svg {
  flex: 0 0 auto;
  color: var(--bm-gold);
}

.tcard__desc {
  display: -webkit-box;
  margin: 2px 0 0;
  overflow: hidden;
  color: var(--c-text-3);
  font-size: 13px;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

/* ---------- Stats ---------- */
.tcard__stats {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: end;
  gap: 18px;
  margin: 16px 18px 0;
  padding-top: 14px;
  border-top: 1px solid var(--c-line);
}

.tcard__stat {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.tcard__stat dt {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.tcard__stat dd {
  margin: 0;
}

.tcard__rating {
  color: var(--c-text);
  font-size: 24px;
  font-weight: 600;
  line-height: 1;
}

.tcard__stat--seats {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: baseline;
}

.tcard__stat--seats dd {
  color: var(--c-text-3);
  font-size: 13px;
}

.tcard__stat--seats dd strong {
  color: var(--c-text);
  font-size: 15px;
  font-weight: 600;
}

.tcard__meter {
  grid-column: 1 / -1;
  margin-top: 6px;
}

/* ---------- Hit area ---------- */
.tcard__hit {
  position: absolute;
  inset: 0;
  z-index: 2;
  width: 100%;
  padding: 0;
  border: 0;
  border-radius: inherit;
  background: transparent;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.tcard__hit:disabled {
  cursor: progress;
}

.tcard__hit:focus-visible {
  outline: 2px solid var(--bm-blue-bright);
  outline-offset: 3px;
}

.tcard:not(.is-preview):active {
  transform: translateY(-2px) scale(0.985);
}

@keyframes tcard-progress {
  from {
    transform: translateX(-100%);
  }
  to {
    transform: translateX(100%);
  }
}

@keyframes tcard-ring {
  0%,
  70%,
  100% {
    transform: rotate(0);
  }
  74% {
    transform: rotate(-8deg);
  }
  80% {
    transform: rotate(7deg);
  }
  86% {
    transform: rotate(-4deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .tcard,
  .tcard__stripes,
  .tcard__abbr,
  .tcard__go {
    transition: none;
  }

  .tcard__bell,
  .tcard__progress {
    animation: none;
  }
}
</style>
