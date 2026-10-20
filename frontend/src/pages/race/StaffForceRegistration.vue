<script setup>
// Admin: register a pilot on their behalf (also after registration closes,
// until the race starts).
import { useI18n } from 'vue-i18n'
import { Search, UserPlus } from 'lucide-vue-next'
import FormField from '../../ui/FormField.vue'
import { formatPilotNumber } from '../../pilotDisplay'
import { personName } from './raceFormat'

defineProps({
  candidates: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  pending: { type: Boolean, default: false },
  allowedCars: { type: Array, default: () => [] }
})
const emit = defineEmits(['submit', 'pilot-change'])
const search = defineModel('search', { type: String, default: '' })
const pilotId = defineModel('pilotId', { type: String, default: '' })
const number = defineModel('number', { type: String, default: '' })
const car = defineModel('car', { type: String, default: '' })
const { t } = useI18n()

function pilotLabel(pilot) {
  return personName(pilot, `${t('roles.pilot')} ${pilot.user_id}`)
}
</script>

<template>
  <form class="staff-block" @submit.prevent="emit('submit')">
    <div class="staff-block__head">
      <strong>{{ t('raceDetails.forceRegistrationTitle') }}</strong>
      <span>{{ t('raceDetails.forceRegistrationHint') }}</span>
    </div>

    <div class="force__search">
      <FormField v-slot="{ id, describedBy }" :label="t('raceDetails.forceRegistrationSearch')" :icon="Search">
        <input
          :id="id"
          v-model="search"
          class="ui-input"
          type="search"
          :placeholder="t('raceDetails.forceRegistrationSearch')"
          :disabled="loading || pending"
          :aria-describedby="describedBy"
          @keydown.enter.prevent
        />
      </FormField>
      <span class="ui-chip ui-num">{{ loading ? t('common.loading') : candidates.length }}</span>
    </div>

    <div class="force__fields">
      <FormField v-slot="{ id }" :label="t('raceDetails.forceRegistrationPilot')" required>
        <select :id="id" v-model="pilotId" class="ui-select" :disabled="loading || pending" required @change="emit('pilot-change')">
          <option value="" disabled>{{ loading ? t('common.loading') : t('raceDetails.forceRegistrationPilotRequired') }}</option>
          <option v-for="pilot in candidates" :key="pilot.id" :value="String(pilot.id)">
            {{ pilotLabel(pilot) }} · #{{ formatPilotNumber(pilot.pilot_number) }}
          </option>
        </select>
      </FormField>
      <FormField v-slot="{ id }" :label="t('common.car')">
        <select :id="id" v-model="car" class="ui-select" :disabled="pending">
          <option v-if="!allowedCars.length" value="">TBD</option>
          <option v-for="item in allowedCars" :key="item" :value="item">{{ item }}</option>
        </select>
      </FormField>
      <FormField v-slot="{ id }" :label="t('fields.pilotNumber')" :hint="t('racePage.staff.forceNumberHint')" required>
        <input :id="id" v-model="number" class="ui-input force__number" inputmode="numeric" pattern="[0-9]{3}" minlength="3" maxlength="3" placeholder="001" required :disabled="pending" />
      </FormField>
    </div>

    <div class="staff-actions">
      <button class="ui-btn ui-btn--primary" type="submit" :disabled="pending || loading || !pilotId">
        <UserPlus :size="16" />{{ t('raceDetails.forceRegistrationSubmit') }}
      </button>
    </div>
  </form>
</template>

<style scoped>
.force__search {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: 10px;
}

.force__search .ui-chip {
  min-height: 48px;
  padding: 0 14px;
}

.force__fields {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr) minmax(120px, 0.6fr);
  align-items: start;
  gap: 12px;
}

.force__number {
  font-family: var(--font-mono);
  letter-spacing: 0.2em;
}

@media (max-width: 760px) {
  .force__fields {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
