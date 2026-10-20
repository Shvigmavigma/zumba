<script setup>
// One legal document, picked by the route (meta.legalDocument). Russian only:
// the operator publishes a single legally binding edition.
import { ArrowLeft } from 'lucide-vue-next'
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { LEGAL_OPERATOR, legalDocuments } from '../legalDocuments'
import PageHeader from '../ui/PageHeader.vue'

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

const siblings = [
  { path: '/privacy-policy', key: 'privacy', label: 'Политика' },
  { path: '/terms', key: 'terms', label: 'Соглашение' },
  { path: '/cookies', key: 'cookies', label: 'Cookies' }
]
</script>

<template>
  <article class="ui-page ui-shell legal-doc">
    <RouterLink class="ui-btn ui-btn--ghost ui-btn--sm legal-doc__back" :to="backTarget">
      <ArrowLeft :size="16" />{{ backLabel }}
    </RouterLink>

    <PageHeader :key="documentKey" eyebrow="BMRL" :title="document.title" :lead="`Редакция от ${document.updatedAt}`" compact>
      <template #below>
        <p class="legal-doc__operator">
          Оператор: {{ LEGAL_OPERATOR.name }} ·
          <a class="ui-link" :href="`mailto:${LEGAL_OPERATOR.email}`">{{ LEGAL_OPERATOR.email }}</a>
        </p>
      </template>
    </PageHeader>

    <nav class="legal-doc__tabs" aria-label="Правовые документы">
      <RouterLink
        v-for="item in siblings"
        :key="item.key"
        class="legal-doc__tab"
        :class="{ 'is-active': item.key === documentKey }"
        :aria-current="item.key === documentKey ? 'page' : undefined"
        :to="{ path: item.path, query: route.query }"
      >{{ item.label }}</RouterLink>
    </nav>

    <div class="legal-doc__body ui-card">
      <section v-for="section in document.sections" :key="section.title" class="legal-doc__section">
        <h2>{{ section.title }}</h2>
        <p v-for="paragraph in section.paragraphs" :key="paragraph">{{ paragraph }}</p>
      </section>
    </div>
  </article>
</template>

<style scoped>
.legal-doc {
  max-width: 920px;
}

.legal-doc__back {
  justify-self: start;
}

.legal-doc__operator {
  margin: 0;
  color: var(--c-text-3);
  font-size: 13px;
}

.legal-doc__tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.legal-doc__tab {
  padding: 8px 16px;
  border: 1px solid var(--c-line);
  border-radius: 999px;
  color: var(--c-text-2);
  font-size: 13.5px;
  font-weight: 600;
  text-decoration: none;
  transition: color var(--dur-1), border-color var(--dur-1), background var(--dur-1);
}

.legal-doc__tab:hover {
  color: var(--c-text);
}

.legal-doc__tab.is-active {
  border-color: var(--bm-blue);
  background: var(--bm-blue);
  color: #fff;
}

.legal-doc__body {
  display: grid;
  gap: clamp(20px, 2.6vw, 30px);
  padding: clamp(20px, 3.4vw, 40px);
}

.legal-doc__section {
  display: grid;
  gap: 10px;
}

.legal-doc__section h2 {
  margin: 0;
  color: var(--c-text);
  font-size: var(--fs-h3);
}

.legal-doc__section p {
  margin: 0;
  max-width: 74ch;
  color: var(--c-text-2);
  font-size: var(--fs-body);
  line-height: 1.65;
  overflow-wrap: anywhere;
}
</style>
