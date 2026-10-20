<script setup>
// Tools for the team owner (and league moderators): join requests, the team
// card editor with avatar upload, and ownership / deletion. Grouped in tabs so
// each job is one clear screen.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Check, ImageUp, Inbox, Maximize2, PenLine, Save, ShieldAlert, Trash2, Upload, UserCheck, XCircle } from 'lucide-vue-next'
import TeamAvatar from '../../components/TeamAvatar.vue'
import { formatPilotNumber, formatRating, pilotName, ratingForGame } from '../../pilotDisplay'
import EmptyState from '../../ui/EmptyState.vue'
import FormField from '../../ui/FormField.vue'
import SegmentedControl from '../../ui/SegmentedControl.vue'
import MemberRow from './MemberRow.vue'
import TeamCard from './TeamCard.vue'
import TeamFormFields from './TeamFormFields.vue'

const props = defineProps({
  team: { type: Object, required: true },
  candidates: { type: Array, default: () => [] },
  game: { type: String, default: 'ACC' },
  editSaving: { type: Boolean, default: false },
  transferSaving: { type: Boolean, default: false },
  deleteSaving: { type: Boolean, default: false },
  avatarSaving: { type: Boolean, default: false },
  avatarFile: { type: Object, default: null },
  busyApplications: { type: Object, default: () => ({}) }
})
const form = defineModel('form', { type: Object, required: true })
const transferOwnerId = defineModel('transferOwnerId', { type: [String, Number], default: '' })
const emit = defineEmits(['save', 'select-file', 'upload', 'transfer', 'delete', 'approve', 'reject', 'open-avatar'])
const { t } = useI18n()

const applications = computed(() => props.team.applications || [])
const tab = ref(applications.value.length ? 'requests' : 'card')
const fileInput = ref(null)

const tabs = computed(() => [
  { value: 'requests', label: t('teamsPage.manage.tabRequests'), icon: Inbox, count: applications.value.length },
  { value: 'card', label: t('teamsPage.manage.tabCard'), icon: PenLine },
  { value: 'ownership', label: t('teamsPage.manage.tabOwnership'), icon: UserCheck }
])

/** How the edited card will look in the team grid for everyone else. */
const preview = computed(() => ({
  ...props.team,
  ...form.value,
  is_member: false,
  is_owner: false,
  my_application_status: null,
  pending_application_count: 0
}))

watch(() => props.team.id, () => {
  tab.value = applications.value.length ? 'requests' : 'card'
})

watch(() => props.avatarFile, (file) => {
  if (!file && fileInput.value) fileInput.value.value = ''
})
</script>

<template>
  <section class="tools ui-card" aria-labelledby="team-tools-title">
    <header class="tools__head">
      <div class="tools__title">
        <p class="ui-eyebrow ui-eyebrow--accent">{{ t('teamsPage.manage.eyebrow') }}</p>
        <h3 id="team-tools-title" class="ui-title tools__h">{{ t('teams.ownerToolsTitle') }}</h3>
        <p class="tools__hint">{{ t('teamsPage.manage.hint') }}</p>
      </div>
      <SegmentedControl v-model="tab" block size="sm" :options="tabs" :aria-label="t('teams.ownerToolsTitle')" />
    </header>

    <Transition name="tools-tab" mode="out-in">
      <!-- Join requests -->
      <div v-if="tab === 'requests'" key="requests" class="tools__pane" role="tabpanel">
        <p class="tools__lead">{{ t('teamsPage.manage.requestsHint') }}</p>
        <TransitionGroup v-if="applications.length" tag="ul" name="ui-list" class="tools__list">
          <li v-for="application in applications" :key="application.id">
            <MemberRow :member="application.user" :game="game" :to="`/pilots/${application.user.id}`">
              <template #actions>
                <button
                  class="ui-btn ui-btn--icon ui-btn--sm tools__approve"
                  type="button"
                  :title="t('teams.approveApplication')"
                  :aria-label="`${t('teams.approveApplication')}: ${pilotName(application.user, application.user.login)}`"
                  :disabled="busyApplications[application.id]"
                  @click="emit('approve', application)"
                >
                  <Check :size="16" />
                </button>
                <button
                  class="ui-btn ui-btn--icon ui-btn--sm ui-btn--danger"
                  type="button"
                  :title="t('teams.rejectApplication')"
                  :aria-label="`${t('teams.rejectApplication')}: ${pilotName(application.user, application.user.login)}`"
                  :disabled="busyApplications[application.id]"
                  @click="emit('reject', application)"
                >
                  <XCircle :size="16" />
                </button>
              </template>
            </MemberRow>
          </li>
        </TransitionGroup>
        <EmptyState v-else compact :icon="Inbox" :title="t('teams.noApplications')" :text="t('teamsPage.manage.requestsEmpty')" />
      </div>

      <!-- Team card + avatar -->
      <div v-else-if="tab === 'card'" key="card" class="tools__pane" role="tabpanel">
        <form class="tools__form" @submit.prevent="emit('save')">
          <div class="tools__preview">
            <p class="ui-eyebrow">{{ t('teamsPage.manage.preview') }}</p>
            <TeamCard preview :team="preview" />
          </div>
          <TeamFormFields v-model="form" :description-placeholder="t('teams.descriptionPlaceholder')" />
          <div class="tools__submit">
            <button class="ui-btn ui-btn--primary" type="submit" :disabled="editSaving">
              <Save :size="16" />{{ editSaving ? t('common.saving') : t('common.save') }}
            </button>
          </div>
        </form>

        <div class="tools__avatar ui-sunken">
          <button class="tools__avatar-open" type="button" :title="t('avatar.open')" :aria-label="t('avatar.open')" @click="emit('open-avatar')">
            <TeamAvatar :src="team.avatar_url" :color="form.avatar_color" :label="form.name || team.name" />
            <span aria-hidden="true"><Maximize2 :size="12" /></span>
          </button>
          <div class="tools__avatar-main">
            <strong>{{ t('avatar.teamTitle') }}</strong>
            <p>{{ t('avatar.teamHint') }}</p>
            <div class="tools__upload">
              <label class="ui-btn ui-btn--outline ui-btn--sm tools__file">
                <ImageUp :size="15" />{{ t('teamsPage.manage.pickFile') }}
                <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp,image/gif" @change="emit('select-file', $event)" />
              </label>
              <span class="tools__filename" :class="{ 'is-empty': !avatarFile }">{{ avatarFile?.name || t('teamsPage.manage.noFile') }}</span>
              <button class="ui-btn ui-btn--primary ui-btn--sm" type="button" :disabled="avatarSaving || !avatarFile" @click="emit('upload')">
                <Upload :size="15" />{{ avatarSaving ? t('common.uploading') : t('common.upload') }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Ownership & deletion -->
      <div v-else key="ownership" class="tools__pane" role="tabpanel">
        <p class="ui-alert ui-alert--info"><ShieldAlert :size="18" /><span>{{ t('teams.ownerLeaveHint') }}</span></p>

        <form class="tools__transfer" @submit.prevent="emit('transfer')">
          <FormField v-slot="{ id, describedBy }" :label="t('teams.newOwner')" :hint="candidates.length ? t('teamsPage.manage.transferHint') : t('teams.noTransferCandidates')" required>
            <select :id="id" v-model="transferOwnerId" class="ui-select" :aria-describedby="describedBy" :disabled="!candidates.length" required>
              <option value="">{{ t('teams.chooseMember') }}</option>
              <option v-for="member in candidates" :key="member.id" :value="member.id">
                {{ pilotName(member, member.nickname || member.login) }} · #{{ formatPilotNumber(member.pilot_number) }} · RER {{ formatRating(ratingForGame(member, game)) }}
              </option>
            </select>
          </FormField>
          <button class="ui-btn ui-btn--outline" type="submit" :disabled="transferSaving || !transferOwnerId">
            <UserCheck :size="16" />{{ t('teams.transferOwner') }}
          </button>
        </form>

        <div class="tools__danger">
          <div>
            <strong>{{ t('teamsPage.manage.dangerTitle') }}</strong>
            <p>{{ t('teamsPage.manage.dangerText') }}</p>
          </div>
          <button class="ui-btn ui-btn--danger" type="button" :disabled="deleteSaving" @click="emit('delete')">
            <Trash2 :size="16" />{{ t('teams.deleteTeam') }}
          </button>
        </div>
      </div>
    </Transition>
  </section>
</template>

<style scoped>
.tools {
  gap: 20px;
}

.tools__head {
  display: grid;
  gap: 16px;
}

.tools__title {
  display: grid;
  gap: 8px;
}

.tools__h {
  font-size: 20px;
}

.tools__hint,
.tools__lead {
  margin: 0;
  color: var(--c-text-3);
  font-size: 13px;
  line-height: 1.5;
}

.tools__pane {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.tools__list {
  position: relative;
  display: grid;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.tools__list > li.ui-list-leave-active {
  width: 100%;
}

.tools__approve {
  --btn-bg: color-mix(in srgb, var(--bm-green) 14%, transparent);
  --btn-fg: color-mix(in srgb, var(--bm-green) 85%, var(--c-text));
  --btn-line: color-mix(in srgb, var(--bm-green) 36%, transparent);
}

.tools__approve:hover {
  border-color: var(--bm-green);
}

/* ---------- Card editor ---------- */
.tools__form {
  display: grid;
  gap: 18px;
}

.tools__preview {
  display: grid;
  gap: 10px;
  max-width: 340px;
}

.tools__submit {
  display: flex;
  justify-content: flex-end;
}

.tools__avatar {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 16px;
  padding: 16px;
}

.tools__avatar-open {
  position: relative;
  padding: 0;
  border: 0;
  border-radius: 20px;
  background: transparent;
  cursor: zoom-in;
}

.tools__avatar-open :deep(.team-avatar) {
  width: 72px;
  height: 72px;
  border-radius: 20px;
}

.tools__avatar-open > span {
  position: absolute;
  right: -4px;
  bottom: -4px;
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border: 1px solid var(--c-line-strong);
  border-radius: 50%;
  background: var(--c-surface-2);
  color: var(--c-text);
}

.tools__avatar-main {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.tools__avatar-main strong {
  color: var(--c-text);
  font-size: 14px;
}

.tools__avatar-main p {
  margin: 0;
  color: var(--c-text-3);
  font-size: 12.5px;
  line-height: 1.45;
}

.tools__upload {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 10px;
  margin-top: 4px;
}

.tools__file input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
}

.tools__file:focus-within {
  outline: 2px solid var(--bm-blue-bright);
  outline-offset: 3px;
}

.tools__filename {
  flex: 1 1 120px;
  min-width: 0;
  overflow: hidden;
  color: var(--c-text);
  font-family: var(--font-mono);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tools__filename.is-empty {
  color: var(--c-text-3);
}

/* ---------- Ownership ---------- */
.tools__transfer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  gap: 12px;
}

.tools__transfer > .ui-btn {
  margin-top: 29px;
}

.tools__danger {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 16px;
  border: 1px solid color-mix(in srgb, var(--bm-red) 30%, transparent);
  border-radius: var(--r-md);
  background:
    repeating-linear-gradient(135deg, color-mix(in srgb, var(--bm-red) 6%, transparent) 0 10px, transparent 10px 20px),
    color-mix(in srgb, var(--bm-red) 6%, transparent);
}

.tools__danger > div {
  display: grid;
  flex: 1 1 240px;
  gap: 4px;
}

.tools__danger strong {
  color: color-mix(in srgb, var(--bm-red) 80%, var(--c-text));
  font-size: 14px;
}

.tools__danger p {
  margin: 0;
  color: var(--c-text-2);
  font-size: 13px;
  line-height: 1.5;
}

/* ---------- Tab transition ---------- */
.tools-tab-enter-active {
  transition: opacity var(--dur-3) var(--ease-out), transform var(--dur-3) var(--ease-ios), filter var(--dur-3) var(--ease-out);
}

.tools-tab-leave-active {
  transition: opacity var(--dur-1) ease-in, transform var(--dur-1) ease-in;
}

.tools-tab-enter-from {
  opacity: 0;
  filter: blur(6px);
  transform: translateY(10px);
}

.tools-tab-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

@media (max-width: 560px) {
  .tools__transfer {
    grid-template-columns: minmax(0, 1fr);
  }

  .tools__transfer > .ui-btn {
    margin-top: 0;
  }

  .tools__avatar {
    grid-template-columns: minmax(0, 1fr);
    justify-items: start;
  }
}

@media (prefers-reduced-motion: reduce) {
  .tools-tab-enter-active,
  .tools-tab-leave-active {
    transition: none;
  }
}
</style>
