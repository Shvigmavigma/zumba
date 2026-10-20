<script setup>
// Name, abbreviation, livery colour and description — shared by the
// "create team" request and the owner's team card editor.
import { useI18n } from 'vue-i18n'
import { Check, Pipette } from 'lucide-vue-next'
import FormField from '../../ui/FormField.vue'
import { normalizeTeamAbbreviation, TEAM_COLOR_PRESETS } from './teamUtils'

const props = defineProps({
  modelValue: { type: Object, required: true },
  descriptionPlaceholder: { type: String, default: '' }
})
const emit = defineEmits(['update:modelValue'])
const { t } = useI18n()

function update(field, value) {
  emit('update:modelValue', { ...props.modelValue, [field]: value })
}

function onAbbreviation(event) {
  const value = normalizeTeamAbbreviation(event.target.value)
  // Keep the input in sync even when the normalised value did not change.
  event.target.value = value
  update('abbreviation', value)
}

function isPreset(color) {
  return String(props.modelValue.avatar_color || '').toLowerCase() === color
}

const isCustomColor = () => !TEAM_COLOR_PRESETS.some(isPreset)
</script>

<template>
  <div class="tform">
    <FormField
      v-slot="{ id, describedBy }"
      class="tform__name"
      :label="t('fields.name')"
      :hint="t('teamsPage.form.nameHint')"
      required
      :count="modelValue.name.length"
      :max="80"
    >
      <input
        :id="id"
        class="ui-input"
        type="text"
        maxlength="80"
        required
        autocomplete="off"
        :aria-describedby="describedBy"
        :value="modelValue.name"
        @input="update('name', $event.target.value)"
      />
    </FormField>

    <FormField
      v-slot="{ id, describedBy }"
      class="tform__abbr"
      :label="t('teams.abbreviation')"
      :hint="t('teamsPage.form.abbreviationHint')"
      required
      :count="modelValue.abbreviation.length"
      :max="3"
    >
      <input
        :id="id"
        class="ui-input tform__abbr-input"
        type="text"
        maxlength="3"
        minlength="3"
        pattern="[A-Za-z]{3}"
        required
        autocomplete="off"
        autocapitalize="characters"
        spellcheck="false"
        :placeholder="t('teams.abbreviationPlaceholder')"
        :aria-describedby="describedBy"
        :value="modelValue.abbreviation"
        @input="onAbbreviation"
      />
    </FormField>

    <FormField v-slot="{ id, describedBy }" class="tform__color" :label="t('teams.avatarColor')" :hint="t('teamsPage.form.colorHint')">
      <div class="tform__swatches" role="group" :aria-label="t('teams.avatarColor')" :aria-describedby="describedBy">
        <button
          v-for="color in TEAM_COLOR_PRESETS"
          :key="color"
          class="tform__swatch"
          :class="{ 'is-active': isPreset(color) }"
          type="button"
          :style="{ '--swatch': color }"
          :aria-pressed="isPreset(color)"
          :aria-label="color"
          :title="color"
          @click="update('avatar_color', color)"
        >
          <Check v-if="isPreset(color)" :size="14" />
        </button>
        <label class="tform__custom" :class="{ 'is-active': isCustomColor() }" :title="t('teamsPage.form.customColor')">
          <input
            :id="id"
            type="color"
            :value="modelValue.avatar_color"
            :aria-label="t('teamsPage.form.customColor')"
            @input="update('avatar_color', $event.target.value)"
          />
          <Pipette :size="14" />
        </label>
        <code class="tform__hex ui-num">{{ String(modelValue.avatar_color || '').toUpperCase() }}</code>
      </div>
    </FormField>

    <FormField
      v-slot="{ id, describedBy }"
      class="tform__desc"
      :label="t('fields.description')"
      :hint="t('teamsPage.form.descriptionHint')"
      :optional-label="t('teamsPage.form.optional')"
      :count="modelValue.description.length"
      :max="1000"
    >
      <textarea
        :id="id"
        class="ui-textarea"
        maxlength="1000"
        rows="4"
        :placeholder="descriptionPlaceholder"
        :aria-describedby="describedBy"
        :value="modelValue.description"
        @input="update('description', $event.target.value)"
      ></textarea>
    </FormField>
  </div>
</template>

<style scoped>
.tform {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(130px, 170px);
  gap: 18px 16px;
}

.tform__color,
.tform__desc {
  grid-column: 1 / -1;
}

.tform__abbr-input {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.24em;
  text-transform: uppercase;
}

.tform__abbr-input::placeholder {
  letter-spacing: 0.24em;
  opacity: 0.6;
}

.tform__swatches {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.tform__swatch,
.tform__custom {
  position: relative;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  cursor: pointer;
  transition: transform var(--dur-3) var(--ease-spring), box-shadow var(--dur-2) var(--ease-out);
  -webkit-tap-highlight-color: transparent;
}

.tform__swatch {
  background: var(--swatch);
  color: #fff;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.18), 0 4px 10px -4px var(--swatch);
}

.tform__swatch:hover,
.tform__custom:hover {
  transform: scale(1.1);
}

.tform__swatch.is-active,
.tform__custom.is-active {
  box-shadow: 0 0 0 2px var(--c-bg), 0 0 0 4px var(--bm-blue-bright);
  transform: scale(1.06);
}

.tform__swatch svg {
  filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.5));
}

.tform__custom {
  background: conic-gradient(from 0deg, #ff3b4e, #ffb020, #22c55e, #4fd8ea, #1652d8, #7c3aed, #ff3b4e);
  color: #fff;
}

.tform__custom svg {
  position: relative;
  filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.6));
  pointer-events: none;
}

.tform__custom input {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  padding: 0;
  border: 0;
  opacity: 0;
  cursor: pointer;
}

.tform__custom:focus-within {
  outline: 2px solid var(--bm-blue-bright);
  outline-offset: 3px;
}

.tform__hex {
  margin-left: 4px;
  padding: 6px 10px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-pill);
  background: var(--c-sunken);
  color: var(--c-text-2);
  font-size: 12px;
}

@media (max-width: 560px) {
  .tform {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (prefers-reduced-motion: reduce) {
  .tform__swatch,
  .tform__custom {
    transition: none;
  }
}
</style>
