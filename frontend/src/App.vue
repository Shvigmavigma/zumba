<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { CalendarDays, Calculator, Flag, Home, Languages, ListChecks, LogIn, LogOut, Medal, Moon, MoreHorizontal, Newspaper, Shield, Sun, Trophy, User, Users } from 'lucide-vue-next'
import { statusLabel } from './i18nLabels'
import { clearSession, state } from './store'

const { t, locale } = useI18n()

const isStaff = computed(() => ['admin', 'moder', 'marshall'].includes(state.user?.role))
const canManageRaces = computed(() => ['admin', 'moder'].includes(state.user?.role))
const canEditBanners = computed(() => ['admin', 'moder', 'smm'].includes(state.user?.role))
const canManageNews = computed(() => ['admin', 'moder', 'smm'].includes(state.user?.role))
const themeTitle = computed(() => state.theme === 'dark' ? t('common.darkTheme') : t('common.lightTheme'))
const navContainer = ref(null)
const navMeasure = ref(null)
const navMore = ref(null)
const visibleNavKeys = ref([])
const navMeasured = ref(false)
const isMoreOpen = ref(false)
let navResizeObserver = null
let navReflowFrame = 0

const navItems = computed(() => [
  { key: 'main', to: '/', label: t('nav.main'), icon: Home, visible: true },
  { key: 'pilots', to: '/pilots', label: t('nav.pilots'), icon: Users, visible: true },
  { key: 'teams', to: '/teams', label: t('nav.teams'), icon: Trophy, visible: true },
  { key: 'championships', to: '/championships', label: t('nav.championships'), icon: Flag, visible: true },
  { key: 'hallOfFame', to: '/hall-of-fame', label: t('nav.hallOfFame'), icon: Medal, visible: true },
  { key: 'calendar', to: '/calendar', label: t('nav.calendar'), icon: CalendarDays, visible: true },
  { key: 'fuel', to: '/fuel-calculator', label: t('nav.fuel'), icon: Calculator, visible: true },
  { key: 'races', to: '/races/manage', label: t('nav.races'), icon: ListChecks, visible: canManageRaces.value },
  { key: 'appeals', to: '/appeals', label: t('nav.appeals'), icon: Shield, visible: isStaff.value },
  { key: 'moderation', to: '/moderation/users', label: t('nav.moderation'), icon: User, visible: isStaff.value },
  { key: 'banners', to: '/banners', label: t('nav.banners'), icon: null, visible: canEditBanners.value },
  { key: 'news', to: '/news/manage', label: t('nav.news'), icon: Newspaper, visible: canManageNews.value },
  { key: 'admin', to: '/admin/users', label: t('nav.admin'), icon: null, visible: state.user?.role === 'admin' }
].filter((item) => item.visible))

const visibleNavItems = computed(() => {
  if (!navMeasured.value) return navItems.value
  const visibleKeys = new Set(visibleNavKeys.value)
  return navItems.value.filter((item) => visibleKeys.has(item.key))
})

const hiddenNavItems = computed(() => {
  if (!navMeasured.value) return []
  const visibleKeys = new Set(visibleNavKeys.value)
  return navItems.value.filter((item) => !visibleKeys.has(item.key))
})

watch(
  () => state.theme,
  (value) => {
    document.documentElement.dataset.theme = value
    localStorage.setItem('theme', value)
  },
  { immediate: true }
)

watch(
  () => state.locale,
  (value) => {
    const nextLocale = value === 'en' ? 'en' : 'ru'
    if (nextLocale !== value) {
      state.locale = nextLocale
      return
    }
    locale.value = nextLocale
    localStorage.setItem('locale', nextLocale)
  },
  { immediate: true }
)

function toggleTheme() {
  state.theme = state.theme === 'light' ? 'dark' : 'light'
}

function setLocale(value) {
  state.locale = value === 'en' ? 'en' : 'ru'
}

function sameKeys(left, right) {
  return left.length === right.length && left.every((key, index) => key === right[index])
}

function recalculateNav() {
  const container = navContainer.value
  const measure = navMeasure.value
  const items = navItems.value
  if (!container || !measure || !items.length) {
    visibleNavKeys.value = items.map((item) => item.key)
    navMeasured.value = true
    return
  }

  const links = Array.from(measure.querySelectorAll('[data-nav-measure-item]'))
  const moreButton = measure.querySelector('[data-nav-measure-more]')
  const availableWidth = container.clientWidth
  const styles = window.getComputedStyle(container)
  const gap = Number.parseFloat(styles.columnGap || styles.gap || '0') || 0
  const moreWidth = moreButton?.getBoundingClientRect().width || 64
  const nextVisibleKeys = []
  let usedWidth = 0
  let hasHiddenItems = false

  links.forEach((link, index) => {
    const width = link.getBoundingClientRect().width
    const linkGap = nextVisibleKeys.length ? gap : 0
    const hasRemainingItems = index < links.length - 1
    const reserveWidth = hasRemainingItems || hasHiddenItems ? moreWidth + (nextVisibleKeys.length ? gap : 0) : 0
    if (usedWidth + linkGap + width + reserveWidth <= availableWidth) {
      usedWidth += linkGap + width
      nextVisibleKeys.push(items[index].key)
    } else {
      hasHiddenItems = true
    }
  })

  if (nextVisibleKeys.length === items.length) {
    isMoreOpen.value = false
  }
  if (!sameKeys(visibleNavKeys.value, nextVisibleKeys)) {
    visibleNavKeys.value = nextVisibleKeys
  }
  navMeasured.value = true
}

function queueNavReflow() {
  if (typeof window === 'undefined') return
  window.cancelAnimationFrame(navReflowFrame)
  navReflowFrame = window.requestAnimationFrame(() => {
    nextTick(recalculateNav)
  })
}

function closeMoreMenu() {
  isMoreOpen.value = false
}

function handleDocumentPointerDown(event) {
  if (!navMore.value?.contains(event.target)) {
    closeMoreMenu()
  }
}

onMounted(() => {
  navResizeObserver = new ResizeObserver(queueNavReflow)
  if (navContainer.value) navResizeObserver.observe(navContainer.value)
  document.addEventListener('pointerdown', handleDocumentPointerDown)
  queueNavReflow()
})

onBeforeUnmount(() => {
  navResizeObserver?.disconnect()
  document.removeEventListener('pointerdown', handleDocumentPointerDown)
  if (typeof window !== 'undefined') {
    window.cancelAnimationFrame(navReflowFrame)
  }
})

watch(navItems, () => {
  navMeasured.value = false
  isMoreOpen.value = false
  queueNavReflow()
}, { flush: 'post' })
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink class="brand" to="/">
        <img class="brand-logo" src="/assets/bmrl-logo-nav.png" alt="" />
        <span class="brand-text">BMRL</span>
      </RouterLink>

      <nav ref="navContainer" class="nav-links" :aria-label="t('nav.main')">
        <template v-for="item in visibleNavItems" :key="item.key">
          <RouterLink v-if="item.to" :to="item.to" @click="closeMoreMenu">
            <component :is="item.icon" v-if="item.icon" :size="18" />
            {{ item.label }}
          </RouterLink>
          <a v-else :href="item.href" @click="closeMoreMenu">
            <component :is="item.icon" v-if="item.icon" :size="18" />
            {{ item.label }}
          </a>
        </template>
        <div v-if="hiddenNavItems.length" ref="navMore" class="nav-more">
          <button class="icon-button nav-more-button" type="button" :aria-expanded="isMoreOpen" :title="t('common.more')" @click="isMoreOpen = !isMoreOpen" @keydown.escape="closeMoreMenu">
            <MoreHorizontal :size="18" />
            <span>{{ t('common.more') }}</span>
          </button>
          <div v-if="isMoreOpen" class="nav-more-menu" role="menu" @keydown.escape="closeMoreMenu">
            <template v-for="item in hiddenNavItems" :key="item.key">
              <RouterLink v-if="item.to" :to="item.to" role="menuitem" @click="closeMoreMenu">
                <component :is="item.icon" v-if="item.icon" :size="18" />
                {{ item.label }}
              </RouterLink>
              <a v-else :href="item.href" role="menuitem" @click="closeMoreMenu">
                <component :is="item.icon" v-if="item.icon" :size="18" />
                {{ item.label }}
              </a>
            </template>
          </div>
        </div>
        <div ref="navMeasure" class="nav-measure" aria-hidden="true">
          <span v-for="item in navItems" :key="item.key" data-nav-measure-item class="nav-measure-link">
            <component :is="item.icon" v-if="item.icon" :size="18" />
            {{ item.label }}
          </span>
          <span data-nav-measure-more class="nav-more-button nav-measure-link">
            <MoreHorizontal :size="18" />
            <span>{{ t('common.more') }}</span>
          </span>
        </div>
      </nav>

      <div class="toolbar">
        <button class="icon-button" type="button" :title="themeTitle" @click="toggleTheme">
          <Sun v-if="state.theme === 'dark'" :size="18" />
          <Moon v-else :size="18" />
        </button>
        <button class="icon-button" type="button" :title="t('common.language')" @click="setLocale(state.locale === 'ru' ? 'en' : 'ru')">
          <Languages :size="18" />
          <span>{{ state.locale.toUpperCase() }}</span>
        </button>
        <RouterLink v-if="!state.user" class="button small" to="/login"><LogIn :size="16" />{{ t('nav.login') }}</RouterLink>
        <RouterLink v-else class="button small" to="/profile">
          <User :size="16" />
          {{ state.user.nickname }}
          <span v-if="state.user.status !== 'active'" class="account-status">{{ statusLabel(t, state.user.status) }}</span>
        </RouterLink>
        <button v-if="state.user" class="icon-button" type="button" :title="t('nav.logout')" @click="clearSession">
          <LogOut :size="18" />
        </button>
      </div>
    </header>

    <main class="page">
      <RouterView />
    </main>
  </div>
</template>
