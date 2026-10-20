<script setup>
// Fields of one championship stage. Used when drafting stages for a new
// championship, adding a stage and editing one. Writes produce a new stage
// object through v-model.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import FormField from '../../ui/FormField.vue'
import SwitchToggle from '../../ui/SwitchToggle.vue'
import { useFieldModels } from './fieldModels'
import { SCORING_OPTIONS } from './helpers'

const props = defineProps({
  game: { type: String, default: 'ACC' },
  /** Track/class lists for the game (assetConfigForGame). */
  assets: { type: Object, default: () => ({ tracks: [], classes: [] }) },
  nameRequired: { type: Boolean, default: false },
  namePlaceholder: { type: String, default: '' }
})
const stage = defineModel({ type: Object, required: true })

const { t } = useI18n()
const isLmu = computed(() => props.game === 'LMU')
const fields = useFieldModels(stage, [
  'name', 'datetime_start', 'lmu_results_at', 'server_link', 'track', 'car_class',
  'has_qualification', 'is_team_event', 'scoring_system', 'pole_bonus_enabled'
])
</script>

<template>
  <div class="stage-fields">
    <div class="stage-fields__grid">
      <FormField :label="t('fields.name')" :required="nameRequired" :optional-label="nameRequired ? '' : t('champPage.form.optional')">
        <template #default="{ id }">
          <input :id="id" v-model="fields.name" class="ui-input" maxlength="100" :required="nameRequired" :placeholder="namePlaceholder" />
        </template>
      </FormField>

      <FormField :label="t('fields.date')" required>
        <template #default="{ id }">
          <input :id="id" v-model="fields.datetime_start" class="ui-input" type="datetime-local" required />
        </template>
      </FormField>

      <FormField v-if="isLmu" :label="t('fields.lmuResultsAt')" required>
        <template #default="{ id }">
          <input :id="id" v-model="fields.lmu_results_at" class="ui-input" type="datetime-local" required />
        </template>
      </FormField>

      <FormField :label="t('fields.track')" :required="isLmu">
        <template #default="{ id }">
          <select :id="id" v-model="fields.track" class="ui-select" :required="isLmu">
            <option value="">TBA</option>
            <option v-for="track in assets.tracks || []" :key="track" :value="track">{{ track }}</option>
          </select>
        </template>
      </FormField>

      <FormField v-if="isLmu" :label="t('fields.class')" required>
        <template #default="{ id }">
          <select :id="id" v-model="fields.car_class" class="ui-select" required>
            <option value="">TBA</option>
            <option v-for="item in assets.classes || []" :key="item.name" :value="item.name">{{ item.name }}</option>
          </select>
        </template>
      </FormField>

      <FormField :label="t('fields.linkUrl')" :optional-label="t('champPage.form.optional')">
        <template #default="{ id }">
          <input :id="id" v-model="fields.server_link" class="ui-input" maxlength="255" />
        </template>
      </FormField>

      <FormField :label="t('championships.stageScoring')">
        <template #default="{ id }">
          <select :id="id" v-model="fields.scoring_system" class="ui-select">
            <option v-for="option in SCORING_OPTIONS" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </template>
      </FormField>
    </div>

    <div class="stage-fields__switches">
      <SwitchToggle v-if="!isLmu" v-model="fields.has_qualification" :label="t('fields.qualification')" />
      <SwitchToggle v-if="!isLmu" v-model="fields.is_team_event" :label="t('champPage.teamStage')" />
      <SwitchToggle v-model="fields.pole_bonus_enabled" :label="t('championships.poleBonus')" />
    </div>
  </div>
</template>

<style scoped>
.stage-fields {
  display: grid;
  gap: 16px;
}

.stage-fields__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 14px;
}

.stage-fields__switches {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 24px;
}
</style>
