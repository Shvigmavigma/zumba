<script setup>
// Account menu (Kokonut UI "profile dropdown" pattern): who is signed in,
// account status, profile shortcuts and sign-out.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { ChevronDown, Clock3, LogOut, PencilLine, UserRound } from 'lucide-vue-next'
import Popover from '../ui/Popover.vue'
import UserAvatar from '../components/UserAvatar.vue'
import { roleLabel, statusLabel } from '../i18nLabels'
import { formatPilotNumber, pilotName } from '../pilotDisplay'
import { clearSession, state } from '../store'

const { t } = useI18n()
const router = useRouter()
const open = ref(false)
const user = computed(() => state.user)
const name = computed(() => pilotName(user.value, user.value?.login))
const isActive = computed(() => user.value?.status === 'active')
const statusTone = computed(() => ({ active: 'green', unapproved: 'amber', timeout: 'amber', banned: 'red' }[user.value?.status] || ''))

function logout() {
  open.value = false
  clearSession()
  router.push('/')
}
</script>

<template>
  <Popover v-model:open="open" :label="t('nav.profile')" width="300px">
    <template #trigger="{ toggle }">
      <button class="account" type="button" :aria-expanded="open" @click="toggle">
        <UserAvatar mini class="account__avatar" :src="user.avatar_url" :color="user.avatar_color" :label="user.nickname || user.login" />
        <span class="account__name">{{ user.nickname || user.login }}</span>
        <span v-if="user.status !== 'active'" class="ui-dot ui-dot--amber" :title="statusLabel(t, user.status)"></span>
        <ChevronDown class="account__chevron" :size="15" :class="{ 'is-open': open }" />
      </button>
    </template>
    <div class="menu">
      <div class="menu__head">
        <UserAvatar class="menu__avatar" :src="user.avatar_url" :color="user.avatar_color" :label="name" />
        <div class="menu__who">
          <strong>{{ name }}</strong>
          <span class="ui-mono">@{{ user.login }} · #{{ formatPilotNumber(user.pilot_number) }}</span>
          <span class="menu__chips">
            <span class="ui-chip" :class="statusTone ? `ui-chip--${statusTone}` : ''">{{ statusLabel(t, user.status) }}</span>
            <span v-if="user.role !== 'pilot'" class="ui-chip ui-chip--blue">{{ roleLabel(t, user.role) }}</span>
          </span>
        </div>
      </div>
      <template v-if="isActive">
        <RouterLink class="menu__item" to="/profile"><UserRound :size="17" />{{ t('ui.account.myProfile') }}</RouterLink>
        <RouterLink class="menu__item" to="/profile/edit"><PencilLine :size="17" />{{ t('ui.account.editProfile') }}</RouterLink>
      </template>
      <!-- Profile routes need an active account; say why instead of a link that bounces home. -->
      <p v-else class="menu__note"><Clock3 :size="16" />{{ t(user.status === 'unapproved' ? 'ui.account.pendingHint' : 'ui.account.restrictedHint') }}</p>
      <hr class="ui-hairline" />
      <button class="menu__item menu__item--danger" type="button" @click="logout"><LogOut :size="17" />{{ t('nav.logout') }}</button>
    </div>
  </Popover>
</template>

<style scoped>
.account {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-height: 44px;
  padding: 4px 12px 4px 4px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-pill);
  background: var(--c-sunken);
  color: var(--c-text);
  cursor: pointer;
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 600;
  transition: border-color var(--dur-2), background-color var(--dur-2), transform var(--dur-2) var(--ease-ios);
}

.account:hover {
  border-color: var(--c-blue-line);
}

.account:active {
  transform: scale(0.97);
}

.account__avatar {
  width: 34px;
  height: 34px;
  border-width: 1px;
  box-shadow: none;
}

.account__name {
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account__chevron {
  color: var(--c-text-3);
  transition: transform var(--dur-3) var(--ease-ios);
}

.account__chevron.is-open {
  transform: rotate(180deg);
}

.menu {
  display: grid;
  gap: 2px;
}

.menu__head {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 6px;
  padding: 10px 10px 14px;
  border-bottom: 1px solid var(--c-line);
}

.menu__avatar {
  width: 52px;
  height: 52px;
  flex: 0 0 auto;
}

.menu__who {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.menu__who strong {
  overflow: hidden;
  font-size: 15px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.menu__who > span {
  color: var(--c-text-3);
  font-size: 12px;
}

.menu__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 2px;
}

.menu__item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  min-height: 42px;
  padding: 0 12px;
  border: 0;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--c-text);
  cursor: pointer;
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 550;
  text-align: left;
  text-decoration: none;
  transition: background-color var(--dur-1);
}

.menu__item svg {
  color: var(--c-text-2);
}

.menu__item:hover {
  background: var(--c-blue-soft);
}

.menu__note {
  display: flex;
  gap: 10px;
  margin: 2px 0;
  padding: 10px 12px;
  border-radius: var(--r-sm);
  background: color-mix(in srgb, var(--bm-amber) 10%, transparent);
  color: var(--c-text-2);
  font-size: 13px;
  line-height: 1.45;
}

.menu__note svg {
  flex: none;
  margin-top: 1px;
  color: var(--bm-amber);
}

.menu__item--danger,
.menu__item--danger svg {
  color: color-mix(in srgb, var(--bm-red) 80%, var(--c-text));
}

.menu__item--danger:hover {
  background: color-mix(in srgb, var(--bm-red) 12%, transparent);
}

.ui-hairline {
  margin: 4px 6px;
}
</style>
