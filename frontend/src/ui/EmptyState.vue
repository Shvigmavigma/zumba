<script setup>
// Empty and loading states. Loading shows the start gantry cycling, empty
// states always say what to do next.
import StartLights from './fx/StartLights.vue'

defineProps({
  icon: { type: [Object, Function], default: null },
  title: { type: String, default: '' },
  text: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  compact: { type: Boolean, default: false }
})
</script>

<template>
  <div class="empty" :class="{ 'empty--compact': compact }" :role="loading ? 'status' : null" :aria-busy="loading || null">
    <StartLights v-if="loading" loop size="sm" :interval="150" :label="title" />
    <span v-else-if="icon" class="empty__icon"><component :is="icon" :size="22" /></span>
    <strong v-if="title" class="empty__title" :class="{ 'ui-shiny': loading }">{{ title }}</strong>
    <p v-if="text" class="empty__text">{{ text }}</p>
    <div v-if="$slots.default" class="empty__actions"><slot /></div>
  </div>
</template>

<style scoped>
.empty {
  display: grid;
  justify-items: center;
  gap: 10px;
  padding: clamp(28px, 5vw, 56px) 20px;
  border: 1px dashed var(--c-line-strong);
  border-radius: var(--r-lg);
  color: var(--c-text-2);
  text-align: center;
}

.empty--compact {
  padding: 22px 16px;
}

.empty__icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border: 1px solid var(--c-blue-line);
  border-radius: 50%;
  background: var(--c-blue-soft);
  color: var(--c-accent-text);
}

.empty__title {
  color: var(--c-text);
  font-size: 15px;
  font-weight: 650;
}

.empty__text {
  max-width: 46ch;
  margin: 0;
  font-size: 14px;
}

.empty__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
  margin-top: 6px;
}
</style>
