<script setup>
// "New team" request as an iOS-style sheet: live livery preview on top, the
// four fields below, a reminder that a moderator approves the request.
import { computed, nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { onKeyStroke } from '@vueuse/core'
import { AlertCircle, Info, Plus, X } from 'lucide-vue-next'
import { state } from '../../store'
import TeamCard from './TeamCard.vue'
import TeamFormFields from './TeamFormFields.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
  error: { type: String, default: '' },
  limit: { type: Number, default: 0 }
})
const form = defineModel('form', { type: Object, required: true })
const emit = defineEmits(['close', 'submit'])
const { t } = useI18n()
const titleId = `team-create-${useId()}`
const sheet = ref(null)

const preview = computed(() => ({
  ...form.value,
  id: 0,
  avatar_url: '',
  owner_nickname: state.user?.nickname || state.user?.login || '',
  member_count: 1,
  member_limit: props.limit || 1,
  average_rating: state.user?.rating ?? 0,
  pending_application_count: 0
}))

function lockScroll(locked) {
  document.documentElement.style.overflow = locked ? 'hidden' : ''
}

watch(() => props.open, async (open) => {
  lockScroll(open)
  if (!open) return
  await nextTick()
  sheet.value?.querySelector('input')?.focus({ preventScroll: true })
})

onKeyStroke('Escape', () => {
  if (props.open) emit('close')
})

onBeforeUnmount(() => lockScroll(false))
</script>

<template>
  <Teleport to="body">
    <Transition name="tsheet" :duration="{ enter: 560, leave: 260 }">
      <div v-if="open" class="ui-modal-backdrop tsheet" @click.self="emit('close')">
        <form ref="sheet" class="ui-modal tsheet__panel" role="dialog" aria-modal="true" :aria-labelledby="titleId" @submit.prevent="emit('submit')">
          <header class="ui-modal__head">
            <div class="tsheet__title">
              <p class="ui-eyebrow ui-eyebrow--accent">{{ t('teamsPage.create.eyebrow') }}</p>
              <h2 :id="titleId" class="ui-title">{{ t('teams.createTitle') }}</h2>
            </div>
            <button class="ui-btn ui-btn--ghost ui-btn--icon ui-btn--sm" type="button" :aria-label="t('common.close')" :title="t('common.close')" @click="emit('close')">
              <X :size="18" />
            </button>
          </header>

          <div class="tsheet__grid">
            <div class="tsheet__preview">
              <p class="ui-eyebrow">{{ t('teamsPage.create.preview') }}</p>
              <TeamCard preview :team="preview" />
            </div>
            <TeamFormFields v-model="form" :description-placeholder="t('teams.descriptionPlaceholder')" />
          </div>

          <Transition name="ui-fade">
            <p v-if="error" class="ui-alert" role="alert"><AlertCircle :size="18" /><span>{{ error }}</span></p>
          </Transition>
          <p class="ui-alert ui-alert--info"><Info :size="18" /><span>{{ t('teams.createHint') }}</span></p>

          <footer class="tsheet__actions">
            <button class="ui-btn ui-btn--ghost" type="button" @click="emit('close')">{{ t('teamsPage.create.cancel') }}</button>
            <button v-spark class="ui-btn ui-btn--primary" type="submit" :disabled="saving">
              <Plus :size="16" />{{ saving ? t('common.saving') : t('teams.sendCreateRequest') }}
            </button>
          </footer>
        </form>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.tsheet__panel {
  width: min(880px, 100%);
  gap: 20px;
}

.tsheet__title {
  display: grid;
  gap: 8px;
}

.tsheet__grid {
  display: grid;
  grid-template-columns: minmax(240px, 300px) minmax(0, 1fr);
  align-items: start;
  gap: 24px;
}

.tsheet__preview {
  position: sticky;
  top: 0;
  display: grid;
  gap: 10px;
}

.tsheet__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

/* Backdrop fades, the sheet springs up from below. */
.tsheet-enter-active,
.tsheet-leave-active {
  transition: opacity var(--dur-2) var(--ease-out);
}

.tsheet-enter-active .tsheet__panel {
  transition: transform 560ms var(--ease-spring), opacity var(--dur-3) var(--ease-out);
}

.tsheet-leave-active .tsheet__panel {
  transition: transform var(--dur-2) ease-in, opacity var(--dur-2) ease-in;
}

.tsheet-enter-from,
.tsheet-leave-to {
  opacity: 0;
}

.tsheet-enter-from .tsheet__panel,
.tsheet-leave-to .tsheet__panel {
  opacity: 0;
  transform: translateY(32px) scale(0.96);
}

@media (max-width: 760px) {
  .tsheet__grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .tsheet__preview {
    position: static;
    max-width: 340px;
  }
}

@media (max-width: 560px) {
  .tsheet {
    align-items: end;
    padding: 0;
  }

  .tsheet__panel {
    max-height: calc(100dvh - 24px);
    border-radius: var(--r-xl) var(--r-xl) 0 0;
    padding-bottom: calc(20px + env(safe-area-inset-bottom));
  }

  .tsheet-enter-from .tsheet__panel,
  .tsheet-leave-to .tsheet__panel {
    transform: translateY(100%);
  }

  .tsheet__actions .ui-btn {
    flex: 1 1 auto;
  }
}

@media (prefers-reduced-motion: reduce) {
  .tsheet-enter-active .tsheet__panel,
  .tsheet-leave-active .tsheet__panel {
    transition: opacity var(--dur-1);
  }

  .tsheet-enter-from .tsheet__panel,
  .tsheet-leave-to .tsheet__panel {
    transform: none;
  }
}
</style>
