<script setup>
// Bar above an open team: back to the grid, plus a pit-lane strip of every
// team's abbreviation to jump straight to another garage.
import { nextTick, ref, useId, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { motion } from 'motion-v'
import { ArrowLeft } from 'lucide-vue-next'
import { teamShortName } from '../../pilotDisplay'
import { teamStyle } from './teamUtils'

const props = defineProps({
  teams: { type: Array, default: () => [] },
  currentId: { type: Number, default: null },
  busy: { type: Object, default: () => ({}) }
})
const emit = defineEmits(['select', 'back'])
const { t } = useI18n()
const strip = ref(null)
const pillId = `team-switch-${useId()}`
const spring = { type: 'spring', stiffness: 480, damping: 38, mass: 0.9 }

function centerActive() {
  const active = strip.value?.querySelector('.is-active')
  if (!active || !strip.value) return
  const left = active.offsetLeft - (strip.value.clientWidth - active.offsetWidth) / 2
  strip.value.scrollTo({ left: Math.max(0, left), behavior: 'smooth' })
}

watch(() => props.currentId, () => nextTick(centerActive), { immediate: true })
</script>

<template>
  <div class="switch-bar">
    <button class="ui-btn ui-btn--outline ui-btn--sm switch-bar__back" type="button" @click="emit('back')">
      <ArrowLeft :size="16" />{{ t('teamsPage.detail.back') }}
    </button>
    <nav v-if="teams.length > 1" ref="strip" class="switch-bar__strip" :aria-label="t('teamsPage.detail.switcher')">
      <button
        v-for="team in teams"
        :key="team.id"
        class="switch-bar__team"
        :class="{ 'is-active': team.id === currentId, 'is-busy': busy[team.id] }"
        type="button"
        :style="teamStyle(team.avatar_color)"
        :title="team.name"
        :aria-current="team.id === currentId ? 'true' : null"
        :disabled="busy[team.id]"
        @click="team.id !== currentId && emit('select', team)"
      >
        <motion.span v-if="team.id === currentId" class="switch-bar__pill" :layoutId="pillId" :transition="spring" />
        <span class="switch-bar__dot"></span>
        <span class="switch-bar__code">{{ teamShortName(team.name, team.abbreviation) }}</span>
      </button>
    </nav>
  </div>
</template>

<style scoped>
.switch-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.switch-bar__back {
  flex: 0 0 auto;
}

.switch-bar__strip {
  display: flex;
  flex: 1 1 auto;
  gap: 4px;
  min-width: 0;
  padding: 4px;
  overflow-x: auto;
  border: 1px solid var(--c-line);
  border-radius: var(--r-pill);
  background: var(--c-sunken);
  scrollbar-width: none;
  -webkit-mask-image: linear-gradient(90deg, transparent, #000 16px, #000 calc(100% - 16px), transparent);
  mask-image: linear-gradient(90deg, transparent, #000 16px, #000 calc(100% - 16px), transparent);
}

.switch-bar__strip::-webkit-scrollbar {
  display: none;
}

.switch-bar__team {
  position: relative;
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 7px;
  min-height: 30px;
  padding: 0 12px;
  border: 0;
  border-radius: var(--r-pill);
  background: transparent;
  color: var(--c-text-2);
  cursor: pointer;
  transition: color var(--dur-2) var(--ease-out), opacity var(--dur-2);
  -webkit-tap-highlight-color: transparent;
}

.switch-bar__team:hover {
  color: var(--c-text);
}

.switch-bar__team.is-active {
  color: var(--team-ink);
  cursor: default;
}

.switch-bar__team.is-busy {
  opacity: 0.55;
  cursor: progress;
}

.switch-bar__pill {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: var(--team);
  box-shadow: 0 6px 18px -6px var(--team), inset 0 1px 0 rgba(255, 255, 255, 0.22);
}

.switch-bar__dot {
  position: relative;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--team);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--c-text) 18%, transparent);
}

.switch-bar__team.is-active .switch-bar__dot {
  background: var(--team-ink);
  box-shadow: none;
}

.switch-bar__code {
  position: relative;
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
}

@media (max-width: 560px) {
  .switch-bar {
    flex-wrap: wrap;
  }

  .switch-bar__strip {
    flex-basis: 100%;
  }
}
</style>
