<script setup>
// The legal documents in one place. They are Russian only, like the documents
// themselves: the operator publishes a single legally binding edition.
import { ArrowLeft, ChevronRight, Cookie, FileText, ShieldCheck } from 'lucide-vue-next'
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { LEGAL_OPERATOR, legalDocuments } from '../legalDocuments'
import PageHeader from '../ui/PageHeader.vue'

const route = useRoute()
const backTarget = computed(() => route.query.from === 'registration' ? '/register' : '/')
const backLabel = computed(() => route.query.from === 'registration' ? 'Назад к регистрации' : 'Назад на главную')

const documents = [
  {
    path: '/privacy-policy',
    icon: ShieldCheck,
    title: legalDocuments.privacy.title,
    description: 'Какие данные обрабатываются, зачем они нужны и как защищаются.'
  },
  {
    path: '/terms',
    icon: FileText,
    title: legalDocuments.terms.title,
    description: 'Правила аккаунта, заявок, модерации, соревнований и рейтинга.'
  },
  {
    path: '/cookies',
    icon: Cookie,
    title: legalDocuments.cookies.title,
    description: 'Технические cookie и внешние сервисы, используемые BMRL.'
  }
]
</script>

<template>
  <div class="ui-page ui-shell legal">
    <RouterLink class="ui-btn ui-btn--ghost ui-btn--sm legal__back" :to="backTarget">
      <ArrowLeft :size="16" />{{ backLabel }}
    </RouterLink>

    <PageHeader eyebrow="BMRL" title="Правовая информация" lead="Все документы сервиса собраны в одном месте." />

    <nav class="legal__list" aria-label="Правовые документы">
      <RouterLink
        v-for="(document, index) in documents"
        :key="document.path"
        v-reveal="{ delay: index * 70, y: 14 }"
        class="legal__doc ui-card"
        :to="{ path: document.path, query: route.query }"
      >
        <span class="legal__icon"><component :is="document.icon" :size="20" /></span>
        <span class="legal__copy">
          <strong>{{ document.title }}</strong>
          <small>{{ document.description }}</small>
        </span>
        <ChevronRight class="legal__arrow" :size="18" />
      </RouterLink>
    </nav>

    <p class="legal__operator">
      Оператор: {{ LEGAL_OPERATOR.name }} ·
      <a class="ui-link" :href="`mailto:${LEGAL_OPERATOR.email}`">{{ LEGAL_OPERATOR.email }}</a>
    </p>
  </div>
</template>

<style scoped>
.legal {
  max-width: 860px;
}

.legal__back {
  justify-self: start;
}

.legal__list {
  display: grid;
  gap: 12px;
}

.legal__doc {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;
  color: var(--c-text);
  text-decoration: none;
  transition: transform var(--dur-2) var(--ease-ios), border-color var(--dur-2) var(--ease-ios);
}

.legal__doc:hover {
  border-color: color-mix(in srgb, var(--bm-blue) 45%, var(--c-line));
  transform: translateY(-2px);
}

.legal__icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: var(--r-md);
  background: color-mix(in srgb, var(--bm-blue) 12%, transparent);
  color: var(--c-accent-text);
}

.legal__copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.legal__copy strong {
  font-size: 16px;
}

.legal__copy small {
  color: var(--c-text-2);
  font-size: 13.5px;
}

.legal__arrow {
  color: var(--c-text-3);
  transition: transform var(--dur-2) var(--ease-ios);
}

.legal__doc:hover .legal__arrow {
  color: var(--c-accent-text);
  transform: translateX(3px);
}

.legal__operator {
  margin: 0;
  color: var(--c-text-3);
  font-size: 13px;
}

@media (prefers-reduced-motion: reduce) {
  .legal__doc,
  .legal__arrow {
    transition: none;
  }
}
</style>
