<script setup>
// Home hero: the league's four numbers over the racing lines. The page opens
// straight on them, without a headline.
import { useI18n } from 'vue-i18n'
import CountUp from '../../ui/fx/CountUp.vue'
import RacingLines from '../../ui/fx/RacingLines.vue'

defineProps({
  stats: { type: Object, required: true }
})

const { t } = useI18n()
</script>

<template>
  <section class="hero" aria-labelledby="home-hero-title">
    <RacingLines class="hero__lines" />
    <div class="hero__grid ui-shell ui-shell--wide">
      <!-- The page's heading, for screen readers and search only: nothing is written above the numbers. -->
      <h1 id="home-hero-title" class="visually-hidden">{{ t('home.hero.label') }}</h1>
      <dl class="hero__stats">
        <div v-reveal="{ delay: 120, y: 12 }" class="hero__stat">
          <dt>{{ t('home.stats.pilots') }}</dt>
          <dd><CountUp :value="stats.pilots" /></dd>
        </div>
        <div v-reveal="{ delay: 200, y: 12 }" class="hero__stat">
          <dt>{{ t('home.stats.completed') }}</dt>
          <dd><CountUp :value="stats.completed_races" /></dd>
        </div>
        <div v-reveal="{ delay: 280, y: 12 }" class="hero__stat hero__stat--live">
          <dt><span class="ui-dot ui-dot--green ui-dot--live"></span>{{ t('home.stats.open') }}</dt>
          <dd><CountUp :value="stats.open_races" /></dd>
        </div>
        <div v-reveal="{ delay: 360, y: 12 }" class="hero__stat">
          <dt>{{ t('home.stats.staff') }}</dt>
          <dd><CountUp :value="stats.staff" /></dd>
        </div>
      </dl>
    </div>
  </section>
</template>

<style scoped>
.hero {
  position: relative;
  padding: clamp(14px, 2.4vw, 28px) 0 clamp(18px, 3vw, 28px);
  overflow: hidden;
}

.hero__lines {
  opacity: 0.9;
  -webkit-mask-image: linear-gradient(90deg, transparent, #000 25%, #000 75%, transparent);
  mask-image: linear-gradient(90deg, transparent, #000 25%, #000 75%, transparent);
}

.hero__grid {
  position: relative;
}

.hero__stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: 0;
  border-top: 1px solid var(--c-line);
}

.hero__stat {
  display: grid;
  gap: 6px;
  padding: 16px 20px 4px 0;
}

.hero__stat + .hero__stat {
  padding-left: 20px;
  border-left: 1px solid var(--c-line);
}

.hero__stat dt {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.hero__stat dd {
  margin: 0;
  color: var(--c-text);
  font-size: clamp(26px, 3vw, 38px);
  font-weight: 600;
}

@media (max-width: 680px) {
  .hero__stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .hero__stat:nth-child(3) {
    padding-left: 0;
    border-left: 0;
  }

  .hero__stat:nth-child(n + 3) {
    border-top: 1px solid var(--c-line);
  }
}
</style>
