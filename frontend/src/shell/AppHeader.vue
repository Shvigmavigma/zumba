<script setup>
// Floating glass navigation bar. The active section is marked by a pill that
// glides between links (Motion shared layout); a softer pill follows hover.
// Links that don't fit collapse into "More"; the bar tucks away while
// scrolling down and returns on the way up.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { motion } from 'motion-v'
import { LogIn, MoreHorizontal, Search, UserPlus } from 'lucide-vue-next'
import Popover from '../ui/Popover.vue'
import SettingsMenu from './SettingsMenu.vue'
import StaffMenu from './StaffMenu.vue'
import UserMenu from './UserMenu.vue'
import { brandingSettings } from '../brandingSettings'
import { state } from '../store'
import { openPalette } from './commandPalette'
import { useNavigation } from './useNavigation'

const { t } = useI18n()
const route = useRoute()
const { publicItems, staffItems } = useNavigation()

const navContainer = ref(null)
const navMeasure = ref(null)
const visibleKeys = ref([])
const measured = ref(false)
const moreOpen = ref(false)
const hovered = ref(null)
const hidden = ref(false)
const scrolled = ref(false)
const pillSpring = { type: 'spring', stiffness: 480, damping: 40 }
const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform || '')
let resizeObserver = null
let reflowFrame = 0
let lastScroll = 0

const visibleItems = computed(() => {
  if (!measured.value) return publicItems.value
  const keys = new Set(visibleKeys.value)
  return publicItems.value.filter((item) => keys.has(item.key))
})
const overflowItems = computed(() => {
  if (!measured.value) return []
  const keys = new Set(visibleKeys.value)
  return publicItems.value.filter((item) => !keys.has(item.key))
})
const activeKey = computed(() => {
  const path = route.path
  const match = publicItems.value
    .filter((item) => (item.to === '/' ? path === '/' : path === item.to || path.startsWith(`${item.to}/`)))
    .sort((a, b) => b.to.length - a.to.length)[0]
  return match?.key || null
})
const overflowActive = computed(() => overflowItems.value.some((item) => item.key === activeKey.value))

function recalculate() {
  const container = navContainer.value
  const measure = navMeasure.value
  const items = publicItems.value
  if (!container || !measure) return
  const links = Array.from(measure.querySelectorAll('[data-measure-item]'))
  const moreWidth = measure.querySelector('[data-measure-more]')?.getBoundingClientRect().width || 72
  const gap = 2
  const available = container.clientWidth
  const next = []
  let used = 0
  let overflowed = false
  links.forEach((link, index) => {
    const width = link.getBoundingClientRect().width
    const remaining = index < links.length - 1
    const reserve = remaining || overflowed ? moreWidth + gap : 0
    if (!overflowed && used + width + gap + reserve <= available) {
      used += width + gap
      next.push(items[index].key)
    } else {
      overflowed = true
    }
  })
  visibleKeys.value = next
  measured.value = true
}

function queueReflow() {
  cancelAnimationFrame(reflowFrame)
  reflowFrame = requestAnimationFrame(() => nextTick(recalculate))
}

function onScroll() {
  const y = window.scrollY
  scrolled.value = y > 8
  const delta = y - lastScroll
  if (Math.abs(delta) > 6) {
    hidden.value = delta > 0 && y > 240 && !moreOpen.value
    lastScroll = y
  }
}

onMounted(() => {
  resizeObserver = new ResizeObserver(queueReflow)
  if (navContainer.value) resizeObserver.observe(navContainer.value)
  document.fonts?.ready.then(queueReflow)
  window.addEventListener('scroll', onScroll, { passive: true })
  queueReflow()
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  cancelAnimationFrame(reflowFrame)
  window.removeEventListener('scroll', onScroll)
})

watch(publicItems, () => {
  measured.value = false
  queueReflow()
}, { flush: 'post' })
watch(() => route.fullPath, () => { hidden.value = false })
</script>

<template>
  <header class="hdr" :class="{ 'is-hidden': hidden, 'is-scrolled': scrolled }">
    <div class="hdr__bar ui-glass">
      <RouterLink class="hdr__brand" to="/" :aria-label="t('ui.nav.home')">
        <img class="hdr__logo hdr__logo--light" :src="brandingSettings.light_logo_url" alt="" />
        <img class="hdr__logo hdr__logo--dark" :src="brandingSettings.dark_logo_url" alt="" />
      </RouterLink>

      <nav ref="navContainer" class="hdr__nav" :aria-label="t('ui.nav.primary')" @mouseleave="hovered = null">
        <RouterLink
          v-for="item in visibleItems"
          :key="item.key"
          class="hdr__link"
          :class="{ 'is-active': activeKey === item.key }"
          :to="item.to"
          @mouseenter="hovered = item.key"
          @focus="hovered = item.key"
        >
          <motion.span v-if="activeKey === item.key" class="hdr__pill" layoutId="hdr-active" :transition="pillSpring" />
          <motion.span v-else-if="hovered === item.key" class="hdr__hover" layoutId="hdr-hover" :transition="pillSpring" :initial="{ opacity: 0 }" :animate="{ opacity: 1 }" :exit="{ opacity: 0 }" />
          <span class="hdr__label">{{ item.label }}</span>
        </RouterLink>

        <Popover v-if="overflowItems.length" v-model:open="moreOpen" align="start" width="240px" :label="t('common.more')">
          <template #trigger="{ toggle }">
            <button class="hdr__link hdr__more" :class="{ 'is-active': overflowActive }" type="button" :aria-expanded="moreOpen" @click="toggle">
              <span class="hdr__label"><MoreHorizontal :size="16" />{{ t('common.more') }}</span>
            </button>
          </template>
          <div class="hdr__menu">
            <RouterLink v-for="item in overflowItems" :key="item.key" class="hdr__menu-item" :to="item.to">
              <component :is="item.icon" :size="17" />{{ item.label }}
            </RouterLink>
          </div>
        </Popover>

        <div ref="navMeasure" class="hdr__measure" aria-hidden="true">
          <span v-for="item in publicItems" :key="item.key" class="hdr__link" data-measure-item><span class="hdr__label">{{ item.label }}</span></span>
          <span class="hdr__link" data-measure-more><span class="hdr__label"><MoreHorizontal :size="16" />{{ t('common.more') }}</span></span>
        </div>
      </nav>

      <div class="hdr__tools">
        <button class="hdr__search" type="button" :aria-label="t('ui.palette.open')" @click="openPalette">
          <Search :size="17" />
          <span class="hdr__search-text">{{ t('ui.palette.short') }}</span>
          <kbd>{{ isMac ? '⌘' : 'Ctrl' }} K</kbd>
        </button>
        <StaffMenu v-if="staffItems.length" class="hdr__staff" :items="staffItems" />
        <SettingsMenu class="hdr__settings" />
        <UserMenu v-if="state.user" />
        <template v-else>
          <RouterLink class="ui-btn ui-btn--ghost ui-btn--sm hdr__login" to="/login"><LogIn :size="16" />{{ t('nav.login') }}</RouterLink>
          <RouterLink v-magnet="4" class="ui-btn ui-btn--primary ui-btn--sm hdr__join" to="/register"><UserPlus :size="16" />{{ t('ui.nav.join') }}</RouterLink>
        </template>
      </div>
    </div>
  </header>
</template>

<style scoped>
.hdr {
  position: sticky;
  top: 0;
  z-index: 60;
  padding: 12px var(--gutter) 0;
  transition: transform 520ms var(--ease-ios);
}

.hdr.is-hidden {
  transform: translateY(calc(-100% - 8px));
}

.hdr__bar {
  display: flex;
  align-items: center;
  gap: 16px;
  width: min(var(--shell-wide), 100%);
  min-height: 60px;
  margin-inline: auto;
  padding: 8px 8px 8px 18px;
  border-radius: 22px;
  transition: background-color var(--dur-3), box-shadow var(--dur-3), border-color var(--dur-3);
}

.hdr.is-scrolled .hdr__bar {
  border-color: var(--c-line-strong);
  background: color-mix(in srgb, var(--c-surface-2) 92%, transparent);
  box-shadow: var(--shadow-2);
}

.hdr__brand {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  height: 40px;
}

.hdr__logo {
  width: auto;
  height: 30px;
  object-fit: contain;
}

.hdr__logo--dark,
:root[data-theme='dark'] .hdr__logo--light {
  display: none;
}

:root[data-theme='dark'] .hdr__logo--dark {
  display: block;
}

.hdr__nav {
  position: relative;
  display: flex;
  flex: 1 1 auto;
  align-items: center;
  justify-content: center;
  gap: 2px;
  min-width: 0;
}

.hdr__link {
  position: relative;
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  min-height: 40px;
  padding: 0 14px;
  border: 0;
  border-radius: var(--r-pill);
  background: transparent;
  color: var(--c-text-2);
  cursor: pointer;
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
  transition: color var(--dur-2) var(--ease-out);
}

.hdr__link:hover,
.hdr__link.is-active {
  color: var(--c-text);
}

.hdr__pill,
.hdr__hover {
  position: absolute;
  inset: 0;
  border-radius: inherit;
}

.hdr__pill {
  border: 1px solid var(--c-blue-line);
  background: var(--c-blue-soft);
  box-shadow: inset 0 1px 0 var(--c-highlight);
}

/* A short telemetry underline under the active section. */
.hdr__pill::after {
  position: absolute;
  bottom: 5px;
  left: 50%;
  width: 16px;
  height: 2px;
  border-radius: 2px;
  background: var(--bm-blue-bright);
  box-shadow: 0 0 10px var(--bm-blue-bright);
  content: '';
  transform: translateX(-50%);
}

.hdr__hover {
  background: color-mix(in srgb, var(--c-text) 6%, transparent);
}

.hdr__label {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.hdr__more.is-active {
  color: var(--c-accent-text);
}

.hdr__measure {
  position: absolute;
  top: 0;
  left: 0;
  display: flex;
  gap: 2px;
  visibility: hidden;
  pointer-events: none;
}

.hdr__menu {
  display: grid;
  gap: 2px;
}

.hdr__menu-item {
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
}

.hdr__menu-item svg {
  color: var(--c-text-2);
}

.hdr__menu-item:hover,
.hdr__menu-item.router-link-active {
  background: var(--c-blue-soft);
}

.hdr__tools {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 6px;
}

.hdr__search {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-height: 40px;
  padding: 0 8px 0 14px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-pill);
  background: var(--c-sunken);
  color: var(--c-text-3);
  cursor: pointer;
  font-family: var(--font-body);
  font-size: 13px;
  transition: border-color var(--dur-2), color var(--dur-2);
}

.hdr__search:hover {
  border-color: var(--c-blue-line);
  color: var(--c-text);
}

.hdr__search kbd {
  padding: 3px 7px;
  border: 1px solid var(--c-line-strong);
  border-radius: 7px;
  background: color-mix(in srgb, var(--c-text) 5%, transparent);
  color: var(--c-text-2);
  font-family: var(--font-mono);
  font-size: 11px;
}

@media (max-width: 1360px) {
  .hdr__search-text,
  .hdr__search kbd {
    display: none;
  }

  .hdr__search {
    width: 44px;
    justify-content: center;
    padding: 0;
  }
}

@media (max-width: 760px) {
  .hdr {
    padding-top: max(8px, env(safe-area-inset-top));
  }

  .hdr__bar {
    gap: 8px;
    min-height: 52px;
    padding: 6px 6px 6px 14px;
    border-radius: 18px;
  }

  .hdr__nav,
  .hdr__staff,
  .hdr__settings,
  .hdr__login {
    display: none;
  }

  .hdr__tools {
    margin-left: auto;
  }

  .hdr__logo {
    height: 24px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .hdr {
    transition: none;
  }
}
</style>
