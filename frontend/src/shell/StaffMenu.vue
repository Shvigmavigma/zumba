<script setup>
// Staff tools (races, appeals, moderation, content, admin) grouped in one menu
// so the public navigation stays calm.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ShieldCheck } from 'lucide-vue-next'
import Popover from '../ui/Popover.vue'

defineProps({
  items: { type: Array, required: true }
})
const { t } = useI18n()
const open = ref(false)
</script>

<template>
  <Popover v-model:open="open" :label="t('ui.nav.manage')" width="270px">
    <template #trigger="{ toggle }">
      <button class="ui-btn ui-btn--ghost ui-btn--icon" type="button" :aria-expanded="open" :title="t('ui.nav.manage')" :aria-label="t('ui.nav.manage')" @click="toggle">
        <ShieldCheck :size="18" />
      </button>
    </template>
    <p class="ui-eyebrow staff__heading">{{ t('ui.nav.manage') }}</p>
    <nav class="staff" :aria-label="t('ui.nav.manage')">
      <RouterLink v-for="item in items" :key="item.key" class="staff__item" :to="item.to">
        <component :is="item.icon" :size="17" />
        {{ item.label }}
      </RouterLink>
    </nav>
  </Popover>
</template>

<style scoped>
.staff__heading {
  padding: 8px 10px 6px;
}

.staff {
  display: grid;
  gap: 2px;
}

.staff__item {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 40px;
  padding: 0 12px;
  border-radius: var(--r-sm);
  color: var(--c-text);
  font-size: 14px;
  font-weight: 550;
  text-decoration: none;
  transition: background-color var(--dur-1);
}

.staff__item svg {
  color: var(--c-text-2);
}

.staff__item:hover,
.staff__item.router-link-active {
  background: var(--c-blue-soft);
}

.staff__item.router-link-active svg {
  color: var(--c-accent-text);
}
</style>
