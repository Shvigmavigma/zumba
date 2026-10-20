<script setup>
// The team's pilots: search, sort, rating per simulator and paging. Rows glide
// to their new places when the order changes.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Search, UserMinus, Users } from 'lucide-vue-next'
import PaginationControls from '../../components/PaginationControls.vue'
import { gameOptions } from '../../i18nLabels'
import { filterPilots, pilotName, sortPilots } from '../../pilotDisplay'
import EmptyState from '../../ui/EmptyState.vue'
import SegmentedControl from '../../ui/SegmentedControl.vue'
import MemberRow from './MemberRow.vue'

const PAGE_SIZE = 10
const RANKED_SORTS = ['rating_desc', 'sr_desc']

const props = defineProps({
  team: { type: Object, required: true },
  canManage: { type: Boolean, default: false },
  busyMembers: { type: Object, default: () => ({}) }
})
const game = defineModel('game', { type: String, default: 'ACC' })
const emit = defineEmits(['remove'])
const { t } = useI18n()

const search = ref('')
const sort = ref('rating_desc')
const page = ref(1)

const sortOptions = computed(() => [
  { value: 'rating_desc', label: t('sort.ratingDesc') },
  { value: 'rating_asc', label: t('sort.ratingAsc') },
  { value: 'sr_desc', label: t('sort.srDesc') },
  { value: 'sr_asc', label: t('sort.srAsc') },
  { value: 'alpha_asc', label: t('sort.alphaAsc') },
  { value: 'alpha_desc', label: t('sort.alphaDesc') }
])
const members = computed(() => props.team.members || [])
const visible = computed(() => sortPilots(filterPilots(members.value, search.value), sort.value, game.value))
const totalPages = computed(() => Math.max(1, Math.ceil(visible.value.length / PAGE_SIZE)))
const paged = computed(() => visible.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE))
const ranked = computed(() => RANKED_SORTS.includes(sort.value) && !search.value.trim())

watch(() => props.team.id, () => { page.value = 1 })
watch([search, sort], () => { page.value = 1 })
watch(visible, () => {
  if (page.value > totalPages.value) page.value = totalPages.value
})
</script>

<template>
  <section class="roster ui-card" aria-labelledby="team-roster-title">
    <header class="roster__head">
      <div class="roster__title">
        <p class="ui-eyebrow ui-eyebrow--accent">{{ t('teamsPage.roster.eyebrow', { count: members.length, limit: team.member_limit }) }}</p>
        <h3 id="team-roster-title" class="ui-title roster__h">{{ t('fields.participants') }}</h3>
      </div>
      <SegmentedControl v-model="game" size="sm" :options="gameOptions(t)" :aria-label="t('teamsPage.roster.ratingGame')" />
    </header>

    <div class="roster__tools">
      <label class="roster__search">
        <span class="ui-sr">{{ t('teams.memberSearch') }}</span>
        <Search class="roster__search-icon" :size="17" aria-hidden="true" />
        <input v-model="search" class="ui-input" type="search" :placeholder="t('teams.memberSearch')" />
      </label>
      <label class="roster__sort">
        <span class="ui-sr">{{ t('common.sort') }}</span>
        <select v-model="sort" class="ui-select" :aria-label="t('common.sort')">
          <option v-for="option in sortOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
      </label>
    </div>

    <TransitionGroup v-if="paged.length" tag="ol" name="ui-list" class="roster__list">
      <li v-for="(member, index) in paged" :key="member.id">
        <MemberRow
          :member="member"
          :game="game"
          :position="(page - 1) * PAGE_SIZE + index + 1"
          :podium="ranked"
          :owner="member.id === team.owner_id"
          :team-name="team.name"
          :team-abbreviation="team.abbreviation"
          :to="`/pilots/${member.id}`"
          show-games
        >
          <template v-if="canManage && member.id !== team.owner_id" #actions>
            <button
              class="ui-btn ui-btn--ghost ui-btn--icon ui-btn--sm roster__remove"
              type="button"
              :title="t('teams.removeMember')"
              :aria-label="`${t('teams.removeMember')}: ${pilotName(member, member.login)}`"
              :disabled="busyMembers[member.id]"
              @click="emit('remove', member)"
            >
              <UserMinus :size="16" />
            </button>
          </template>
        </MemberRow>
      </li>
    </TransitionGroup>
    <EmptyState
      v-else
      compact
      :icon="Users"
      :title="members.length ? t('common.noMatches') : t('teams.noMembers')"
      :text="members.length ? t('teamsPage.roster.noMatchesText') : ''"
    />

    <PaginationControls v-model:page="page" :page-size="PAGE_SIZE" :total-items="visible.length" />
  </section>
</template>

<style scoped>
.roster {
  gap: 18px;
}

.roster__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 14px;
}

.roster__title {
  display: grid;
  gap: 8px;
}

.roster__h {
  font-size: 20px;
}

.roster__tools {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(150px, 210px);
  gap: 10px;
}

.roster__search {
  position: relative;
  display: grid;
}

.roster__search-icon {
  position: absolute;
  top: 50%;
  left: 14px;
  color: var(--c-text-3);
  pointer-events: none;
  transform: translateY(-50%);
  transition: color var(--dur-2);
}

.roster__search:focus-within .roster__search-icon {
  color: var(--c-accent-text);
}

.roster__search .ui-input {
  min-height: 44px;
  padding-left: 42px;
}

.roster__sort .ui-select {
  min-height: 44px;
}

.roster__list {
  position: relative;
  display: grid;
  gap: 2px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.roster__list > li.ui-list-leave-active {
  width: 100%;
}

.roster__remove {
  --btn-fg: color-mix(in srgb, var(--bm-red) 80%, var(--c-text));
}

.roster__remove:hover {
  --btn-bg: color-mix(in srgb, var(--bm-red) 14%, transparent);
}

@media (max-width: 560px) {
  .roster__tools {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
