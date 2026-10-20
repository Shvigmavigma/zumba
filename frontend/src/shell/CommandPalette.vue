<script setup>
// ⌘K / Ctrl+K search (Kokonut UI "action search bar"): jump to any section,
// find a pilot by name, nickname or number, or open an upcoming race.
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { onKeyStroke, useDebounceFn } from '@vueuse/core'
import { ArrowRight, CornerDownLeft, Flag, Search, UserRound } from 'lucide-vue-next'
import UserAvatar from '../components/UserAvatar.vue'
import { api } from '../api'
import { formatPilotNumber, formatRating, pilotName, ratingForGame } from '../pilotDisplay'
import { formatShortDate } from '../timezone'
import { closePalette, paletteOpen } from './commandPalette'
import { useNavigation } from './useNavigation'

const { t } = useI18n()
const router = useRouter()
const { publicItems, staffItems } = useNavigation()

const query = ref('')
const input = ref(null)
const pilots = ref([])
const races = ref([])
const loadingPilots = ref(false)
const error = ref('')
const activeIndex = ref(0)
let racesLoaded = false

const needle = computed(() => query.value.trim().toLowerCase())

const sections = computed(() => [...publicItems.value, ...staffItems.value]
  .filter((item) => !needle.value || item.label.toLowerCase().includes(needle.value))
  .map((item) => ({ id: `nav-${item.key}`, kind: 'nav', icon: item.icon, title: item.label, to: item.to })))

const raceResults = computed(() => (needle.value.length < 2 ? [] : races.value
  .filter((race) => `${race.name} ${race.track} ${race.car_class}`.toLowerCase().includes(needle.value))
  .slice(0, 5)
  .map((race) => ({ id: `race-${race.id}`, kind: 'race', title: race.name, meta: `${race.track} · ${formatShortDate(race.datetime_start)}`, to: `/races/${race.id}` }))))

const pilotResults = computed(() => pilots.value.map((pilot) => ({
  id: `pilot-${pilot.id}`,
  kind: 'pilot',
  pilot,
  title: pilotName(pilot, pilot.login),
  meta: `#${formatPilotNumber(pilot.pilot_number)} · ${pilot.nickname || pilot.login} · RER ${formatRating(ratingForGame(pilot, 'ACC'))}`,
  to: `/pilots/${pilot.id}`
})))

const groups = computed(() => [
  { key: 'sections', label: t('ui.palette.sections'), items: sections.value.slice(0, needle.value ? 6 : 8) },
  { key: 'pilots', label: t('ui.palette.pilots'), items: pilotResults.value },
  { key: 'races', label: t('ui.palette.races'), items: raceResults.value }
].filter((group) => group.items.length))

const flat = computed(() => groups.value.flatMap((group) => group.items))

const searchPilots = useDebounceFn(async (value) => {
  if (value.length < 2) {
    pilots.value = []
    loadingPilots.value = false
    return
  }
  try {
    const params = new URLSearchParams({ search: value, limit: '6', sort: 'rating_desc' })
    pilots.value = await api(`/users/pilots?${params.toString()}`)
    error.value = ''
  } catch (err) {
    error.value = err.message
  } finally {
    loadingPilots.value = false
  }
}, 220)

async function loadRaces() {
  if (racesLoaded) return
  racesLoaded = true
  try {
    races.value = await api('/races?status_filter=not_finished&limit=50&offset=0')
  } catch {
    racesLoaded = false
  }
}

watch(query, (value) => {
  activeIndex.value = 0
  const trimmed = value.trim()
  loadingPilots.value = trimmed.length >= 2
  searchPilots(trimmed)
})

watch(paletteOpen, async (open) => {
  document.documentElement.style.overflow = open ? 'hidden' : ''
  if (!open) return
  query.value = ''
  pilots.value = []
  activeIndex.value = 0
  loadRaces()
  await nextTick()
  input.value?.focus()
})

onKeyStroke((event) => (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k', (event) => {
  event.preventDefault()
  paletteOpen.value = !paletteOpen.value
})

function go(item) {
  if (!item) return
  closePalette()
  router.push(item.to)
}

function onKeydown(event) {
  if (event.key === 'Escape') {
    closePalette()
  } else if (event.key === 'ArrowDown') {
    event.preventDefault()
    activeIndex.value = (activeIndex.value + 1) % Math.max(1, flat.value.length)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    activeIndex.value = (activeIndex.value - 1 + flat.value.length) % Math.max(1, flat.value.length)
  } else if (event.key === 'Enter') {
    event.preventDefault()
    go(flat.value[activeIndex.value])
  }
}

function indexOf(item) {
  return flat.value.indexOf(item)
}
</script>

<template>
  <Teleport to="body">
    <Transition name="ui-fade">
      <div v-if="paletteOpen" class="palette-backdrop" @click="closePalette"></div>
    </Transition>
    <Transition name="ui-pop">
      <div v-if="paletteOpen" class="palette ui-glass ui-glass--strong" role="dialog" aria-modal="true" :aria-label="t('ui.palette.open')" @keydown="onKeydown">
        <label class="palette__field">
          <Search :size="20" aria-hidden="true" />
          <input
            ref="input"
            v-model="query"
            type="search"
            autocomplete="off"
            spellcheck="false"
            :placeholder="t('ui.palette.placeholder')"
            role="combobox"
            aria-expanded="true"
            aria-controls="palette-results"
            :aria-activedescendant="flat[activeIndex]?.id"
          />
          <kbd>Esc</kbd>
        </label>

        <div id="palette-results" class="palette__results" role="listbox">
          <section v-for="group in groups" :key="group.key" class="palette__group">
            <p class="ui-eyebrow palette__label">{{ group.label }}</p>
            <button
              v-for="item in group.items"
              :id="item.id"
              :key="item.id"
              class="palette__item"
              :class="{ 'is-active': indexOf(item) === activeIndex }"
              type="button"
              role="option"
              :aria-selected="indexOf(item) === activeIndex"
              @mouseenter="activeIndex = indexOf(item)"
              @click="go(item)"
            >
              <span class="palette__icon">
                <UserAvatar v-if="item.kind === 'pilot'" mini :src="item.pilot.avatar_url" :color="item.pilot.avatar_color" :label="item.title" />
                <Flag v-else-if="item.kind === 'race'" :size="17" />
                <component :is="item.icon || UserRound" v-else :size="17" />
              </span>
              <span class="palette__text">
                <strong>{{ item.title }}</strong>
                <small v-if="item.meta">{{ item.meta }}</small>
              </span>
              <ArrowRight class="palette__go" :size="16" />
            </button>
          </section>

          <p v-if="loadingPilots" class="palette__status ui-shiny">{{ t('ui.palette.searching') }}</p>
          <p v-else-if="needle.length >= 2 && !pilotResults.length && !raceResults.length && !sections.length" class="palette__status">
            {{ t('ui.palette.nothing', { query: query.trim() }) }}
          </p>
          <p v-if="error" class="palette__status palette__status--error">{{ error }}</p>
        </div>

        <footer class="palette__foot">
          <span><kbd>↑</kbd><kbd>↓</kbd>{{ t('ui.palette.navigate') }}</span>
          <span><kbd><CornerDownLeft :size="12" /></kbd>{{ t('ui.palette.select') }}</span>
        </footer>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.palette-backdrop {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: var(--c-overlay);
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
}

.palette {
  position: fixed;
  top: min(14vh, 140px);
  left: 50%;
  z-index: 101;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  width: min(640px, calc(100vw - 24px));
  max-height: min(70vh, 620px);
  margin-left: calc(min(640px, calc(100vw - 24px)) / -2);
  overflow: hidden;
  border-radius: var(--r-xl);
  box-shadow: var(--shadow-2), 0 0 0 1px var(--c-line-strong);
}

.palette__field {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  border-bottom: 1px solid var(--c-line);
  color: var(--c-text-3);
}

.palette__field input {
  flex: 1 1 auto;
  min-width: 0;
  height: 32px;
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
  color: var(--c-text);
  font-size: 17px;
  outline: none;
}

.palette__field input:focus {
  box-shadow: none;
}

.palette__field input::-webkit-search-cancel-button {
  display: none;
}

kbd {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 3px 7px;
  border: 1px solid var(--c-line-strong);
  border-radius: 7px;
  background: color-mix(in srgb, var(--c-text) 5%, transparent);
  color: var(--c-text-2);
  font-family: var(--font-mono);
  font-size: 11px;
}

.palette__results {
  display: grid;
  align-content: start;
  gap: 10px;
  padding: 10px;
  overflow-y: auto;
}

.palette__label {
  padding: 6px 10px 4px;
}

.palette__group {
  display: grid;
  gap: 2px;
}

.palette__item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  min-height: 52px;
  padding: 8px 10px;
  border: 0;
  border-radius: var(--r-md);
  background: transparent;
  color: var(--c-text);
  cursor: pointer;
  font-family: var(--font-body);
  text-align: left;
}

.palette__item.is-active {
  background: var(--c-blue-soft);
  box-shadow: inset 0 0 0 1px var(--c-blue-line);
}

.palette__icon {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 11px;
  background: var(--c-sunken);
  color: var(--c-accent-text);
}

.palette__icon :deep(.user-avatar) {
  width: 36px;
  height: 36px;
  border-width: 1px;
  box-shadow: none;
}

.palette__text {
  display: grid;
  flex: 1 1 auto;
  gap: 2px;
  min-width: 0;
}

.palette__text strong {
  overflow: hidden;
  font-size: 14px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.palette__text small {
  overflow: hidden;
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 11.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.palette__go {
  color: var(--c-text-3);
  opacity: 0;
  transform: translateX(-4px);
  transition: opacity var(--dur-2), transform var(--dur-2) var(--ease-ios);
}

.palette__item.is-active .palette__go {
  color: var(--c-accent-text);
  opacity: 1;
  transform: none;
}

.palette__status {
  margin: 0;
  padding: 14px 10px;
  color: var(--c-text-2);
  font-size: 14px;
  text-align: center;
}

.palette__status--error {
  color: color-mix(in srgb, var(--bm-red) 80%, var(--c-text));
}

.palette__foot {
  display: flex;
  gap: 18px;
  padding: 10px 18px;
  border-top: 1px solid var(--c-line);
  color: var(--c-text-3);
  font-size: 12px;
}

.palette__foot span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

@media (max-width: 760px) {
  .palette {
    top: 10px;
    max-height: calc(100dvh - 20px);
  }

  .palette__foot {
    display: none;
  }
}
</style>
