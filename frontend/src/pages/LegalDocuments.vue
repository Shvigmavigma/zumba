<script setup>
import { ArrowLeft } from 'lucide-vue-next'
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { LEGAL_OPERATOR, legalDocuments } from '../legalDocuments'

const route = useRoute()

const documentKey = computed(() => route.meta.legalDocument || 'privacy')
const document = computed(() => legalDocuments[documentKey.value] || legalDocuments.privacy)
const backTarget = computed(() => {
  if (route.query.from === 'registration') return '/register'
  if (route.query.from === 'main') return '/'
  return '/legal'
})
const backLabel = computed(() => {
  if (route.query.from === 'registration') return 'Назад к регистрации'
  if (route.query.from === 'main') return 'Назад на главную'
  return 'Назад к документам'
})
</script>

<template>
  <article class="section card legal-document">
    <div class="legal-document-topline">
      <RouterLink class="button small legal-back-button" :to="backTarget">
        <ArrowLeft :size="16" />
        <span>{{ backLabel }}</span>
      </RouterLink>
    </div>
    <header class="legal-document-header">
      <p class="eyebrow">BMRL</p>
      <h1>{{ document.title }}</h1>
      <p class="muted">Редакция от {{ document.updatedAt }}</p>
      <p class="muted">Оператор: {{ LEGAL_OPERATOR.name }} · <a :href="`mailto:${LEGAL_OPERATOR.email}`">{{ LEGAL_OPERATOR.email }}</a></p>
    </header>

    <section v-for="section in document.sections" :key="section.title" class="legal-document-section">
      <h2>{{ section.title }}</h2>
      <p v-for="paragraph in section.paragraphs" :key="paragraph">{{ paragraph }}</p>
    </section>

    <nav class="legal-document-links" aria-label="Правовые документы">
      <RouterLink :to="{ path: '/privacy-policy', query: route.query }">Политика</RouterLink>
      <RouterLink :to="{ path: '/terms', query: route.query }">Соглашение</RouterLink>
      <RouterLink :to="{ path: '/cookies', query: route.query }">Cookies</RouterLink>
    </nav>
  </article>
</template>
