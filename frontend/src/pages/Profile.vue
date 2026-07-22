<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import CountryCombobox from '../components/CountryCombobox.vue'
import GameCheckboxGroup from '../components/GameCheckboxGroup.vue'
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
const countries = computed(() => countryOptionsWithCurrent(state.locale, form.value.country))

async function submit() {
  error.value = ''
  saved.value = false
  try {
    const user = await api('/users/me', {
      method: 'PATCH',
      body: {
        ...form.value,
        country: form.value.country || null,
        discord: form.value.discord || null
      }
    })
    setSession(state.token, user)
    saved.value = true
  } catch (err) {
    error.value = err.message
  }
}
</script>

<template>
  <section class="section card">
    <h1>{{ t('nav.profile') }}</h1>
    <p v-if="state.user?.status === 'unapproved'" class="pill">{{ t('profile.waitingApproval') }}</p>
    <p v-if="state.user?.pending_profile_changes" class="pill">{{ t('profile.pendingChanges') }}</p>
    <form v-if="state.user" class="form" @submit.prevent="submit">
      <div class="form-row">
        <label class="field"><span>{{ t('fields.email') }}</span><input v-model="form.email" type="email" /></label>
        <label class="field"><span>{{ t('fields.nickname') }}</span><input v-model="form.nickname" /></label>
      </div>
      <div class="form-row">
        <label class="field"><span>{{ t('fields.firstName') }}</span><input v-model="form.first_name" /></label>
        <label class="field"><span>{{ t('fields.lastName') }}</span><input v-model="form.last_name" /></label>
      </div>
      <div class="form-row">
        <div class="field">
          <span>{{ t('fields.country') }}</span>
          <CountryCombobox v-model="form.country" :options="countries" />
        </div>
        <label class="field"><span>{{ t('fields.discord') }}</span><input v-model="form.discord" /></label>
      </div>
      <label class="field"><span>{{ t('fields.avatarColor') }}</span><input v-model="form.avatar_color" type="color" /></label>
      <div class="field">
        <span>{{ t('fields.games') }}</span>
        <GameCheckboxGroup v-model="form.games" />
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="saved" class="pill">{{ t('common.saved') }}</p>
      <p v-if="saved && state.user?.role !== 'admin'" class="muted">{{ t('profile.changesAfterModeration') }}</p>
      <button class="button primary" type="submit">{{ t('common.save') }}</button>
    </form>
    <RouterLink v-else class="button" to="/login">{{ t('nav.login') }}</RouterLink>
  </section>
</template>
