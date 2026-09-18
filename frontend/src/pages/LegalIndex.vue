<script setup>
import { ArrowLeft, ChevronRight, FileText } from 'lucide-vue-next'
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { LEGAL_OPERATOR, legalDocuments } from '../legalDocuments'

const route = useRoute()
const backTarget = computed(() => route.query.from === 'registration' ? '/register' : '/')
const backLabel = computed(() => route.query.from === 'registration' ? 'Назад к регистрации' : 'Назад на главную')

const documents = [
  {
    path: '/privacy-policy',
    title: legalDocuments.privacy.title,
    description: 'Какие данные обрабатываются, зачем они нужны и как защищаются.'
  },
  {
    path: '/terms',
    title: legalDocuments.terms.title,
    description: 'Правила аккаунта, заявок, модерации, соревнований и рейтинга.'
  },
  {
    path: '/cookies',
    title: legalDocuments.cookies.title,
    description: 'Технические cookie и внешние сервисы, используемые BMRL.'
  }
]
</script>

<template>
  <section class="section card legal-index">
    <div class="legal-index-topline">
      <RouterLink class="button small legal-back-button" :to="backTarget">
        <ArrowLeft :size="16" />
        <span>{{ backLabel }}</span>
      </RouterLink>
    </div>

    <header class="legal-index-header">
      <p class="eyebrow">BMRL</p>
      <h1>Правовая информация</h1>
      <p class="muted">Все документы сервиса собраны в одном месте.</p>
    </header>

    <nav class="legal-index-list" aria-label="Правовые документы">
      <RouterLink v-for="document in documents" :key="document.path" class="legal-index-link" :to="{ path: document.path, query: route.query }">
        <span class="legal-index-icon"><FileText :size="20" /></span>
        <span class="legal-index-copy">
          <strong>{{ document.title }}</strong>
          <small>{{ document.description }}</small>
        </span>
        <ChevronRight :size="18" />
      </RouterLink>
    </nav>

    <p class="legal-index-operator">
      Оператор: {{ LEGAL_OPERATOR.name }} ·
      <a :href="`mailto:${LEGAL_OPERATOR.email}`">{{ LEGAL_OPERATOR.email }}</a>
    </p>
  </section>
</template>
