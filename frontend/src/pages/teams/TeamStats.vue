<script setup>
// Header telemetry for the listed teams: how many, pilots on rosters, open seats.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import CountUp from '../../ui/fx/CountUp.vue'
import { freeSeats } from './teamUtils'

const props = defineProps({
  teams: { type: Array, default: () => [] }
})
const { t } = useI18n()

const pilots = computed(() => props.teams.reduce((sum, team) => sum + (Number(team.member_count) || 0), 0))
const seats = computed(() => props.teams.reduce((sum, team) => sum + freeSeats(team), 0))
</script>

<template>
  <dl class="tstats" :aria-label="t('teamsPage.stats.label')">
    <div>
      <dt>{{ t('teamsPage.stats.teams') }}</dt>
      <dd><CountUp :value="teams.length" /></dd>
    </div>
    <div>
      <dt>{{ t('teamsPage.stats.pilots') }}</dt>
      <dd><CountUp :value="pilots" /></dd>
    </div>
    <div>
      <dt>{{ t('teamsPage.stats.seats') }}</dt>
      <dd class="is-accent"><CountUp :value="seats" /></dd>
    </div>
  </dl>
</template>

<style scoped>
.tstats {
  display: grid;
  grid-template-columns: repeat(3, auto);
  gap: 1px;
  margin: 0;
  overflow: hidden;
  border: 1px solid var(--c-line);
  border-radius: var(--r-lg);
  background: var(--c-line);
}

.tstats > div {
  display: grid;
  gap: 4px;
  padding: 12px 18px;
  background: var(--c-surface-solid);
}

.tstats dt {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  white-space: nowrap;
}

.tstats dd {
  margin: 0;
  color: var(--c-text);
  font-size: 26px;
  font-weight: 600;
  line-height: 1;
}

.tstats dd.is-accent {
  color: var(--c-accent-text);
}

@media (max-width: 760px) {
  .tstats {
    width: 100%;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .tstats > div {
    padding: 10px 12px;
  }

  .tstats dt {
    white-space: normal;
  }

  .tstats dd {
    font-size: 21px;
  }
}
</style>
