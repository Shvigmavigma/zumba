<script setup>
import { computed, onMounted, ref } from 'vue'
import { ArrowLeft, AtSign, CheckCircle2, Clock3, ImageUp, LoaderCircle, Mail, MessageCircle, Save, Upload, UserRound } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import AvatarViewer from '../components/AvatarViewer.vue'
import CountryCombobox from '../components/CountryCombobox.vue'
import GameCheckboxGroup from '../components/GameCheckboxGroup.vue'
import PilotLicenseCard from '../components/PilotLicenseCard.vue'
import UserAvatar from '../components/UserAvatar.vue'
import FormField from '../ui/FormField.vue'
import PageHeader from '../ui/PageHeader.vue'
import SwitchToggle from '../ui/SwitchToggle.vue'
import EmptyState from '../ui/EmptyState.vue'
import { countryOptionsWithCurrent } from '../countries'
import { DEFAULT_LICENSE_TIERS, ratingForGame, ratingLicenseTier } from '../pilotDisplay'
import { changedProfileFields, editableProfile } from '../profileChanges'
import { setSession, state } from '../store'

const { t } = useI18n()
const initial = editableProfile(state.user)
const form = ref({
  ...initial,
  country: initial.country || '',
  show_pilot_roles: initial.show_pilot_roles !== false,
  games: initial.games?.length ? [...initial.games] : ['ACC']
})
const error = ref('')
const saved = ref(false)
const savedKind = ref('')
const savedForReview = ref(false)
const saving = ref(false)
const avatarFile = ref(null)
const avatarSaving = ref(false)
const avatarViewerOpen = ref(false)
const countries = computed(() => countryOptionsWithCurrent(state.locale, form.value.country))
const displayName = computed(() => state.user?.nickname || state.user?.login || t('nav.profile'))
const raceAssets = ref({ games: {} })
const favoriteCarOptions = computed(() => {
  const games = raceAssets.value.games || {}
  const sources = Object.values(games).flatMap((game) => (game?.classes || []).flatMap((item) => item.cars || []))
  const current = form.value.favorite_car ? [form.value.favorite_car] : []
  return [...new Set([...current, ...sources])].sort((a, b) => a.localeCompare(b))
})
const previewGame = computed(() => form.value.games?.[0] || 'ACC')
const previewTier = computed(() => ratingLicenseTier(ratingForGame(state.user, previewGame.value), state.licenseTiers || DEFAULT_LICENSE_TIERS))

onMounted(async () => {
  try {
    raceAssets.value = await api('/race-assets')
  } catch {
    raceAssets.value = { games: {} }
  }
})

function setAvatarFile(event) {
  avatarFile.value = event.target.files?.[0] || null
}

async function submit() {
  error.value = ''
  saved.value = false
  savedKind.value = ''
  saving.value = true
  // Favourite car and role badges apply at once; the rest goes to a moderator,
  // so only fields that really changed are sent for review.
  const changes = changedProfileFields(form.value, state.user)
  try {
    const user = await api('/users/me', {
      method: 'PATCH',
      body: {
        ...changes,
        favorite_car: form.value.favorite_car || null,
        show_pilot_roles: form.value.show_pilot_roles !== false
      }
    })
    setSession(state.token, user)
    saved.value = true
    savedKind.value = 'profile'
    savedForReview.value = Object.keys(changes).length > 0 && user.role !== 'admin'
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
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
  <div class="ui-page ui-shell ui-shell--wide edit">
    <PageHeader :eyebrow="t('profileEdit.eyebrow')" :title="t('profile.editTitle')" :lead="t('profileEdit.lead')">
      <template #actions>
        <RouterLink class="ui-btn ui-btn--ghost ui-btn--sm" to="/profile"><ArrowLeft :size="16" />{{ t('profileEdit.back') }}</RouterLink>
      </template>
    </PageHeader>

    <template v-if="state.user">
      <div class="edit__notes">
        <p v-if="state.user.status === 'unapproved'" class="ui-alert ui-alert--info"><Clock3 :size="17" />{{ t('profile.waitingApproval') }}</p>
        <p v-if="state.user.pending_profile_changes" class="ui-alert ui-alert--info"><Clock3 :size="17" />{{ t('profile.pendingChanges') }}</p>
      </div>

      <div class="edit__layout">
        <div class="edit__main">
          <section v-reveal class="ui-card">
            <header class="ui-card__title"><h2>{{ t('profileEdit.sections.avatar') }}</h2></header>
            <div class="avatar">
              <button class="avatar__preview" type="button" :title="t('avatar.open')" @click="avatarViewerOpen = true">
                <UserAvatar class="avatar__img" :src="state.user.avatar_url" :color="form.avatar_color" :label="displayName" />
              </button>
              <div class="avatar__body">
                <p class="avatar__hint">{{ t('avatar.userHint') }}</p>
                <div class="avatar__row">
                  <label class="ui-btn ui-btn--outline ui-btn--sm avatar__pick">
                    <ImageUp :size="16" />{{ t('profileEdit.chooseFile') }}
                    <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" @change="setAvatarFile" />
                  </label>
                  <span class="avatar__file">{{ avatarFile?.name || t('profileEdit.noFile') }}</span>
                  <button class="ui-btn ui-btn--primary ui-btn--sm" type="button" :disabled="avatarSaving || !avatarFile" @click="uploadAvatar">
                    <LoaderCircle v-if="avatarSaving" class="edit__spin" :size="16" />
                    <Upload v-else :size="16" />
                    {{ t('profileEdit.uploadAvatar') }}
                  </button>
                </div>
                <label class="avatar__color">
                  <input v-model="form.avatar_color" type="color" :aria-label="t('avatar.backgroundColor')" />
                  <span>
                    <b>{{ t('avatar.backgroundColor') }}</b>
                    <small>{{ t('profileEdit.colorHint') }}</small>
                  </span>
                  <code class="ui-mono">{{ form.avatar_color }}</code>
                </label>
              </div>
            </div>
          </section>

          <form id="profile-edit-form" class="edit__form" @submit.prevent="submit">
            <section v-reveal class="ui-card">
              <header class="ui-card__title"><h2>{{ t('profileEdit.sections.personal') }}</h2></header>
              <div class="ui-form-row">
                <FormField v-slot="{ id, describedBy }" :label="t('fields.email')" :hint="t('profileEdit.hints.email')" :icon="Mail" required>
                  <input :id="id" v-model="form.email" class="ui-input" type="email" required :aria-describedby="describedBy" />
                </FormField>
                <FormField v-slot="{ id, describedBy }" :label="t('fields.nickname')" :hint="t('profileEdit.hints.nickname')" :icon="AtSign" required :count="form.nickname?.length || 0" :max="80">
                  <input :id="id" v-model="form.nickname" class="ui-input" required maxlength="80" :aria-describedby="describedBy" />
                </FormField>
              </div>
              <div class="ui-form-row">
                <FormField v-slot="{ id, describedBy }" :label="t('fields.firstName')" :hint="t('profileEdit.hints.firstName')" :icon="UserRound" required>
                  <input :id="id" v-model="form.first_name" class="ui-input" required maxlength="50" :aria-describedby="describedBy" />
                </FormField>
                <FormField v-slot="{ id, describedBy }" :label="t('fields.lastName')" :hint="t('profileEdit.hints.lastName')" :icon="UserRound" required>
                  <input :id="id" v-model="form.last_name" class="ui-input" required maxlength="50" :aria-describedby="describedBy" />
                </FormField>
              </div>
              <div class="ui-form-row">
                <FormField v-slot="{ id, describedBy }" :label="t('fields.country')" :hint="t('profileEdit.hints.country')" :optional-label="t('profileEdit.optional')">
                  <CountryCombobox v-model="form.country" :options="countries" :trigger-id="id" :described-by="describedBy" />
                </FormField>
                <FormField v-slot="{ id, describedBy }" :label="t('fields.discord')" :hint="t('profileEdit.hints.discord')" :icon="MessageCircle" :optional-label="t('profileEdit.optional')">
                  <input :id="id" v-model="form.discord" class="ui-input" :aria-describedby="describedBy" />
                </FormField>
              </div>
            </section>

            <section v-reveal class="ui-card">
              <header class="ui-card__title"><h2>{{ t('profileEdit.sections.racing') }}</h2></header>
              <FormField v-slot="{ describedBy }" :label="t('fields.games')" :hint="t('profileEdit.hints.games')" required>
                <GameCheckboxGroup v-model="form.games" :aria-describedby="describedBy" />
              </FormField>
              <FormField v-slot="{ id, describedBy }" :label="t('profile.favoriteCar')" :hint="t('profileEdit.hints.favoriteCar')" :optional-label="t('profileEdit.optional')">
                <select :id="id" v-model="form.favorite_car" class="ui-select" :aria-describedby="describedBy">
                  <option value="">{{ t('common.none') }}</option>
                  <option v-for="car in favoriteCarOptions" :key="car" :value="car">{{ car }}</option>
                </select>
              </FormField>
            </section>

            <section v-reveal class="ui-card">
              <header class="ui-card__title"><h2>{{ t('profileEdit.sections.privacy') }}</h2></header>
              <SwitchToggle v-model="form.show_pilot_roles" :label="t('profile.showRoles')" :hint="t('profile.showRolesHint')" />
            </section>
          </form>
        </div>

        <aside class="edit__side">
          <p class="ui-eyebrow">{{ t('profileEdit.preview') }}</p>
          <PilotLicenseCard :pilot="{ ...state.user, ...form, avatar_url: state.user.avatar_url }" :game="previewGame" :rating="ratingForGame(state.user, previewGame)" :tier="previewTier" />
          <div class="edit__save ui-glass">
            <Transition name="ui-fade" mode="out-in">
              <p v-if="error" key="error" class="ui-alert" role="alert">{{ error }}</p>
              <div v-else-if="saved" key="saved" class="ui-alert ui-alert--success" role="status">
                <CheckCircle2 :size="17" />
                <span>
                  {{ savedKind === 'avatar' ? t('profileEdit.savedAvatar') : t('profileEdit.savedProfile') }}
                  <template v-if="savedKind === 'profile' && savedForReview"> {{ t('profile.changesAfterModeration') }}</template>
                </span>
              </div>
            </Transition>
            <button v-spark class="ui-btn ui-btn--primary ui-btn--lg ui-btn--block" type="submit" form="profile-edit-form" :disabled="saving">
              <LoaderCircle v-if="saving" class="edit__spin" :size="18" />
              <Save v-else :size="18" />
              {{ saving ? t('profileEdit.saving') : t('profileEdit.save') }}
            </button>
          </div>
        </aside>
      </div>
    </template>

    <EmptyState v-else :title="t('nav.login')">
      <RouterLink class="ui-btn ui-btn--primary ui-btn--sm" to="/login">{{ t('nav.login') }}</RouterLink>
    </EmptyState>

    <AvatarViewer
      :open="avatarViewerOpen"
      :src="state.user?.avatar_url"
      :label="displayName"
      :fallback-color="form.avatar_color"
      @close="avatarViewerOpen = false"
    />
  </div>
</template>

<style scoped>
.edit__notes {
  display: grid;
  gap: 8px;
}

.edit__notes:empty {
  display: none;
}

.edit__layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(300px, 380px);
  gap: clamp(16px, 2vw, 24px);
  align-items: start;
}

.edit__main,
.edit__form {
  display: grid;
  gap: clamp(14px, 1.8vw, 20px);
}

.edit__side {
  position: sticky;
  top: calc(var(--header-h) + 20px);
  display: grid;
  gap: 12px;
}

.edit__save {
  display: grid;
  gap: 12px;
  padding: 14px;
  border-radius: var(--r-xl);
}

.edit__spin {
  animation: edit-spin 900ms linear infinite;
}

@keyframes edit-spin {
  to {
    transform: rotate(360deg);
  }
}

.avatar {
  display: flex;
  align-items: flex-start;
  gap: 20px;
}

.avatar__preview {
  flex: 0 0 auto;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: none;
  cursor: zoom-in;
  transition: transform var(--dur-3) var(--ease-ios);
}

.avatar__preview:hover {
  transform: scale(1.04);
}

.avatar__img {
  width: 96px;
  height: 96px;
}

.avatar__body {
  display: grid;
  flex: 1 1 auto;
  gap: 14px;
  min-width: 0;
}

.avatar__hint {
  margin: 0;
  color: var(--c-text-2);
  font-size: 13.5px;
}

.avatar__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.avatar__pick input {
  display: none;
}

.avatar__file {
  flex: 1 1 120px;
  min-width: 0;
  overflow: hidden;
  color: var(--c-text-3);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.avatar__color {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  background: var(--c-sunken);
  cursor: pointer;
}

.avatar__color input {
  flex: none;
  width: 40px;
  height: 40px;
  min-height: 0;
  padding: 0;
  overflow: hidden;
  border: 0;
  border-radius: 12px;
  background: none;
  cursor: pointer;
}

.avatar__color input::-webkit-color-swatch-wrapper {
  padding: 0;
}

.avatar__color input::-webkit-color-swatch {
  border: 0;
  border-radius: 12px;
}

.avatar__color input::-moz-color-swatch {
  border: 0;
  border-radius: 12px;
}

.avatar__color span {
  display: grid;
  flex: 1 1 auto;
  gap: 2px;
}

.avatar__color b {
  font-size: 13.5px;
  font-weight: 600;
}

.avatar__color small {
  color: var(--c-text-3);
  font-size: 12px;
}

.avatar__color code {
  flex: none;
  color: var(--c-text-2);
  font-size: 12px;
  text-transform: uppercase;
  white-space: nowrap;
}

@media (max-width: 980px) {
  .edit__layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .edit__side {
    position: static;
  }
}

@media (max-width: 560px) {
  .avatar {
    flex-direction: column;
  }
}
</style>
