<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ShieldCheck, UserX } from 'lucide-vue-next'
import { api } from '../api'
import EmptyState from '../ui/EmptyState.vue'
import PilotProfileView from './profile/PilotProfileView.vue'
import { DEFAULT_LICENSE_TIERS, normalizeLicenseTiers } from '../pilotDisplay'
import { state } from '../store'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const pilot = ref(null)
const error = ref('')
const loading = ref(true)
const licenseTiers = ref(DEFAULT_LICENSE_TIERS)
const adminOpenError = ref('')
const adminOpening = ref(false)
const canManagePilot = computed(() => state.user?.role === 'admin' && state.user?.status === 'active')

async function openPilotAdmin() {
  if (!pilot.value || !canManagePilot.value || adminOpening.value) return
  adminOpening.value = true
  adminOpenError.value = ''
  try {
    // The admin endpoint checks the session on the server; a zero limit returns no user data.
    await api('/users/admin?limit=0')
    await router.push({ path: '/admin/users', query: { focusUser: String(pilot.value.id), returnPilotId: String(pilot.value.id) } })
  } catch {
    adminOpenError.value = t('profile.adminOpenError')
  } finally {
    adminOpening.value = false
  }
}

onMounted(async () => {
  try {
    const [loadedPilot, loadedLicenses] = await Promise.all([
      api(`/users/${route.params.id}`),
      api('/app-settings/licenses').catch(() => null)
    ])
    pilot.value = loadedPilot
    licenseTiers.value = normalizeLicenseTiers(loadedLicenses)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="ui-page ui-shell ui-shell--wide">
    <PilotProfileView v-if="pilot" :pilot="pilot" :tiers="licenseTiers">
      <template v-if="canManagePilot" #actions>
        <button class="ui-btn ui-btn--outline ui-btn--sm" type="button" :disabled="adminOpening" @click="openPilotAdmin">
          <ShieldCheck :size="15" />{{ adminOpening ? t('profile.adminChecking') : t('profile.adminManagePilot') }}
        </button>
      </template>
      <template v-if="adminOpenError" #alerts>
        <p class="ui-alert" role="alert">{{ adminOpenError }}</p>
      </template>
    </PilotProfileView>
    <EmptyState v-else-if="loading" loading :title="t('ui.common.loading')" />
    <EmptyState v-else :icon="UserX" :title="t('profilePage.notFound')" :text="error">
      <RouterLink class="ui-btn ui-btn--outline ui-btn--sm" to="/pilots">{{ t('profilePage.backToPilots') }}</RouterLink>
    </EmptyState>
  </div>
</template>
