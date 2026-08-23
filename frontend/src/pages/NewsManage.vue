<script setup>
import { computed, onMounted, ref } from 'vue'
import { Eye, EyeOff, Pin, PinOff, Plus, Save, Trash2 } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { isVideoUrl, mediaUploadAccept } from '../media'
import { formatDateTime } from '../timezone'

const { t } = useI18n()
const items = ref([])
const error = ref('')
const saving = ref(false)
const busyItems = ref({})
const newsSettings = ref({ auto_rotate_seconds: 30, manual_pause_minutes: 5 })
const newsSettingsSaving = ref(false)
const newsSettingsSaved = ref(false)
const fileInput = ref(null)
const form = ref({
  title: '',
  body: '',
  is_published: true,
  is_pinned: false,
  file: null
})

const sortedItems = computed(() => [...items.value].sort((a, b) => Number(b.is_pinned) - Number(a.is_pinned) || new Date(b.created_at) - new Date(a.created_at)))

function formatDate(value) {
  return formatDateTime(value)
}

async function load() {
  error.value = ''
  try {
    const [loadedItems, loadedSettings] = await Promise.all([api('/news/manage'), api('/app-settings/news')])
    items.value = loadedItems
    newsSettings.value = {
      auto_rotate_seconds: loadedSettings.auto_rotate_seconds,
      manual_pause_minutes: Math.round(Number(loadedSettings.manual_pause_seconds || 0) / 60)
    }
  } catch (err) {
    error.value = err.message
  }
}

function chooseFile(event) {
  form.value.file = event.target.files?.[0] || null
}

function resetForm() {
  form.value = {
    title: '',
    body: '',
    is_published: true,
    is_pinned: false,
    file: null
  }
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

async function createNews() {
  if (!form.value.file) return
  error.value = ''
  saving.value = true
  try {
    const body = new FormData()
    body.append('title', form.value.title)
    body.append('body', form.value.body)
    body.append('is_published', String(form.value.is_published))
    body.append('is_pinned', String(form.value.is_pinned))
    body.append('file', form.value.file)
    const created = await api('/news', { method: 'POST', body })
    items.value = [created, ...items.value.map((item) => (created.is_pinned ? { ...item, is_pinned: false } : item))]
    resetForm()
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}

async function saveNews(item) {
  error.value = ''
  busyItems.value = { ...busyItems.value, [item.id]: true }
  try {
    const updated = await api(`/news/${item.id}`, {
      method: 'PATCH',
      body: {
        title: item.title,
        body: item.body,
        is_published: item.is_published,
        is_pinned: item.is_pinned
      }
    })
    items.value = items.value.map((news) => {
      if (news.id === updated.id) return updated
      return updated.is_pinned ? { ...news, is_pinned: false } : news
    })
  } catch (err) {
    error.value = err.message
  } finally {
    busyItems.value = { ...busyItems.value, [item.id]: false }
  }
}

async function togglePublished(item) {
  item.is_published = !item.is_published
  await saveNews(item)
}

async function togglePinned(item) {
  item.is_pinned = !item.is_pinned
  await saveNews(item)
}

async function saveNewsSettings() {
  newsSettingsSaving.value = true
  newsSettingsSaved.value = false
  error.value = ''
  try {
    const saved = await api('/app-settings/news', {
      method: 'PATCH',
      body: {
        auto_rotate_seconds: Number(newsSettings.value.auto_rotate_seconds),
        manual_pause_seconds: Math.max(0, Number(newsSettings.value.manual_pause_minutes) || 0) * 60
      }
    })
    newsSettings.value = {
      auto_rotate_seconds: saved.auto_rotate_seconds,
      manual_pause_minutes: Math.round(Number(saved.manual_pause_seconds || 0) / 60)
    }
    newsSettingsSaved.value = true
  } catch (err) {
    error.value = err.message
  } finally {
    newsSettingsSaving.value = false
  }
}

async function deleteNews(item) {
  if (!window.confirm(t('news.confirmDelete', { title: item.title }))) return
  error.value = ''
  busyItems.value = { ...busyItems.value, [item.id]: true }
  try {
    await api(`/news/${item.id}`, { method: 'DELETE' })
    items.value = items.value.filter((news) => news.id !== item.id)
  } catch (err) {
    error.value = err.message
  } finally {
    busyItems.value = { ...busyItems.value, [item.id]: false }
  }
}

onMounted(load)
</script>

<template>
  <section class="section news-manage-page">
    <div class="section-header">
      <div>
        <h1>{{ t('news.manageTitle') }}</h1>
        <p class="muted">{{ t('news.subtitle') }}</p>
      </div>
      <span class="pill">{{ items.length }}</span>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <form class="card news-settings-form" @submit.prevent="saveNewsSettings">
      <div>
        <h2>{{ t('news.autoSettingsTitle') }}</h2>
        <p class="muted">{{ t('news.autoSettingsHint') }}</p>
      </div>
      <label class="field">
        <span>{{ t('news.autoIntervalField') }}</span>
        <input v-model.number="newsSettings.auto_rotate_seconds" type="number" min="5" max="3600" required />
      </label>
      <label class="field">
        <span>{{ t('news.manualPauseField') }}</span>
        <input v-model.number="newsSettings.manual_pause_minutes" type="number" min="0" max="60" required />
      </label>
      <button class="button primary" type="submit" :disabled="newsSettingsSaving">
        <Save :size="16" />
        {{ t('common.save') }}
      </button>
      <span v-if="newsSettingsSaved" class="pill">{{ t('common.saved') }}</span>
    </form>

    <form class="card news-create-form" @submit.prevent="createNews">
      <h2>{{ t('news.addTitle') }}</h2>
      <div class="form-row">
        <label class="field">
          <span>{{ t('fields.title') }}</span>
          <input v-model="form.title" required maxlength="120" />
        </label>
        <label class="news-publish-toggle">
          <input v-model="form.is_pinned" type="checkbox" />
          <Pin :size="16" />
          <span>{{ t('news.pinned') }}</span>
        </label>
        <label class="field">
          <span>{{ t('news.image') }}</span>
          <input ref="fileInput" type="file" :accept="mediaUploadAccept" required @change="chooseFile" />
        </label>
      </div>
      <label class="field">
        <span>{{ t('fields.text') }}</span>
        <textarea v-model="form.body" required maxlength="1000" />
      </label>
      <div class="news-form-actions">
        <label class="news-publish-toggle">
          <input v-model="form.is_published" type="checkbox" />
          <span>{{ t('news.published') }}</span>
        </label>
        <button class="button primary" type="submit" :disabled="saving || !form.file">
          <Plus :size="16" />
          {{ t('common.create') }}
        </button>
      </div>
    </form>

    <div class="news-manage-list">
      <article v-for="item in sortedItems" :key="item.id" class="card news-manage-card">
        <video v-if="isVideoUrl(item.image_url)" :src="item.image_url" controls playsinline preload="metadata"></video>
        <img v-else :src="item.image_url" alt="" />
        <div class="news-manage-body">
          <div class="section-header news-manage-card-head">
            <div>
              <span class="pill">{{ item.is_published ? t('news.published') : t('news.hidden') }}</span>
              <span v-if="item.is_pinned" class="pill news-pinned-badge"><Pin :size="13" /> {{ t('news.pinned') }}</span>
              <p class="muted">{{ formatDate(item.created_at) }}</p>
            </div>
            <div class="toolbar">
              <button class="button news-publish-button" type="button" :disabled="busyItems[item.id]" @click="togglePublished(item)">
                <EyeOff v-if="item.is_published" :size="16" />
                <Eye v-else :size="16" />
                {{ item.is_published ? t('news.hide') : t('news.publish') }}
              </button>
              <button class="button news-publish-button" type="button" :disabled="busyItems[item.id]" @click="togglePinned(item)">
                <PinOff v-if="item.is_pinned" :size="16" />
                <Pin v-else :size="16" />
                {{ item.is_pinned ? t('news.unpin') : t('news.pin') }}
              </button>
              <button class="icon-button danger-icon" type="button" :title="t('common.delete')" :disabled="busyItems[item.id]" @click="deleteNews(item)">
                <Trash2 :size="16" />
              </button>
            </div>
          </div>
          <label class="field">
            <span>{{ t('fields.title') }}</span>
            <input v-model="item.title" maxlength="120" />
          </label>
          <label class="news-publish-toggle">
            <input v-model="item.is_pinned" type="checkbox" />
            <Pin :size="16" />
            <span>{{ t('news.pinned') }}</span>
          </label>
          <label class="field">
            <span>{{ t('fields.text') }}</span>
            <textarea v-model="item.body" maxlength="1000" />
          </label>
          <button class="button" type="button" :disabled="busyItems[item.id]" @click="saveNews(item)">
            <Save :size="16" />
            {{ t('common.save') }}
          </button>
        </div>
      </article>

      <div v-if="!items.length" class="empty-row">{{ t('news.empty') }}</div>
    </div>
  </section>
</template>
