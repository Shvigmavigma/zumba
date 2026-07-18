<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'

const users = ref([])
const roles = ['admin', 'moder', 'marshall', 'smm', 'pilot']
const error = ref('')

async function load() {
  try {
    users.value = await api('/users/admin')
  } catch (err) {
    error.value = err.message
  }
}

async function chooseRole(user, role) {
  if (user.role === role) return
  user.role = role
  await api(`/users/${user.id}/role`, { method: 'PATCH', body: { role } })
}

async function ban(user) {
  if (user.role === 'admin') return
  await api(`/users/${user.id}/ban`, { method: 'POST' })
  await load()
}

async function unban(user) {
  await api(`/users/${user.id}/unban`, { method: 'POST' })
  await load()
}

onMounted(load)
</script>

<template>
  <section class="section">
    <h1>AdminUserList</h1>
    <p v-if="error" class="error">{{ error }}</p>
    <table class="table card">
      <thead>
        <tr><th>User</th><th>Role</th><th>Status</th><th>Actions</th></tr>
      </thead>
      <tbody>
        <tr v-for="user in users" :key="user.id">
          <td>{{ user.login }} · #{{ user.pilot_number }}</td>
          <td>
            <div class="role-checks">
              <label v-for="role in roles" :key="role" class="role-check">
                <input
                  type="checkbox"
                  :checked="user.role === role"
                  @change="chooseRole(user, role)"
                />
                <span>{{ role }}</span>
              </label>
            </div>
          </td>
          <td>{{ user.status }}</td>
          <td class="toolbar">
            <button class="button danger" :disabled="user.role === 'admin'" @click="ban(user)">Ban</button>
            <button class="button" @click="unban(user)">Unban</button>
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

