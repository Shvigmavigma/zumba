<script setup>
// Create / edit a championship in a dialog. The form object lives in the page
// (so a closed dialog keeps the draft); every change here emits a new copy.
import { computed, nextTick, ref, useId, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { onKeyStroke } from '@vueuse/core'
import { AlertTriangle, Plus, Trash2, X } from 'lucide-vue-next'
import FormField from '../../ui/FormField.vue'
import SwitchToggle from '../../ui/SwitchToggle.vue'
import StageFields from './StageFields.vue'
import { useFieldModels } from './fieldModels'
import { defaultStage, resetForGame, toggleInList } from './helpers'

const props = defineProps({
  open: { type: Boolean, default: false },
  mode: { type: String, default: 'create' },
  /** Track/class lists for the form's game. */
  assets: { type: Object, default: () => ({ tracks: [], classes: [] }) },
  gameChoices: { type: Array, default: () => [] },
  saving: { type: Boolean, default: false },
  error: { type: String, default: '' }
})
const emit = defineEmits(['submit', 'close'])
const form = defineModel('form', { type: Object, required: true })

const { t } = useI18n()
const titleId = `champ-form-${useId()}`
const firstInput = ref(null)
const isCreate = computed(() => props.mode === 'create')
const selectedClasses = computed(() => new Set(form.value.classes || []))
const fields = useFieldModels(form, [
  'name', 'description', 'video_url',
  'registration_start', 'registration_end', 'championship_start', 'championship_end',
  'car_change_allowed', 'is_team_event', 'is_published'
])

function setGame(game) {
  form.value = resetForGame({ ...form.value, game })
}

function toggleClass(name) {
  form.value = { ...form.value, classes: toggleInList(form.value.classes || [], name) }
}

function addStage() {
  form.value = { ...form.value, stages: [...form.value.stages, { ...defaultStage(), is_team_event: form.value.is_team_event }] }
}

function removeStage(index) {
  form.value = { ...form.value, stages: form.value.stages.filter((_, position) => position !== index) }
}

function updateStage(index, stage) {
  form.value = { ...form.value, stages: form.value.stages.map((item, position) => (position === index ? stage : item)) }
}

onKeyStroke('Escape', () => {
  if (props.open) emit('close')
})

watch(() => props.open, async (open) => {
  if (!open) return
  await nextTick()
  firstInput.value?.focus({ preventScroll: true })
})
</script>

<template>
  <Teleport to="body">
    <Transition name="champ-modal">
      <div v-if="open" class="ui-modal-backdrop champ-modal">
        <form class="ui-modal ui-modal--wide champ-modal__panel" role="dialog" aria-modal="true" :aria-labelledby="titleId" @submit.prevent="emit('submit')">
          <header class="ui-modal__head champ-modal__head">
            <div class="champ-modal__heading">
              <p class="ui-eyebrow ui-eyebrow--accent">{{ t('champPage.manage.eyebrow') }}</p>
              <h2 :id="titleId" class="ui-title">{{ isCreate ? t('championships.createTitle') : t('championships.editTitle') }}</h2>
            </div>
            <button class="ui-btn ui-btn--ghost ui-btn--icon" type="button" :aria-label="t('common.close')" @click="emit('close')"><X :size="18" /></button>
          </header>

          <p v-if="error" class="ui-alert" role="alert"><AlertTriangle :size="18" /><span>{{ error }}</span></p>

          <section class="champ-modal__section">
            <h3 class="champ-modal__step"><span class="ui-num">01</span>{{ t('champPage.form.basics') }}</h3>
            <div class="ui-form-row">
              <FormField :label="t('fields.name')" required :count="(form.name || '').length" :max="120">
                <template #default="{ id }">
                  <input :id="id" ref="firstInput" v-model="fields.name" class="ui-input" required maxlength="120" />
                </template>
              </FormField>
              <FormField :label="t('fields.game')" required :hint="t('champPage.form.gameHint')">
                <template #default="{ id, describedBy }">
                  <select :id="id" class="ui-select" :value="form.game" :aria-describedby="describedBy" @change="setGame($event.target.value)">
                    <option v-for="option in gameChoices" :key="option.value" :value="option.value">{{ option.value }}</option>
                  </select>
                </template>
              </FormField>
            </div>
            <FormField :label="t('fields.description')" :count="(form.description || '').length" :max="3000" :optional-label="t('champPage.form.optional')">
              <template #default="{ id }">
                <textarea :id="id" v-model="fields.description" class="ui-textarea" maxlength="3000"></textarea>
              </template>
            </FormField>
            <FormField :label="t('championships.video')" :hint="t('champPage.form.videoHint')" :optional-label="t('champPage.form.optional')">
              <template #default="{ id, describedBy }">
                <input :id="id" v-model="fields.video_url" class="ui-input" maxlength="255" placeholder="https://..." :aria-describedby="describedBy" />
              </template>
            </FormField>
          </section>

          <section class="champ-modal__section">
            <h3 class="champ-modal__step"><span class="ui-num">02</span>{{ t('champPage.form.classes') }} <span class="champ-modal__req" aria-hidden="true">*</span></h3>
            <p class="champ-modal__hint">{{ t('champPage.form.classesHint') }}</p>
            <div v-if="assets.classes?.length" class="champ-modal__classes" role="group" :aria-label="t('champPage.form.classes')">
              <button
                v-for="item in assets.classes"
                :key="item.name"
                class="champ-modal__class"
                :class="{ 'is-on': selectedClasses.has(item.name) }"
                type="button"
                :aria-pressed="selectedClasses.has(item.name)"
                @click="toggleClass(item.name)"
              >
                {{ item.name }}
                <small class="ui-num">{{ t('champPage.form.cars', { count: item.cars?.length || 0 }) }}</small>
              </button>
            </div>
            <p v-else class="champ-modal__empty">{{ t('champPage.form.noClasses') }}</p>
          </section>

          <section class="champ-modal__section">
            <h3 class="champ-modal__step"><span class="ui-num">03</span>{{ t('champPage.form.dates') }}</h3>
            <div class="ui-form-row">
              <FormField :label="t('fields.registrationStart')" required>
                <template #default="{ id }"><input :id="id" v-model="fields.registration_start" class="ui-input" type="datetime-local" required /></template>
              </FormField>
              <FormField :label="t('fields.registrationEnd')" required>
                <template #default="{ id }"><input :id="id" v-model="fields.registration_end" class="ui-input" type="datetime-local" required /></template>
              </FormField>
            </div>
            <div class="ui-form-row">
              <FormField :label="t('championships.championshipStart')" required>
                <template #default="{ id }"><input :id="id" v-model="fields.championship_start" class="ui-input" type="datetime-local" required /></template>
              </FormField>
              <FormField :label="t('championships.championshipEnd')" required>
                <template #default="{ id }"><input :id="id" v-model="fields.championship_end" class="ui-input" type="datetime-local" required /></template>
              </FormField>
            </div>
          </section>

          <section class="champ-modal__section">
            <h3 class="champ-modal__step"><span class="ui-num">04</span>{{ t('champPage.form.rules') }}</h3>
            <div class="champ-modal__switches">
              <SwitchToggle v-model="fields.car_change_allowed" :label="t('championships.carCanChange')" :hint="t('champPage.form.carChangeHint')" />
              <SwitchToggle v-model="fields.is_team_event" :label="t('champPage.form.teamChampionship')" :hint="t('champPage.form.teamHint')" />
              <SwitchToggle v-model="fields.is_published" :label="t('championships.published')" :hint="t('champPage.form.publishHint')" />
            </div>
          </section>

          <section v-if="isCreate" class="champ-modal__section">
            <div class="champ-modal__stages-head">
              <h3 class="champ-modal__step"><span class="ui-num">05</span>{{ t('championships.stages') }}</h3>
              <button class="ui-btn ui-btn--outline ui-btn--sm" type="button" @click="addStage"><Plus :size="15" />{{ t('championships.stage') }}</button>
            </div>
            <p class="champ-modal__hint">{{ t('champPage.form.stagesHint') }}</p>
            <TransitionGroup tag="ol" name="ui-fade" class="champ-modal__stage-list">
              <li v-for="(stage, index) in form.stages" :key="index" class="champ-modal__stage ui-sunken">
                <div class="champ-modal__stage-head">
                  <strong class="ui-num">R{{ index + 1 }}</strong>
                  <button class="ui-btn ui-btn--ghost ui-btn--sm ui-btn--icon" type="button" :title="t('championships.deleteStage')" :aria-label="t('championships.deleteStage')" @click="removeStage(index)"><Trash2 :size="15" /></button>
                </div>
                <StageFields
                  :model-value="stage"
                  :game="form.game"
                  :assets="assets"
                  :name-placeholder="t('championships.stageNumber', { number: index + 1 })"
                  @update:model-value="updateStage(index, $event)"
                />
              </li>
            </TransitionGroup>
          </section>

          <footer class="champ-modal__footer">
            <button class="ui-btn ui-btn--ghost" type="button" @click="emit('close')">{{ t('champPage.form.cancel') }}</button>
            <button v-spark class="ui-btn ui-btn--primary" type="submit" :disabled="saving">
              {{ saving ? t('common.saving') : (isCreate ? t('championships.createChampionship') : t('championships.saveChanges')) }}
            </button>
          </footer>
        </form>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.champ-modal {
  align-items: start;
  overscroll-behavior: contain;
}

.champ-modal__panel {
  gap: 22px;
  margin-block: clamp(0px, 4vh, 40px);
  max-height: none;
  overflow: visible;
}

.champ-modal__head {
  align-items: center;
}

.champ-modal__heading {
  display: grid;
  gap: 8px;
}

.champ-modal__section {
  display: grid;
  gap: 14px;
  padding-top: 18px;
  border-top: 1px solid var(--c-line);
}

.champ-modal__step {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 0;
  color: var(--c-text);
  font-family: var(--font-body);
  font-size: 15px;
  font-weight: 650;
  letter-spacing: 0;
}

.champ-modal__step .ui-num {
  color: var(--c-accent-text);
  font-size: 12px;
  font-weight: 700;
}

.champ-modal__req {
  color: var(--bm-blue-bright);
}

.champ-modal__hint,
.champ-modal__empty {
  margin: -6px 0 0;
  color: var(--c-text-3);
  font-size: 13px;
}

.champ-modal__classes {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.champ-modal__class {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 14px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-pill);
  background: var(--c-sunken);
  color: var(--c-text-2);
  cursor: pointer;
  font: inherit;
  font-size: 13.5px;
  font-weight: 600;
  transition: background-color var(--dur-2), border-color var(--dur-2), color var(--dur-2), transform var(--dur-2) var(--ease-ios);
}

.champ-modal__class:hover {
  border-color: var(--c-blue-line);
  color: var(--c-text);
}

.champ-modal__class:active {
  transform: scale(0.96);
}

.champ-modal__class small {
  color: var(--c-text-3);
  font-size: 11px;
}

.champ-modal__class.is-on {
  border-color: transparent;
  background: var(--bm-blue);
  color: #fff;
  box-shadow: var(--shadow-blue);
}

.champ-modal__class.is-on small {
  color: rgba(255, 255, 255, 0.75);
}

.champ-modal__switches {
  display: grid;
  gap: 14px;
}

.champ-modal__stages-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.champ-modal__stage-list {
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.champ-modal__stage {
  display: grid;
  gap: 12px;
  padding: 14px 16px;
  border-radius: var(--r-lg);
}

.champ-modal__stage-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--c-text);
}

.champ-modal__footer {
  position: sticky;
  bottom: -1px;
  z-index: 2;
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
  margin: 0 calc(clamp(18px, 2.4vw, 26px) * -1) calc(clamp(18px, 2.4vw, 26px) * -1);
  padding: 14px clamp(18px, 2.4vw, 26px);
  border-top: 1px solid var(--c-line);
  border-radius: 0 0 var(--r-xl) var(--r-xl);
  background: color-mix(in srgb, var(--c-surface-solid) 92%, transparent);
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
}

.champ-modal-enter-active,
.champ-modal-leave-active {
  transition: opacity var(--dur-2) var(--ease-out);
}

.champ-modal-enter-active .champ-modal__panel,
.champ-modal-leave-active .champ-modal__panel {
  transition: transform var(--dur-3) var(--ease-ios), opacity var(--dur-2) var(--ease-out);
}

.champ-modal-enter-from,
.champ-modal-leave-to {
  opacity: 0;
}

.champ-modal-enter-from .champ-modal__panel,
.champ-modal-leave-to .champ-modal__panel {
  opacity: 0;
  transform: translateY(18px) scale(0.98);
}

@media (prefers-reduced-motion: reduce) {
  .champ-modal-enter-active,
  .champ-modal-leave-active,
  .champ-modal-enter-active .champ-modal__panel,
  .champ-modal-leave-active .champ-modal__panel {
    transition: none;
  }
}
</style>
