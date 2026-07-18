<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'

const banners = ref([])
const error = ref('')

async function load() {
  banners.value = await api('/banners')
}

async function save(banner) {
  try {
    await api(`/banners/${banner.position}`, { method: 'PUT', body: banner })
    await load()
  } catch (err) {
    error.value = err.message
  }
}

onMounted(load)
</script>

<template>
  <section class="section">
    <h1>BannerEdit</h1>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="grid cols-2">
      <article v-for="banner in banners" :key="banner.position" class="card">
        <h3>{{ banner.position }}</h3>
        <label class="field"><span>Image URL</span><input v-model="banner.image_url" /></label>
        <label class="field"><span>Link URL</span><input v-model="banner.link_url" /></label>
        <button class="button primary" @click="save(banner)">Save</button>
      </article>
    </div>
  </section>
</template>

