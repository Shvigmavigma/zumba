<script setup>
import { computed, ref } from 'vue'
import { Upload } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import AvatarViewer from '../components/AvatarViewer.vue'
import CountryCombobox from '../components/CountryCombobox.vue'
import GameCheckboxGroup from '../components/GameCheckboxGroup.vue'
import UserAvatar from '../components/UserAvatar.vue'
import { countryOptionsWithCurrent } from '../countries'
import { setSession, state } from '../store'

const { t } = useI18n()
const form = ref({
  ...state.user,
  country: state.user?.country || '',
  games: state.user?.games?.length ? [...state.user.games] : ['ACC']
})
const error = ref('')
const saved = ref(false)
const savedKind = ref('')
const avatarFile = ref(null)
const avatarSaving = ref(false)
const avatarViewerOpen = ref(false)
const countries = computed(() => countryOptionsWithCurrent(state.locale, form.value.country))
const displayName = computed(() => state.user?.nickname || state.user?.login || t('nav.profile'))

function setAvatarFile(event) {
  avatarFile.value = event.target.files?.[0] || null
}

async function submit() {
  error.value = ''
  saved.value = false
  savedKind.value = ''
  try {
    const user = await api('/users/me', {
      method: 'PATCH',
      body: {
        email: form.value.email,
        first_name: form.value.first_name,
        last_name: form.value.last_name,
        nickname: form.value.nickname,
        country: form.value.country || null,
        discord: form.value.discord || null,
        games: form.value.games
      }
    })
    setSession(state.token, user)
    saved.value = true
    savedKind.value = 'profile'
  } catch (err) {
    error.value = err.message
  }
}

async function uploadAvatar() {
  if (!avatarFile.value) return
  error.value = ''
  saved.value = false
  savedKind.value = ''
  avatarSaving.value = true
  try {
    const payload = new FormData()
    payload.append('file', avatarFile.value)
    const user = await api('/users/me/avatar', {
      method: 'POST',
      body: payload
    })
    setSession(state.token, user)
    avatarFile.value = null
    saved.value = true
    savedKind.value = 'avatar'
  } catch (err) {
    error.value = err.message
  } finally {
    avatarSaving.value = false
  }
}
</script>

<template>
  <section class="section card">
    <h1>{{ t('profile.editTitle') }}</h1>
    <p v-if="state.user?.status === 'unapproved'" class="pill">{{ t('profile.waitingApproval') }}</p>
    <p v-if="state.user?.pending_profile_changes" class="pill">{{ t('profile.pendingChanges') }}</p>
    <div v-if="state.user" class="avatar-edit-panel">
      <button class="avatar-open-button" type="button" :title="t('avatar.open')" @click="avatarViewerOpen = true">
        <UserAvatar :src="state.user.avatar_url" :color="state.user.avatar_color" :label="displayName" />
      </button>
      <div class="avatar-edit-main">
        <strong>{{ t('avatar.userTitle') }}</strong>
        <p class="muted">{{ t('avatar.userHint') }}</p>
        <div class="avatar-upload-row">
          <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" @change="setAvatarFile" />
          <button class="button" type="button" :disabled="avatarSaving || !avatarFile" @click="uploadAvatar">
            <Upload :size="16" />
            {{ t('common.upload') }}
          </button>
        </div>
      </div>
    </div>
    <form v-if="state.user" class="form" @submit.prevent="submit">
      <div class="form-row">
        <label class="field"><span>{{ t('fields.email') }}</span><input v-model="form.email" type="email" required /></label>
        <label class="field"><span>{{ t('fields.nickname') }}</span><input v-model="form.nickname" required maxlength="80" /></label>
      </div>
      <div class="form-row">
        <label class="field"><span>{{ t('fields.firstName') }}</span><input v-model="form.first_name" required maxlength="50" /></label>
        <label class="field"><span>{{ t('fields.lastName') }}</span><input v-model="form.last_name" required maxlength="50" /></label>
      </div>
      <div class="form-row">
        <div class="field">
          <span>{{ t('fields.country') }}</span>
          <CountryCombobox v-model="form.country" :options="countries" />
        </div>
        <label class="field"><span>{{ t('fields.discord') }}</span><input v-model="form.discord" /></label>
      </div>
      <div class="field is-required">
        <span>{{ t('fields.games') }}</span>
        <GameCheckboxGroup v-model="form.games" />
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="saved" class="pill">{{ t('common.saved') }}</p>
      <p v-if="saved && savedKind === 'profile' && state.user?.role !== 'admin'" class="muted">{{ t('profile.changesAfterModeration') }}</p>
      <button class="button primary" type="submit">{{ t('common.save') }}</button>
    </form>
    <RouterLink v-else class="button" to="/login">{{ t('nav.login') }}</RouterLink>
    <AvatarViewer
      :open="avatarViewerOpen"
      :src="state.user?.avatar_url"
      :label="displayName"
      :fallback-color="state.user?.avatar_color"
      @close="avatarViewerOpen = false"
    />
  </section>
</template>
