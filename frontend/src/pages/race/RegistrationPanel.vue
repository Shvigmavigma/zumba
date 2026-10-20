<script setup>
// Registration for solo and team races. Every field explains itself; the race
// number is checked as you type (format, 000, already taken in this race).
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Car, CheckCircle2, ChevronDown, ChevronUp, Hash, Info, Send, UserX } from 'lucide-vue-next'
import PilotRoles from '../../components/PilotRoles.vue'
import UserAvatar from '../../components/UserAvatar.vue'
import FormField from '../../ui/FormField.vue'
import SwitchToggle from '../../ui/SwitchToggle.vue'
import WarningPulse from '../../ui/fx/WarningPulse.vue'
import { formatPilotNumber } from '../../pilotDisplay'
import { state } from '../../store'
import { personName, pilotNumberIssue } from './raceFormat'
import { useRaceMods } from './useRaceMods'

const props = defineProps({
  race: { type: Object, required: true },
  isChampionshipStage: { type: Boolean, default: false },
  registered: { type: Boolean, default: false },
  myEntry: { type: Object, default: null },
  teamRegistered: { type: Boolean, default: false },
  myTeamRegistration: { type: Object, default: null },
  canManageTeam: { type: Boolean, default: false },
  myTeam: { type: Object, default: null },
  teamDriverIds: { type: Array, default: () => [] },
  participants: { type: Array, default: () => [] },
  teamRegistrations: { type: Array, default: () => [] },
  full: { type: Boolean, default: false },
  busy: { type: Boolean, default: false }
})
const emit = defineEmits(['register', 'unregister', 'toggle-driver', 'move-driver'])
const car = defineModel('car', { type: String, default: '' })
const pilotNumber = defineModel('pilotNumber', { type: String, default: '' })
const teamRaceNumber = defineModel('teamRaceNumber', { type: String, default: '' })
const { t } = useI18n()
const { mods, seen: modsSeen, showMods } = useRaceMods(() => props.race)

const cars = computed(() => props.race.allowed_cars || [])
const isTeam = computed(() => Boolean(props.race.is_team_event))
const isEntered = computed(() => (isTeam.value ? props.teamRegistered : props.registered))
const selectedDrivers = computed(() => {
  const members = new Map((props.myTeam?.members || []).map((member) => [member.id, member]))
  return props.teamDriverIds.map((id) => members.get(id)).filter(Boolean)
})

function memberName(member) {
  return personName({ ...member, user_id: member.id }, `${t('roles.pilot')} ${member.id}`)
}

function driverName(driver) {
  return personName(driver, `${t('roles.pilot')} ${driver.user_id}`)
}

function isSelected(id) {
  return props.teamDriverIds.includes(Number(id))
}

function numberError(value, takenBy) {
  const issue = pilotNumberIssue(value)
  if (issue) return t('raceDetails.invalidRacePilotNumber')
  const raw = String(value || '').trim()
  if (raw.length !== 3) return ''
  const owner = takenBy(Number(raw))
  return owner ? t('racePage.form.numberTaken', { number: raw, name: owner }) : ''
}

const soloNumberError = computed(() => numberError(pilotNumber.value, (number) => {
  const item = props.participants.find((pilot) => Number(pilot.pilot_number) === number && pilot.user_id !== state.user?.id)
  return item ? personName(item, `#${formatPilotNumber(number)}`) : ''
}))

const teamNumberError = computed(() => numberError(teamRaceNumber.value, (number) => {
  const item = props.teamRegistrations.find((team) => Number(team.race_number) === number && team.team_id !== state.user?.team_id)
  return item?.team_name || ''
}))

const title = computed(() => {
  if (isTeam.value && props.teamRegistered) return t('racePage.form.teamEntered')
  if (props.registered) return props.isChampionshipStage ? t('raceDetails.championshipStageRegistered') : t('racePage.form.entered')
  return props.isChampionshipStage ? t('racePage.form.stageTitle') : t('racePage.form.title')
})
</script>

<template>
  <section id="race-registration" class="reg ui-card" :class="{ 'is-entered': isEntered, 'ui-beam': !isEntered && !full }" aria-labelledby="race-reg-title">
    <header class="ui-card__head">
      <div class="ui-card__title">
        <p class="ui-eyebrow ui-eyebrow--accent">{{ t('racePage.form.eyebrow') }}</p>
        <h2 id="race-reg-title">{{ title }}</h2>
      </div>
      <span v-if="isEntered" class="ui-chip ui-chip--green"><span class="ui-dot ui-dot--green"></span>{{ t('racePage.form.confirmed') }}</span>
    </header>

    <Transition name="race-swap" mode="out-in">
      <!-- Team entry already submitted -->
      <div v-if="isTeam && teamRegistered" key="team-entered" class="reg__ticket">
        <span class="reg__plate ui-num">{{ formatPilotNumber(myTeamRegistration.race_number) }}</span>
        <div class="reg__ticket-main">
          <strong>{{ myTeamRegistration.team_name || t('raceDetails.teams') }}</strong>
          <span><Car :size="14" />{{ myTeamRegistration.car_model }}</span>
          <ol class="reg__chain">
            <li v-for="(driver, index) in myTeamRegistration.drivers || []" :key="driver.user_id || index">
              <b class="ui-num">{{ index + 1 }}</b>{{ driverName(driver) }}
            </li>
          </ol>
        </div>
        <button v-if="canManageTeam" class="ui-btn ui-btn--danger" type="button" :disabled="busy" @click="emit('unregister')">
          <UserX :size="16" />{{ t('common.unregister') }}
        </button>
      </div>

      <!-- Team entry form -->
      <form v-else-if="isTeam" key="team-form" class="reg__form" @submit.prevent="emit('register')">
        <p v-if="!canManageTeam" class="ui-alert ui-alert--info"><Info :size="18" />{{ t('racePage.form.ownerOnly') }}</p>
        <template v-else>
          <p class="reg__lead">{{ t('racePage.form.teamLead') }}</p>
          <div class="reg__row">
            <FormField v-slot="{ id, describedBy }" :label="t('common.car')" :hint="t('racePage.form.carHint')" :icon="Car">
              <select :id="id" v-model="car" class="ui-select" :aria-describedby="describedBy">
                <option v-if="!cars.length" value="">TBD</option>
                <option v-for="item in cars" :key="item">{{ item }}</option>
              </select>
            </FormField>
            <FormField v-slot="{ id, describedBy, invalid }" :label="t('racePage.form.teamNumber')" :hint="t('racePage.form.teamNumberHint')" :error="teamNumberError" :icon="Hash" required>
              <input
                :id="id"
                v-model="teamRaceNumber"
                class="ui-input reg__number"
                inputmode="numeric"
                pattern="[0-9]{3}"
                minlength="3"
                maxlength="3"
                placeholder="001"
                required
                :aria-describedby="describedBy"
                :aria-invalid="invalid"
              />
            </FormField>
          </div>

          <div class="reg__drivers">
            <div class="reg__drivers-head">
              <span class="ui-label">{{ t('racePage.form.drivers') }}</span>
              <span class="ui-faint">{{ t('racePage.form.driversHint') }}</span>
            </div>
            <TransitionGroup tag="ul" name="ui-list" class="reg__members">
              <li v-for="member in myTeam?.members || []" :key="member.id" class="reg__member" :class="{ 'is-on': isSelected(member.id) }">
                <span class="reg__order ui-num">{{ teamDriverIds.indexOf(member.id) + 1 || '–' }}</span>
                <UserAvatar mini :src="member.avatar_url" :color="member.avatar_color" :label="memberName(member)" />
                <span class="reg__member-name">{{ memberName(member) }}<PilotRoles :roles="member.pilot_roles" /></span>
                <SwitchToggle :model-value="isSelected(member.id)" :label="isSelected(member.id) ? t('racePage.form.inEntry') : t('racePage.form.notInEntry')" @update:model-value="emit('toggle-driver', member.id)" />
                <span class="reg__move">
                  <button class="ui-btn ui-btn--ghost ui-btn--icon ui-btn--sm" type="button" :disabled="!isSelected(member.id)" :aria-label="t('racePage.form.moveUp')" @click="emit('move-driver', member.id, -1)"><ChevronUp :size="16" /></button>
                  <button class="ui-btn ui-btn--ghost ui-btn--icon ui-btn--sm" type="button" :disabled="!isSelected(member.id)" :aria-label="t('racePage.form.moveDown')" @click="emit('move-driver', member.id, 1)"><ChevronDown :size="16" /></button>
                </span>
              </li>
            </TransitionGroup>
            <ol v-if="selectedDrivers.length" class="reg__chain reg__chain--preview" :aria-label="t('racePage.form.order')">
              <li v-for="(member, index) in selectedDrivers" :key="`selected-team-driver-${member.id}`">
                <b class="ui-num">{{ index + 1 }}</b>{{ memberName(member) }} <span class="ui-faint ui-num">#{{ formatPilotNumber(member.pilot_number) }}</span>
              </li>
            </ol>
          </div>

          <p v-if="isChampionshipStage" class="reg__lead">{{ t('racePage.form.teamStageNote') }}</p>
          <p v-if="full" class="ui-alert ui-alert--info"><Info :size="18" />{{ t('racePage.form.fullNote') }}</p>
          <p v-if="mods.length" class="reg__mods">
            <WarningPulse :size="17" :calm="modsSeen" />{{ t('racePage.form.modsReminder') }}
            <button class="ui-link" type="button" @click="showMods">{{ t('racePage.form.modsOpen') }}</button>
          </p>
          <div class="reg__submit">
            <button v-magnet v-spark class="ui-btn ui-btn--primary ui-btn--lg" type="submit" :disabled="busy">
              <Send :size="17" />{{ t('common.register') }}
            </button>
          </div>
        </template>
      </form>

      <!-- Solo entry already submitted -->
      <div v-else-if="registered" key="solo-entered" class="reg__ticket">
        <span class="reg__plate ui-num">{{ myEntry ? formatPilotNumber(myEntry.pilot_number) : '—' }}</span>
        <div class="reg__ticket-main">
          <strong><CheckCircle2 :size="16" />{{ isChampionshipStage ? t('raceDetails.championshipStageRegistered') : t('raceDetails.alreadyRegistered') }}</strong>
          <span v-if="myEntry?.car_model"><Car :size="14" />{{ myEntry.car_model }}</span>
          <span class="ui-faint">{{ t('racePage.form.enteredHint') }}</span>
        </div>
        <button class="ui-btn ui-btn--danger" type="button" :disabled="busy" @click="emit('unregister')">
          <UserX :size="16" />{{ t('common.unregister') }}
        </button>
      </div>

      <!-- Solo entry form -->
      <form v-else key="solo-form" class="reg__form" @submit.prevent="emit('register')">
        <p class="reg__lead">{{ isChampionshipStage ? t('raceDetails.championshipStageRegistrationHint') : t('racePage.form.lead') }}</p>
        <div class="reg__row" :class="{ 'is-single': isChampionshipStage }">
          <FormField v-slot="{ id, describedBy }" :label="t('common.car')" :hint="t('racePage.form.carHint')" :icon="Car">
            <select :id="id" v-model="car" class="ui-select" :aria-describedby="describedBy">
              <option v-if="!cars.length" value="">TBD</option>
              <option v-for="item in cars" :key="item">{{ item }}</option>
            </select>
          </FormField>
          <FormField
            v-if="!isChampionshipStage"
            v-slot="{ id, describedBy, invalid }"
            :label="t('fields.pilotNumber')"
            :hint="t('racePage.form.numberHint')"
            :error="soloNumberError"
            :icon="Hash"
            required
          >
            <input
              :id="id"
              v-model="pilotNumber"
              class="ui-input reg__number"
              inputmode="numeric"
              pattern="[0-9]{3}"
              minlength="3"
              maxlength="3"
              placeholder="001"
              required
              :aria-describedby="describedBy"
              :aria-invalid="invalid"
            />
          </FormField>
        </div>
        <p v-if="full" class="ui-alert ui-alert--info"><Info :size="18" />{{ t('racePage.form.fullNote') }}</p>
        <p v-if="mods.length" class="reg__mods">
          <WarningPulse :size="17" :calm="modsSeen" />{{ t('racePage.form.modsReminder') }}
          <button class="ui-link" type="button" @click="showMods">{{ t('racePage.form.modsOpen') }}</button>
        </p>
        <div class="reg__submit">
          <div v-if="!isChampionshipStage" class="reg__preview" aria-hidden="true">
            <span class="reg__plate reg__plate--sm ui-num" :class="{ 'is-empty': !pilotNumber }">{{ pilotNumber || '000' }}</span>
            <span class="reg__preview-car">{{ car || 'TBD' }}</span>
          </div>
          <button v-magnet v-spark class="ui-btn ui-btn--primary ui-btn--lg" type="submit" :disabled="busy">
            <Send :size="17" />{{ isChampionshipStage ? t('raceDetails.championshipStageRegister') : t('common.register') }}
          </button>
        </div>
      </form>
    </Transition>
  </section>
</template>

<style scoped>
.reg {
  scroll-margin-top: calc(var(--header-h) + 16px);
}

.reg.is-entered {
  border-color: color-mix(in srgb, var(--bm-green) 32%, var(--c-line));
}

.reg__form {
  display: grid;
  gap: 18px;
}

.race-swap-enter-active,
.race-swap-leave-active {
  transition: opacity var(--dur-2) var(--ease-out), transform var(--dur-3) var(--ease-ios), filter var(--dur-2) var(--ease-out);
}

.race-swap-enter-from {
  opacity: 0;
  filter: blur(6px);
  transform: translateY(10px) scale(0.99);
}

.race-swap-leave-to {
  opacity: 0;
  filter: blur(4px);
  transform: translateY(-6px);
}

@media (prefers-reduced-motion: reduce) {
  .race-swap-enter-active,
  .race-swap-leave-active {
    transition: none;
  }
}

.reg__lead {
  margin: 0;
  color: var(--c-text-2);
  font-size: 14px;
  line-height: 1.55;
}

.reg__row {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
  gap: 16px;
}

.reg__row.is-single {
  grid-template-columns: minmax(0, 1fr);
}

.reg__number {
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.24em;
}

/* A race with mods: say so right where the pilot signs up. */
.reg__mods {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 10px;
  margin: 0;
  padding: 10px 14px;
  border: 1px solid color-mix(in srgb, var(--bm-red) 40%, transparent);
  border-radius: var(--r-md);
  background: color-mix(in srgb, var(--bm-red) 8%, transparent);
  color: var(--c-text);
  font-size: 13.5px;
}

.reg__mods .ui-link {
  padding: 0;
  border: 0;
  background: none;
  cursor: pointer;
  font: inherit;
  font-weight: 600;
}

.reg__submit {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 14px;
}

.reg__preview {
  display: flex;
  flex: 1 1 auto;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.reg__preview-car {
  overflow: hidden;
  color: var(--c-text-2);
  font-size: 13.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Number board, like the door plate on a GT car. */
.reg__plate {
  display: inline-grid;
  place-items: center;
  min-width: 86px;
  height: 64px;
  padding: 0 14px;
  border: 2px solid #0a0f1a;
  border-radius: 14px;
  background: linear-gradient(180deg, #fff, #e8edf6);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--bm-blue) 70%, transparent), 0 14px 30px color-mix(in srgb, var(--bm-blue) 35%, transparent);
  color: #070c18;
  font-size: 30px;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.reg__plate--sm {
  min-width: 64px;
  height: 44px;
  border-radius: 10px;
  font-size: 20px;
  transition: transform var(--dur-3) var(--ease-spring);
}

.reg__plate.is-empty {
  color: #9aa6ba;
}

.reg__ticket {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 18px;
  padding: 16px;
  border: 1px solid color-mix(in srgb, var(--bm-green) 28%, transparent);
  border-radius: var(--r-lg);
  background: linear-gradient(120deg, color-mix(in srgb, var(--bm-green) 10%, transparent), transparent 60%);
}

.reg__ticket-main {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.reg__ticket-main strong {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--c-text);
  font-size: 16px;
}

.reg__ticket-main strong svg {
  color: var(--bm-green);
}

.reg__ticket-main > span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--c-text-2);
  font-size: 13.5px;
}

.reg__chain {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 2px 0 0;
  padding: 0;
  list-style: none;
}

.reg__chain li {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 4px 10px 4px 4px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-pill);
  background: var(--c-sunken);
  font-size: 13px;
}

.reg__chain b {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--bm-blue);
  color: #fff;
  font-size: 11px;
}

.reg__drivers {
  display: grid;
  gap: 12px;
}

.reg__drivers-head {
  display: grid;
  gap: 4px;
}

.reg__drivers-head .ui-faint {
  font-size: 12.5px;
}

.reg__members {
  position: relative;
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.reg__member {
  display: grid;
  grid-template-columns: 26px auto minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 12px;
  padding: 8px 10px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  background: var(--c-sunken);
  transition: border-color var(--dur-2), background-color var(--dur-2);
}

.reg__member.is-on {
  border-color: var(--c-blue-line);
  background: var(--c-blue-soft);
}

.reg__order {
  color: var(--c-text-3);
  font-size: 13px;
  font-weight: 700;
  text-align: center;
}

.reg__member.is-on .reg__order {
  color: var(--c-accent-text);
}

.reg__member-name {
  min-width: 0;
  overflow: hidden;
  font-size: 14px;
  font-weight: 600;
  text-overflow: ellipsis;
}

.reg__move {
  display: inline-flex;
  gap: 2px;
}

@media (max-width: 760px) {
  .reg__row {
    grid-template-columns: minmax(0, 1fr);
  }

  .reg__ticket {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .reg__ticket > .ui-btn {
    grid-column: 1 / -1;
  }

  .reg__member {
    grid-template-columns: 22px auto minmax(0, 1fr) auto;
  }

  .reg__member :deep(.switch__text) {
    display: none;
  }

  .reg__move {
    grid-column: 3 / -1;
    justify-self: end;
  }

  .reg__submit .ui-btn {
    flex: 1 1 100%;
  }
}
</style>
