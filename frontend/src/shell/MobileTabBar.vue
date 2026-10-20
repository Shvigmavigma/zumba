<script setup>
// iOS-style tab bar for phones: races, calendar, rating, profile and the full menu.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { motion } from 'motion-v'
import { CalendarDays, Flag, LayoutGrid, Trophy, UserRound } from 'lucide-vue-next'
import NavSheet from './NavSheet.vue'
import { state } from '../store'

const { t } = useI18n()
const route = useRoute()
const sheetOpen = ref(false)
const spring = { type: 'spring', stiffness: 520, damping: 40 }

const tabs = computed(() => [
  { key: 'races', to: '/', label: t('ui.tabs.races'), icon: Flag, match: (path) => path === '/' || path.startsWith('/races') },
  { key: 'calendar', to: '/calendar', label: t('nav.calendar'), icon: CalendarDays, match: (path) => path.startsWith('/calendar') },
  { key: 'rating', to: '/pilots', label: t('ui.tabs.rating'), icon: Trophy, match: (path) => path.startsWith('/pilots') },
  { key: 'profile', to: state.user ? '/profile' : '/login', label: state.user ? t('nav.profile') : t('nav.login'), icon: UserRound, match: (path) => path.startsWith('/profile') || path === '/login' || path === '/register' }
])
const activeKey = computed(() => (sheetOpen.value ? 'more' : tabs.value.find((tab) => tab.match(route.path))?.key || null))
</script>

<template>
  <nav class="tabbar ui-glass ui-glass--strong" :aria-label="t('ui.nav.primary')">
    <RouterLink v-for="tab in tabs" :key="tab.key" class="tabbar__item" :class="{ 'is-active': activeKey === tab.key }" :to="tab.to">
      <motion.span v-if="activeKey === tab.key" class="tabbar__pill" layoutId="tabbar-pill" :transition="spring" />
      <component :is="tab.icon" :size="21" />
      <span>{{ tab.label }}</span>
    </RouterLink>
    <button class="tabbar__item" :class="{ 'is-active': activeKey === 'more' }" type="button" :aria-expanded="sheetOpen" @click="sheetOpen = true">
      <motion.span v-if="activeKey === 'more'" class="tabbar__pill" layoutId="tabbar-pill" :transition="spring" />
      <LayoutGrid :size="21" />
      <span>{{ t('ui.tabs.more') }}</span>
    </button>
  </nav>
  <NavSheet v-model:open="sheetOpen" />
</template>

<style scoped>
.tabbar {
  position: fixed;
  right: 10px;
  bottom: max(10px, env(safe-area-inset-bottom));
  left: 10px;
  z-index: 70;
  display: none;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  padding: 6px;
  border-radius: 24px;
  box-shadow: var(--shadow-2);
}

@media (max-width: 760px) {
  .tabbar {
    display: grid;
  }
}

.tabbar__item {
  position: relative;
  display: grid;
  justify-items: center;
  gap: 3px;
  min-height: 54px;
  padding: 7px 2px 6px;
  border: 0;
  border-radius: 18px;
  background: transparent;
  color: var(--c-text-3);
  cursor: pointer;
  font-family: var(--font-body);
  font-size: 10.5px;
  font-weight: 600;
  text-decoration: none;
  -webkit-tap-highlight-color: transparent;
  transition: color var(--dur-2);
}

.tabbar__item > svg,
.tabbar__item > span:not(.tabbar__pill) {
  position: relative;
  z-index: 1;
}

.tabbar__item > span:not(.tabbar__pill) {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tabbar__item.is-active {
  color: var(--c-accent-text);
}

.tabbar__item:active {
  transform: scale(0.94);
}

.tabbar__pill {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: var(--c-blue-soft);
}
</style>
