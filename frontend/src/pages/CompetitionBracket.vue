<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ArrowUpRight, BarChart3, CheckCircle2, Clock3, Trophy, Users, Vote } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import { api } from '../api'

const route = useRoute()
const competition = ref(null)
const loading = ref(true)
const error = ref('')
let pollTimer = null
let pollingActive = false
const bracketRoutesEl = ref(null)
const connectorPaths = ref([])

const token = computed(() => String(route.params.token || ''))
const statusLabel = computed(() => ({ draft: 'Черновик', 'in-progress': 'Идёт', complete: 'Завершён' }[competition.value?.status] || ''))
const statusDescription = computed(() => ({
  draft: 'Сетка будет доступна после запуска турнира.',
  'in-progress': 'Голосование идёт. Результаты обновляются автоматически.',
  complete: 'Все результаты опубликованы.'
}[competition.value?.status] || ''))
const selectionSystemLabel = computed(() => ({
  direct: 'Прямой плей-офф',
  qualifying: 'Отбор + плей-офф',
  groups: 'Группы + плей-офф',
  double_elimination: 'Верхняя + нижняя сетка (8 → 4)',
}[competition.value?.settings?.variant] || 'Прямой плей-офф'))
const advancingPlacesDescription = computed(() => {
  if (competition.value?.settings?.variant === 'double_elimination') return 'Ровно 8 участников: 4 победителя сеток переходят в полуфинал.'
  if (competition.value?.settings?.variant !== 'groups') return ''
  const places = [...new Set((competition.value?.settings?.advancing_places || [1]).map(Number).filter((place) => Number.isInteger(place) && place > 0))].sort((left, right) => left - right)
  return places.length ? `В плей-офф проходят ${places.map((place) => `${place}-е`).join(', ')} места из каждой группы` : ''
})
const pairPath = (match) => `/competitions/view/${encodeURIComponent(token.value)}?match=${encodeURIComponent(match.id)}`
const overviewPath = computed(() => competition.value?.public_path || `/competitions/view/${encodeURIComponent(token.value)}`)
const mediaUrl = (value) => {
  const raw = String(value || '').trim()
  if (!raw) return ''
  if (/^(?:https?:|data:|blob:)/i.test(raw)) return raw
  return raw.startsWith('/') ? raw : `/${raw}`
}
const formatVotes = (value) => {
  const amount = Number(value || 0)
  return `${amount} ${amount === 1 ? 'голос' : amount >= 2 && amount <= 4 ? 'голоса' : 'голосов'}`
}
const participantInitials = (participant) => String(participant?.name || '?').trim().slice(0, 2).toUpperCase()
const matchStatusLabel = (match) => match.status === 'open' ? 'Голосование открыто' : match.status === 'bye' ? 'Автопроход' : 'Завершено'
const matchStageLabel = (match) => ({
  group: `Группа ${match?.group || 1}`,
  qualifying: 'Отбор',
  upper: 'Верхняя сетка',
  lower: 'Нижняя сетка',
  semifinal: 'Полуфинал',
  third_place: 'Матч за 3-е место',
  playoff: 'Финал',
}[match?.stage] || 'Плей-офф')
const displayMatchStageLabel = (match) => match?.stage === 'upper' && Number(match?.round || 1) === 1 ? '1 этап' : matchStageLabel(match)
const matchTotalVotes = (match) => Number(match.votes_a || 0) + Number(match.votes_b || 0)
const voteShare = (match, side) => {
  const total = matchTotalVotes(match)
  if (!total) return 0
  return Math.round((Number(side === 'a' ? match.votes_a : match.votes_b || 0) / total) * 100)
}

function roundLabel(round, maxRound) {
  const denominator = 2 ** (maxRound - round)
  return denominator <= 1 ? 'Финал' : `1/${denominator}`
}

const columns = computed(() => {
  const matches = competition.value?.matches || []
  const matchHeight = 174
  const baseGap = 32
  const playoffMatches = matches.filter((match) => match.stage === 'playoff')
  const maxRound = Math.max(...playoffMatches.map((match) => Number(match.round) || 1), 1)
  const grouped = new Map()
  for (const match of matches) {
    const type = match.stage === 'group' ? 'group' : match.stage === 'qualifying' ? 'qualifying' : ['upper', 'lower', 'semifinal', 'third_place'].includes(match.stage) ? match.stage : 'playoff'
    const number = type === 'group' ? Number(match.group) || 1 : Number(match.round) || 1
    const key = `${type}-${number}`
    if (!grouped.has(key)) {
      const label = type === 'playoff'
        ? roundLabel(number, maxRound)
        : type === 'upper'
          ? number === 1 ? '1 этап' : `Раунд ${number}`
          : type === 'lower'
            ? `Раунд ${number}`
            : matchStageLabel(match)
      const depth = ['playoff', 'upper', 'lower'].includes(type) ? Math.max(0, number - 1) : 0
      grouped.set(key, {
        key,
        type,
        number,
        label,
        depth,
        offset: depth ? ((matchHeight + baseGap) * (2 ** depth - 1)) / 2 : 0,
        gap: depth ? (matchHeight + baseGap) * (2 ** depth) - matchHeight : baseGap,
        matches: [],
      })
    }
    grouped.get(key).matches.push(match)
  }
  return [...grouped.values()].sort((left, right) => {
    const order = { group: 0, qualifying: 1, upper: 2, lower: 3, semifinal: 4, playoff: 5, third_place: 6 }
    return order[left.type] - order[right.type] || left.number - right.number
  })
})

const isDoubleElimination = computed(() => competition.value?.settings?.variant === 'double_elimination')
const bracketRoutes = computed(() => {
  const columnsList = visibleColumns.value
  if (!isDoubleElimination.value) return [{ key: 'main', columns: columnsList }]
  return [
    { key: 'opening', kicker: 'Этап', label: 'До распределения', columns: columnsList.filter((column) => column.type === 'upper' && column.number === 1) },
    { key: 'upper', label: 'Верхняя сетка', columns: columnsList.filter((column) => column.type === 'upper' && column.number > 1) },
    { key: 'lower', label: 'Нижняя сетка', columns: columnsList.filter((column) => column.type === 'lower') },
    { key: 'final', label: 'Финальная стадия', columns: columnsList.filter((column) => ['semifinal', 'playoff'].includes(column.type)) },
    { key: 'third', label: 'Матч за 3-е место', columns: columnsList.filter((column) => column.type === 'third_place') },
  ].filter((route) => route.columns.length)
})

const activePhase = ref('playoff')
const activeView = ref('playoff')
const phaseTabs = computed(() => {
  const groups = columns.value.filter((column) => column.type === 'group')
  const playoff = columns.value.filter((column) => column.type !== 'group')
  return [
    groups.length ? { key: 'groups', label: 'Групповой этап', count: groups.reduce((sum, column) => sum + column.matches.length, 0) } : null,
    playoff.length ? { key: 'playoff', label: 'Плей-офф', count: playoff.reduce((sum, column) => sum + column.matches.length, 0) } : null,
  ].filter(Boolean)
})
const viewTabs = computed(() => {
  const tabs = [
    phaseTabs.value.some((tab) => tab.key === 'playoff') ? { key: 'playoff', label: 'Турнирная сетка', count: phaseTabs.value.find((tab) => tab.key === 'playoff')?.count || 0 } : null,
    phaseTabs.value.some((tab) => tab.key === 'groups') ? { key: 'groups', label: 'Групповой этап', count: phaseTabs.value.find((tab) => tab.key === 'groups')?.count || 0 } : null,
    competition.value?.status === 'complete' && resultRows.value.length ? { key: 'results', label: 'Результаты', count: resultRows.value.length } : null,
  ]
  return tabs.filter(Boolean)
})
const visibleColumns = computed(() => columns.value.filter((column) => activePhase.value === 'groups' ? column.type === 'group' : column.type !== 'group'))

const resultRows = computed(() => {
  const participants = competition.value?.participants || []
  const byId = new Map(participants.map((participant) => [participant.id, participant]))
  return [...(competition.value?.results || [])]
    .sort((left, right) => Number(left.place || 999) - Number(right.place || 999))
    .map((result) => ({
      ...result,
      participant: byId.get(result.participant_id) || { name: 'Участник', images: [] },
      place: Number(result.place || 0),
      votes: Number(result.votes || 0),
    }))
})
const resultTotalVotes = computed(() => resultRows.value.reduce((sum, row) => sum + row.votes, 0))
const resultWinner = computed(() => resultRows.value[0] || null)
const podiumRows = computed(() => [resultRows.value[1], resultRows.value[0], resultRows.value[2]].filter(Boolean))

const stats = computed(() => {
  const matches = competition.value?.matches || []
  return {
    participants: competition.value?.participants?.length || 0,
    matches: matches.length,
    closed: matches.filter((match) => match.status === 'closed').length,
    votes: matches.reduce((sum, match) => sum + matchTotalVotes(match), 0),
  }
})
const hasLiveMatches = computed(() => stats.value.matches > stats.value.closed)

function updateBracketConnectors() {
  const canvas = bracketRoutesEl.value
  if (!canvas || !isDoubleElimination.value || activeView.value !== 'playoff') {
    connectorPaths.value = []
    canvas?.querySelector('.standalone-bracket-route.is-third')?.style.removeProperty('--standalone-bracket-third-shift')
    return
  }
  const canvasRect = canvas.getBoundingClientRect()
  const thirdRoute = canvas.querySelector('.standalone-bracket-route.is-third')
  thirdRoute?.style.removeProperty('--standalone-bracket-third-shift')
  const upperMatches = [...canvas.querySelectorAll('.standalone-bracket-route.is-upper .standalone-bracket-match')]
  const lowerMatches = [...canvas.querySelectorAll('.standalone-bracket-route.is-lower .standalone-bracket-match')]
  const semifinalMatches = [...canvas.querySelectorAll('.standalone-bracket-route.is-final .standalone-bracket-column.is-semifinal .standalone-bracket-match')]
  const toPoint = (element, side) => {
    const rect = element.getBoundingClientRect()
    return {
      x: (side === 'right' ? rect.right : rect.left) - canvasRect.left,
      y: rect.top - canvasRect.top + rect.height / 2,
    }
  }
  const paths = []
  const addConnections = (matches, kind) => {
    matches.slice(0, semifinalMatches.length).forEach((source, index) => {
      const start = toPoint(source, 'right')
      const end = toPoint(semifinalMatches[index], 'left')
      const bendX = end.x - 16
      paths.push({
        key: `${kind}-${index}`,
        kind,
        d: `M ${start.x} ${start.y} H ${bendX} V ${end.y} H ${end.x}`,
      })
    })
  }
  addConnections(upperMatches, 'upper')
  addConnections(lowerMatches, 'lower')
  connectorPaths.value = paths

  const finalMatch = canvas.querySelector('.standalone-bracket-route.is-final .standalone-bracket-column.is-playoff .standalone-bracket-match')
  if (finalMatch && thirdRoute) {
    const finalRect = finalMatch.getBoundingClientRect()
    const thirdRect = thirdRoute.getBoundingClientRect()
    const shift = finalRect.bottom + 28 - thirdRect.top
    thirdRoute.style.setProperty('--standalone-bracket-third-shift', `${shift}px`)
  }
}

function scheduleBracketConnectors() {
  window.requestAnimationFrame(updateBracketConnectors)
}

async function load() {
  try {
    const next = await api(`/competitions/public/${token.value}`)
    competition.value = next
    error.value = ''
  } catch (err) {
    if (!competition.value) error.value = err.message
  } finally {
    loading.value = false
  }
}

function startPolling() {
  pollingActive = true
  const tick = async () => {
    if (!pollingActive) return
    await load()
    if (pollingActive && competition.value?.status !== 'complete') pollTimer = window.setTimeout(tick, 5000)
  }
  pollTimer = window.setTimeout(tick, 5000)
}

function stopPolling() {
  pollingActive = false
  if (pollTimer) window.clearTimeout(pollTimer)
  pollTimer = null
}

onMounted(async () => {
  await load()
  await nextTick()
  scheduleBracketConnectors()
  window.addEventListener('resize', scheduleBracketConnectors)
  if (competition.value?.status !== 'complete') startPolling()
})
watch(() => competition.value?.settings?.phase, (phase) => {
  if (phase) activePhase.value = phase === 'groups' ? 'groups' : 'playoff'
}, { immediate: true })
watch(() => competition.value?.status, (status) => {
  if (status === 'complete' && resultRows.value.length) activeView.value = competition.value?.settings?.variant === 'double_elimination' ? 'playoff' : 'results'
  else if (status !== 'complete' && activeView.value === 'results') activeView.value = 'playoff'
}, { immediate: true })
watch(() => `${competition.value?.matches?.length || 0}:${activeView.value}:${activePhase.value}`, async () => {
  await nextTick()
  scheduleBracketConnectors()
})
onBeforeUnmount(() => {
  stopPolling()
  window.removeEventListener('resize', scheduleBracketConnectors)
})
</script>

<template>
  <section class="standalone-bracket-page" :class="{ 'is-double-elimination': competition?.settings?.variant === 'double_elimination' }">
    <div v-if="loading" class="standalone-bracket-loading" aria-live="polite">
      <div class="standalone-bracket-skeleton skeleton-line wide"></div>
      <div class="standalone-bracket-skeleton skeleton-line"></div>
      <div class="standalone-bracket-skeleton-grid"><div v-for="index in 3" :key="index" class="standalone-bracket-skeleton skeleton-card"></div></div>
    </div>
    <div v-else-if="error" class="standalone-bracket-empty"><Trophy :size="32" /><h1>Ссылка недействительна</h1><p>{{ error }}</p></div>
    <template v-else-if="competition">
      <header class="standalone-bracket-heading">
        <div class="standalone-bracket-heading-copy">
          <div class="standalone-bracket-eyebrow"><Trophy :size="15" />Публичный турнир</div>
          <div class="standalone-bracket-title-row"><h1>{{ competition.name }}</h1><span class="standalone-bracket-status" :class="`is-${competition.status}`"><span></span>{{ statusLabel }}</span></div>
          <p>{{ statusDescription }}</p>
          <p class="standalone-bracket-system"><span>Система отбора</span><strong>{{ selectionSystemLabel }}</strong><small v-if="advancingPlacesDescription">{{ advancingPlacesDescription }}</small></p>
        </div>
        <div class="standalone-bracket-live" :class="{ 'is-live': hasLiveMatches }"><span class="standalone-bracket-live-dot"></span><span>{{ hasLiveMatches ? 'Обновляется онлайн' : 'Результаты зафиксированы' }}</span><Clock3 :size="15" /></div>
      </header>

      <div class="standalone-bracket-stats" aria-label="Статистика турнира">
        <div class="standalone-bracket-stat"><Users :size="17" /><span><b>{{ stats.participants }}</b> участников</span></div>
        <div class="standalone-bracket-stat"><Vote :size="17" /><span><b>{{ formatVotes(stats.votes) }}</b></span></div>
        <div class="standalone-bracket-stat"><CheckCircle2 :size="17" /><span><b>{{ stats.closed }} / {{ stats.matches }}</b> пар завершено</span></div>
      </div>

      <div v-if="!columns.length" class="standalone-bracket-empty"><Trophy :size="32" /><h2>Сетка ещё не создана</h2><p>Ожидается запуск турнира.</p></div>
      <template v-else>
        <div v-if="viewTabs.length > 1" class="standalone-bracket-phase-switch" role="tablist" aria-label="Раздел турнира">
          <button v-for="tab in viewTabs" :key="tab.key" class="standalone-bracket-phase-tab" :class="{ 'is-active': activeView === tab.key }" type="button" role="tab" :aria-selected="activeView === tab.key" @click="activeView = tab.key; if (tab.key === 'groups' || tab.key === 'playoff') activePhase = tab.key">
            <span>{{ tab.label }}</span><small>{{ tab.count }} {{ tab.key === 'results' ? 'мест' : tab.count === 1 ? 'пара' : 'пар' }}</small>
          </button>
        </div>
        <div v-if="activeView === 'results'" class="standalone-results-panel">
          <header class="standalone-results-hero"><div><span class="standalone-results-kicker"><Trophy :size="15" />Финальные результаты</span><h2>Турнир завершён</h2><p>Итоговая таблица собрана по результатам всех пар.</p></div><div v-if="resultWinner" class="standalone-results-winner"><small>Победитель</small><strong>{{ resultWinner.participant.name }}</strong><span>{{ formatVotes(resultWinner.votes) }}</span></div></header>
          <div class="standalone-results-podium" v-if="resultRows.length"><article v-for="row in podiumRows" :key="row.participant_id" class="standalone-results-podium-card" :class="`place-${row.place}`"><span class="standalone-results-place">{{ row.place }}</span><div class="standalone-results-avatar"><img v-if="row.participant.images?.[0]" :src="mediaUrl(row.participant.images[0])" :alt="row.participant.name" /><span v-else>{{ participantInitials(row.participant) }}</span></div><strong>{{ row.participant.name }}</strong><span>{{ formatVotes(row.votes) }}</span><small>{{ resultTotalVotes ? Math.round((row.votes / resultTotalVotes) * 100) : 0 }}% голосов</small></article></div>
          <div class="standalone-results-ranking"><div class="standalone-results-ranking-head"><span>Место</span><span>Участник</span><span>Голоса</span></div><div v-for="row in resultRows.slice(3)" :key="row.participant_id" class="standalone-results-ranking-row"><b>{{ row.place }}</b><span class="standalone-results-ranking-name"><span class="standalone-results-mini-avatar">{{ participantInitials(row.participant) }}</span>{{ row.participant.name }}</span><strong>{{ formatVotes(row.votes) }}</strong></div><p v-if="resultRows.length <= 3" class="standalone-results-ranking-empty">Все участники вошли в подиум.</p></div>
        </div>
        <div v-else class="standalone-bracket-scroll">
          <div ref="bracketRoutesEl" class="standalone-bracket-routes" :class="{ 'is-double': isDoubleElimination }">
            <svg v-if="isDoubleElimination && connectorPaths.length" class="standalone-bracket-route-connectors" aria-hidden="true">
              <path v-for="connector in connectorPaths" :key="connector.key" :class="`is-${connector.kind}`" :d="connector.d"></path>
            </svg>
            <section v-for="route in bracketRoutes" :key="route.key" class="standalone-bracket-route" :class="`is-${route.key}`">
              <header v-if="route.label" class="standalone-bracket-route-head"><div><span>{{ route.kicker || 'Сетка' }}</span><strong>{{ route.label }}</strong></div><small>{{ route.columns.reduce((sum, column) => sum + column.matches.length, 0) }} пар</small></header>
              <div class="standalone-bracket-columns">
                <section v-for="column in route.columns" :key="column.key" class="standalone-bracket-column" :class="`is-${column.type}`" :style="{ '--standalone-bracket-match-count': column.matches.length, '--standalone-bracket-column-offset': `${column.offset}px`, '--standalone-bracket-column-gap': `${column.gap}px` }">
                  <header class="standalone-bracket-column-head"><div><span>{{ column.type === 'playoff' ? 'Раунд' : 'Этап' }}</span><h2>{{ column.label }}</h2></div><span class="standalone-bracket-column-count">{{ column.matches.length }} {{ column.matches.length === 1 ? 'пара' : 'пар' }}</span></header>
                  <div class="standalone-bracket-column-matches">
                    <RouterLink v-for="(match, index) in column.matches" :key="match.id" class="standalone-bracket-match" :class="{ 'is-closed': match.status === 'closed', 'is-open': match.status === 'open', 'is-bye': match.status === 'bye' }" :to="pairPath(match)" :aria-label="`Открыть пару: ${match.a?.name || '—'} — ${match.b?.name || 'автопроход'}`">
                      <div class="standalone-bracket-match-meta"><span>{{ displayMatchStageLabel(match) }} · Пара {{ index + 1 }}</span><span class="standalone-bracket-match-state" :class="`is-${match.status}`"><i></i>{{ matchStatusLabel(match) }}</span></div>
                      <div class="standalone-bracket-team" :class="{ winner: match.winner === match.a?.id }"><span class="standalone-bracket-avatar"><img v-if="match.a?.images?.[0]" :src="mediaUrl(match.a.images[0])" alt="" /><span v-else>{{ participantInitials(match.a) }}</span></span><strong>{{ match.a?.name || '—' }}</strong><b>{{ match.votes_a }}</b></div>
                      <div class="standalone-bracket-team" :class="{ winner: match.winner === match.b?.id }"><span class="standalone-bracket-avatar"><img v-if="match.b?.images?.[0]" :src="mediaUrl(match.b.images[0])" alt="" /><span v-else>{{ participantInitials(match.b) }}</span></span><strong>{{ match.b?.name || 'Автопроход' }}</strong><b>{{ match.votes_b }}</b></div>
                      <div class="standalone-bracket-progress" aria-hidden="true"><span :style="{ width: `${voteShare(match, 'a')}%` }"></span></div>
                      <div class="standalone-bracket-match-foot"><span v-if="match.winner" class="standalone-bracket-winner" :title="match.winner_name" :aria-label="`Победитель: ${match.winner_name}`"><BarChart3 :size="13" />Победитель: {{ match.winner_name }}</span><span v-else class="standalone-bracket-vote-total">{{ formatVotes(matchTotalVotes(match)) }}</span><span class="standalone-bracket-match-link"><ArrowUpRight :size="14" />Открыть пару</span></div>
                    </RouterLink>
                  </div>
                </section>
              </div>
            </section>
          </div>
        </div>
      </template>
    </template>
  </section>
</template>
