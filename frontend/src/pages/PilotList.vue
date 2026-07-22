<script setup>
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import UserAvatar from '../components/UserAvatar.vue'
import { gameLabel } from '../i18nLabels'

const { t } = useI18n()
const pilots = ref([])
const search = ref('')
const error = ref('')

async function load() {
  try {
    pilots.value = await api(`/users/pilots?search=${encodeURIComponent(search.value)}`)
  } catch (err) {
    error.value = err.message
  }
}

onMounted(load)
watch(search, load)

function pilotGames(pilot) {
  return pilot.games?.length ? pilot.games.map((game) => gameLabel(t, game)).join(' / ') : t('common.none')
}
</script>

<template>
  <section class="section pilot-list-page">
    <div class="section-header pilot-list-header">
      <h1>{{ t('nav.pilots') }}</h1>
      <input v-model="search" class="pilot-list-search" :placeholder="t('common.search')" />
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <table class="table card">
      <thead>
        <tr><th>#</th><th>{{ t('roles.pilot') }}</th><th>{{ t('fields.country') }}</th><th>SR</th></tr>
      </thead>
      <tbody>
        <tr v-for="pilot in pilots" :key="pilot.id">
          <td>{{ pilot.pilot_number }}</td>
          <td>
            <div class="user-list-cell">
              <UserAvatar mini :color="pilot.avatar_color" :label="pilot.nickname || pilot.login" />
              <RouterLink class="user-list-main" :to="`/pilots/${pilot.id}`">
                <strong>{{ pilot.first_name }} {{ pilot.last_name }}</strong>
                <span>{{ pilot.nickname }} - {{ pilotGames(pilot) }}</span>
              </RouterLink>
            </div>
          </td>
          <td>{{ pilot.country || '-' }}</td>
          <td>{{ pilot.sr }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
