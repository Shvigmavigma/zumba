<script setup>
// Moderators and admins: pending requests to create a team.
import { useI18n } from 'vue-i18n'
import { Check, ShieldCheck, XCircle } from 'lucide-vue-next'
import LicenseBadge from '../../components/LicenseBadge.vue'
import TeamAvatar from '../../components/TeamAvatar.vue'
import { formatPilotNumber, formatRating, pilotName, ratingForGame } from '../../pilotDisplay'
import { teamStyle } from './teamUtils'

defineProps({
  requests: { type: Array, default: () => [] },
  busy: { type: Object, default: () => ({}) },
  game: { type: String, default: 'ACC' }
})
const emit = defineEmits(['approve', 'reject'])
const { t } = useI18n()

function requester(item) {
  return pilotName(item.requester, item.requester?.nickname || item.requester?.login)
}
</script>

<template>
  <section class="creq ui-card" aria-labelledby="team-create-requests-title">
    <header class="creq__head">
      <span class="creq__icon"><ShieldCheck :size="20" /></span>
      <div class="creq__title">
        <p class="ui-eyebrow">{{ t('teamsPage.requests.eyebrow') }}</p>
        <h2 id="team-create-requests-title">{{ t('teams.creationRequestsTitle') }}</h2>
        <p>{{ t('teams.creationRequestsHint') }}</p>
      </div>
      <span class="ui-chip" :class="{ 'ui-chip--amber': requests.length }">{{ requests.length }}</span>
    </header>

    <TransitionGroup v-if="requests.length" tag="ul" name="ui-list" class="creq__list">
      <li v-for="item in requests" :key="item.id" class="creq__row" :style="teamStyle(item.avatar_color)">
        <TeamAvatar mini class="creq__avatar" :src="item.avatar_url" :color="item.avatar_color" :label="item.name" />
        <span class="creq__main">
          <span class="creq__name"><strong>{{ item.name }}</strong><span class="creq__code">{{ item.abbreviation }}</span></span>
          <span class="creq__by">
            {{ t('teams.requestedBy', { name: requester(item) }) }}
            <LicenseBadge :user="item.requester" :game="game" />
          </span>
        </span>
        <span class="creq__stat">
          <strong class="ui-num">#{{ formatPilotNumber(item.requester?.pilot_number) }}</strong>
          <small class="ui-num">RER {{ formatRating(ratingForGame(item.requester, game)) }}</small>
        </span>
        <span class="creq__actions">
          <button class="ui-btn ui-btn--icon ui-btn--sm creq__approve" type="button" :title="t('teams.approveCreateRequest')" :aria-label="`${t('teams.approveCreateRequest')}: ${item.name}`" :disabled="busy[item.id]" @click="emit('approve', item)">
            <Check :size="16" />
          </button>
          <button class="ui-btn ui-btn--icon ui-btn--sm ui-btn--danger" type="button" :title="t('teams.rejectCreateRequest')" :aria-label="`${t('teams.rejectCreateRequest')}: ${item.name}`" :disabled="busy[item.id]" @click="emit('reject', item)">
            <XCircle :size="16" />
          </button>
        </span>
      </li>
    </TransitionGroup>
    <p v-else class="creq__empty">{{ t('teams.noCreationRequests') }}</p>
  </section>
</template>

<style scoped>
.creq {
  gap: 14px;
}

.creq__head {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
}

.creq__icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border: 1px solid var(--c-blue-line);
  border-radius: 13px;
  background: var(--c-blue-soft);
  color: var(--c-accent-text);
}

.creq__title {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.creq__title h2 {
  margin: 0;
  color: var(--c-text);
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  text-transform: uppercase;
}

.creq__title p:not(.ui-eyebrow) {
  margin: 0;
  color: var(--c-text-3);
  font-size: 13px;
}

.creq__list {
  position: relative;
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.creq__row {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--c-line);
  border-left: 3px solid var(--team);
  border-radius: var(--r-md);
  background: var(--c-sunken);
}

.creq__row.ui-list-leave-active {
  width: 100%;
}

.creq :deep(.creq__avatar.team-avatar) {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  box-shadow: none;
}

.creq__main {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.creq__name {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.creq__name strong {
  overflow: hidden;
  color: var(--c-text);
  font-size: 14.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.creq__code {
  padding: 2px 7px;
  border-radius: 6px;
  background: var(--team);
  color: var(--team-ink);
  font-family: var(--font-display);
  font-size: 10.5px;
  font-weight: 800;
  letter-spacing: 0.12em;
}

.creq__by {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  color: var(--c-text-3);
  font-size: 12.5px;
}

.creq__by :deep(.license-badge) {
  font-size: 10px;
}

.creq__stat {
  display: grid;
  justify-items: end;
  gap: 2px;
}

.creq__stat strong {
  color: var(--c-text);
  font-size: 14px;
}

.creq__stat small {
  color: var(--c-text-3);
  font-size: 11px;
}

.creq__actions {
  display: flex;
  gap: 6px;
}

.creq__approve {
  --btn-bg: color-mix(in srgb, var(--bm-green) 14%, transparent);
  --btn-fg: color-mix(in srgb, var(--bm-green) 85%, var(--c-text));
  --btn-line: color-mix(in srgb, var(--bm-green) 36%, transparent);
}

.creq__empty {
  margin: 0;
  padding: 14px;
  border: 1px dashed var(--c-line-strong);
  border-radius: var(--r-md);
  color: var(--c-text-3);
  font-size: 13.5px;
  text-align: center;
}

@media (max-width: 640px) {
  .creq__head {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .creq__head > .ui-chip {
    display: none;
  }

  .creq__row {
    grid-template-columns: 40px minmax(0, 1fr) auto;
  }

  .creq__stat {
    display: none;
  }
}
</style>
