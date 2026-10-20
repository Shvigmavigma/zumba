<script setup>
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { Moon, Sun } from 'lucide-vue-next'
import { api } from './api'
import { brandingSettings, ensureBrandingSettings } from './brandingSettings'
import AccountModerationNotice from './components/AccountModerationNotice.vue'
import { setSession, state } from './store'
import AmbientBackground from './ui/fx/AmbientBackground.vue'
import InkFilters from './ui/fx/InkFilters.vue'
import AppHeader from './shell/AppHeader.vue'
import AppFooter from './shell/AppFooter.vue'
import CommandPalette from './shell/CommandPalette.vue'
import MobileTabBar from './shell/MobileTabBar.vue'
import { syncPreferences, toggleTheme } from './shell/preferences'
import ThemePilot from './shell/ThemePilot.vue'

const { t, locale } = useI18n()
const route = useRoute()

const isStandaloneCompetition = computed(() => route.name === 'competition-bracket' || (route.name === 'competition-view' && Boolean(route.query.match)))
// Mirrors what AccountModerationNotice shows site-wide, so its padded wrapper
// is not left empty for everyone else.
const hasModerationNotice = computed(() => state.user?.status === 'unapproved'
  || (state.user?.status === 'rejected' && state.user?.last_rejection?.request_type === 'registration'))
const themeTitle = computed(() => (state.theme === 'dark' ? t('common.darkTheme') : t('common.lightTheme')))

syncPreferences(locale)

async function refreshSession() {
  if (!state.token) return
  try {
    const user = await api('/auth/me')
    setSession(state.token, user)
  } catch {
    // Keep the cached session on transient startup failures.
  }
}

function prepareDevice() {
  // Set the anonymous marker for every visitor and associate it with the
  // current account when an access token is available.
  api('/auth/device').catch(() => {})
}

onMounted(() => {
  ensureBrandingSettings().catch(() => {})
  refreshSession().finally(prepareDevice)
})
</script>

<template>
  <AmbientBackground />
  <InkFilters />

  <div v-if="isStandaloneCompetition" class="standalone">
    <div class="standalone__bar ui-glass">
      <RouterLink class="standalone__brand" to="/" :aria-label="t('ui.nav.home')">
        <img class="standalone__logo standalone__logo--light" :src="brandingSettings.light_logo_url" alt="BMRL" />
        <img class="standalone__logo standalone__logo--dark" :src="brandingSettings.dark_logo_url" alt="BMRL" />
      </RouterLink>
      <button class="ui-btn ui-btn--ghost ui-btn--icon" type="button" :aria-label="themeTitle" :title="themeTitle" @click="toggleTheme">
        <Sun v-if="state.theme === 'dark'" :size="18" />
        <Moon v-else :size="18" />
      </button>
    </div>
    <main class="standalone__main">
      <RouterView />
    </main>
  </div>

  <div v-else class="app">
    <AppHeader />
    <main class="app__main">
      <div v-if="hasModerationNotice" class="app__notice ui-shell ui-shell--wide">
        <AccountModerationNotice scope="global" />
      </div>
      <RouterView v-slot="{ Component, route: viewRoute }">
        <Transition name="route" mode="out-in">
          <!-- Redesigned pages own their layout; legacy screens keep the classic .page container. -->
          <div :key="viewRoute.path" class="app__view" :class="{ page: !viewRoute.meta.design }">
            <component :is="Component" />
          </div>
        </Transition>
      </RouterView>
    </main>
    <AppFooter />
    <MobileTabBar />
    <CommandPalette />
  </div>
  <ThemePilot />
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-height: 100dvh;
}

.app__main {
  flex: 1 0 auto;
  min-width: 0;
}

.app__notice {
  padding-top: 16px;
}

.standalone {
  min-height: 100dvh;
  padding: 12px var(--gutter) 40px;
}

.standalone__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: min(var(--shell-wide), 100%);
  margin: 0 auto 20px;
  padding: 8px 8px 8px 18px;
  border-radius: 22px;
}

.standalone__brand {
  display: flex;
  align-items: center;
  height: 40px;
}

.standalone__logo {
  height: 28px;
  width: auto;
}

.standalone__logo--dark,
:root[data-theme='dark'] .standalone__logo--light {
  display: none;
}

:root[data-theme='dark'] .standalone__logo--dark {
  display: block;
}

.standalone__main {
  width: min(var(--shell-wide), 100%);
  margin: 0 auto;
}
</style>
