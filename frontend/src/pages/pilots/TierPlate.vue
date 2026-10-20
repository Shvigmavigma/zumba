<script setup>
// One licence tier of the RER ladder, shown as a small preview of the profile
// banner a pilot gets at that tier: the same carbon plate, glow, living scene,
// rim and crest (see profile/PilotHero.vue), so the ladder reads as "this is
// what you are racing for".
import RankAura from '../../ui/rank/RankAura.vue'
import RankEmblem from '../../ui/rank/RankEmblem.vue'
import RankScene from '../../ui/rank/RankScene.vue'

defineProps({
  /** A step of rankLadder(): the tier with its rank key and position. */
  step: { type: Object, required: true },
  /** The signed-in pilot holds this tier in the selected simulator. */
  mine: { type: Boolean, default: false },
  mineLabel: { type: String, default: '' }
})

const CREST_SIZE = 36
</script>

<template>
  <li class="plate ui-carbon" :class="{ 'is-mine': mine }" :data-rank="step.key">
    <span class="plate__glow" aria-hidden="true"></span>
    <RankScene :rank="step.key" size="card" :seed="step.index + 1" cx="var(--crest-x)" cy="50%" />
    <RankAura :rank="step.key" :seed="step.index + 1" glint />
    <RankEmblem class="plate__crest" :rank="step.key" :size="CREST_SIZE" />
    <span class="plate__text">
      <span class="plate__name rank-text rank-text--adaptive">{{ step.name }}</span>
      <span class="plate__range ui-num">{{ step.tier.min_rating }}–{{ step.tier.max_rating }}</span>
    </span>
    <span v-if="mine" class="plate__mine">{{ mineLabel }}</span>
  </li>
</template>

<style scoped>
.plate {
  /* The crest's centre: the scene of the top tier turns around it. */
  --crest-x: 30px;
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 78px;
  padding: 12px;
  overflow: hidden;
  /* Keeps the scene and the rim's blend inside the plate. */
  isolation: isolate;
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  box-shadow: 0 10px 28px -18px var(--rank-glow);
}

/* The same glow the banner has behind the avatar. */
.plate__glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(70% 130% at 0% 50%, color-mix(in srgb, var(--rank-2) 26%, transparent), transparent 70%);
}

.plate.is-mine {
  border-color: color-mix(in srgb, var(--rank-2) 70%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--rank-2) 45%, transparent), 0 14px 34px -16px var(--rank-glow);
}

.plate__crest,
.plate__text,
.plate__mine {
  position: relative;
  z-index: 3;
}

.plate__text {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.plate__name {
  overflow: hidden;
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 800;
  line-height: 1.2;
  text-overflow: ellipsis;
  text-transform: uppercase;
  white-space: nowrap;
}

.plate__range {
  color: var(--c-text-2);
  font-size: 12px;
  white-space: nowrap;
}

/* A tab hanging from the top edge, clear of the name even when it is long. */
.plate__mine {
  position: absolute;
  top: 0;
  right: 10px;
  padding: 1px 6px 2px;
  border-radius: 0 0 6px 6px;
  background: var(--rank-metal);
  color: var(--rank-ink);
  font-family: var(--font-mono);
  font-size: 9.5px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
</style>
