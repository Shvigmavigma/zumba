<script setup>
// Team search (name, abbreviation or description — searched on the server on
// submit) plus the league's roster limit.
import { useI18n } from 'vue-i18n'
import { Search, Users } from 'lucide-vue-next'

defineProps({
  loading: { type: Boolean, default: false },
  limit: { type: Number, default: 0 }
})
const search = defineModel({ type: String, default: '' })
const emit = defineEmits(['submit'])
const { t } = useI18n()
</script>

<template>
  <div class="tsearch">
    <form class="tsearch__form" role="search" @submit.prevent="emit('submit')">
      <label class="tsearch__field">
        <span class="ui-sr">{{ t('teamsPage.search.label') }}</span>
        <Search class="tsearch__icon" :size="18" aria-hidden="true" />
        <input v-model="search" class="ui-input" type="search" :placeholder="t('teams.searchPlaceholder')" />
      </label>
      <button class="ui-btn ui-btn--outline" type="submit" :disabled="loading">
        <Search :size="16" />{{ t('teamsPage.search.submit') }}
      </button>
    </form>
    <span class="ui-chip tsearch__limit"><Users :size="13" />{{ t('teamsPage.limitChip', { limit }) }}</span>
  </div>
</template>

<style scoped>
.tsearch {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.tsearch__form {
  display: flex;
  flex: 1 1 420px;
  gap: 10px;
  max-width: 640px;
}

.tsearch__field {
  position: relative;
  display: grid;
  flex: 1 1 auto;
}

.tsearch__icon {
  position: absolute;
  top: 50%;
  left: 16px;
  color: var(--c-text-3);
  pointer-events: none;
  transform: translateY(-50%);
  transition: color var(--dur-2);
}

.tsearch__field:focus-within .tsearch__icon {
  color: var(--c-accent-text);
}

.tsearch__field .ui-input {
  min-height: 48px;
  padding-left: 46px;
  border-radius: var(--r-pill);
}

.tsearch__form .ui-btn {
  min-height: 48px;
}

@media (max-width: 760px) {
  .tsearch__form {
    flex-basis: 100%;
    max-width: none;
  }
}

@media (max-width: 480px) {
  .tsearch__form .ui-btn {
    width: 48px;
    padding: 0;
    gap: 0;
    font-size: 0;
  }
}
</style>
