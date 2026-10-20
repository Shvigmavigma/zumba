<script setup>
// Published car setups. The section header stays visible with an empty state
// whenever the admin has the section switched on.
import { useI18n } from 'vue-i18n'
import { Wrench } from 'lucide-vue-next'
import EmptyState from '../../ui/EmptyState.vue'

defineProps({
  setups: { type: Array, default: () => [] }
})
const { t } = useI18n()
</script>

<template>
  <section class="setups" aria-labelledby="home-setups-title">
    <header class="setups__head">
      <p class="ui-eyebrow ui-eyebrow--accent">{{ t('home.setups.eyebrow') }}</p>
      <h2 id="home-setups-title" class="ui-title">{{ t('main.setups') }}</h2>
    </header>
    <div v-if="setups.length" class="setups__grid">
      <article v-for="(setup, index) in setups" :key="setup.id" v-reveal="{ delay: index * 60, y: 12 }" v-spotlight class="setups__card ui-glass">
        <span class="setups__icon"><Wrench :size="17" /></span>
        <div>
          <strong>{{ setup.car_model }}</strong>
          <p>{{ setup.description || setup.setup_data }}</p>
        </div>
      </article>
    </div>
    <EmptyState v-else :icon="Wrench" :title="t('home.setups.empty')" compact />
  </section>
</template>

<style scoped>
.setups {
  display: grid;
  gap: 16px;
}

.setups__head {
  display: grid;
  gap: 8px;
}

.setups__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 10px;
}

.setups__card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 16px;
}

.setups__icon {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: var(--c-blue-soft);
  color: var(--c-accent-text);
}

.setups__card strong {
  font-size: 14.5px;
}

.setups__card p {
  margin: 4px 0 0;
  color: var(--c-text-2);
  font-size: 13.5px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
</style>
