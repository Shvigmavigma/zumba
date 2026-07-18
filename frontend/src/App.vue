<script setup>
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { CalendarDays, Flag, Home, Languages, LogIn, LogOut, Moon, Shield, Sun, User, Users } from 'lucide-vue-next'
import { clearSession, state } from './store'

const { t, locale } = useI18n()

const isStaff = computed(() => ['admin', 'moder', 'marshall'].includes(state.user?.role))
const canEditBanners = computed(() => ['admin', 'moder', 'smm'].includes(state.user?.role))

watch(
  () => state.theme,
  (value) => {
    document.documentElement.dataset.theme = value
    localStorage.setItem('theme', value)
  },
  { immediate: true }
)

function toggleTheme() {
  state.theme = state.theme === 'light' ? 'dark' : 'light'
}

function setLocale(value) {
  state.locale = value
  locale.value = value
  localStorage.setItem('locale', value)
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink class="brand" to="/">
        <Flag :size="22" />
        <span>BRML</span>
      </RouterLink>

      <nav class="nav-links" aria-label="Main navigation">
        <RouterLink to="/"><Home :size="18" />{{ t('nav.main') }}</RouterLink>
        <RouterLink to="/pilots"><Users :size="18" />{{ t('nav.pilots') }}</RouterLink>
        <RouterLink to="/calendar"><CalendarDays :size="18" />{{ t('nav.calendar') }}</RouterLink>
        <RouterLink v-if="isStaff" to="/appeals"><Shield :size="18" />{{ t('nav.appeals') }}</RouterLink>
        <RouterLink v-if="isStaff" to="/moderation/users"><User :size="18" />{{ t('nav.moderation') }}</RouterLink>
        <RouterLink v-if="canEditBanners" to="/banners">{{ t('nav.banners') }}</RouterLink>
        <RouterLink v-if="state.user?.role === 'admin'" to="/admin/users">{{ t('nav.admin') }}</RouterLink>
      </nav>

      <div class="toolbar">
        <button class="icon-button" type="button" :title="state.theme" @click="toggleTheme">
          <Sun v-if="state.theme === 'dark'" :size="18" />
          <Moon v-else :size="18" />
        </button>
        <button class="icon-button" type="button" title="Language" @click="setLocale(state.locale === 'ru' ? 'en' : 'ru')">
          <Languages :size="18" />
          <span>{{ state.locale.toUpperCase() }}</span>
        </button>
        <RouterLink v-if="!state.user" class="button small" to="/login"><LogIn :size="16" />{{ t('nav.login') }}</RouterLink>
        <RouterLink v-else class="button small" to="/profile">
          <User :size="16" />
          {{ state.user.nickname }}
          <span v-if="state.user.status !== 'active'" class="account-status">{{ state.user.status }}</span>
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
