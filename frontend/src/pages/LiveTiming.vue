<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { Cloud, CloudRain, CloudSun, CloudLightning, MapPin, Sun } from 'lucide-vue-next'
import { API_BASE } from '../api'
import { timing } from '../liveTiming'
import { formatDuration } from './race/raceTime'
import SegmentedControl from '../ui/SegmentedControl.vue'

const { locale } = useI18n()
const words = (ru, en) => locale.value === 'en' ? en : ru
const session = computed(() => timing.session)
const online = computed(() => (session.value?.drivers || []).filter(d => d.online).sort((a, b) => a.position - b.position))
const offline = computed(() => (session.value?.drivers || []).filter(d => !d.online))
const groups = computed(() => [online.value, offline.value])
const record = computed(() => (session.value?.drivers || []).filter(d => d.best > 0).sort((a,b) => a.best - b.best)[0])
const trackName = computed(() => (session.value?.track || '').replace(/^(rt|ks)_/, '').replaceAll('_', ' '))
const sessionName = computed(() => {
  const name = session.value?.name || ''
  return locale.value === 'en' ? name : ({Practice:'Практика', Qualifying:'Квалификация', Race:'Гонка'}[name] || name)
})
const mode = ref('current')
const now = ref(Date.now())
let clock
const sessionClock = computed(() => {
  const s = session.value
  if (!s || !Number.isFinite(s.elapsedMs) || s.elapsedMs < 0) return { label: words('Осталось времени','Time remaining'), value: '—' }
  const elapsed = s.elapsedMs + timing.snapshotAgeMs + (timing.stale ? 0 : Math.max(0, now.value - timing.receivedAt))
  const waiting = Math.max(0, Number(s.waitSeconds) || 0) * 1000
  if (elapsed < waiting) return { label: words('До начала сессии','Session starts in'), value: clockLabel(waiting - elapsed) }
  if (!(s.durationMinutes > 0)) {
    return s.laps > 0
      ? { label: words('Кругов','Laps'), value: String(s.laps) }
      : { label: words('Осталось времени','Time remaining'), value: '—' }
  }
  return { label: words('Осталось времени','Time remaining'), value: clockLabel(Math.max(0, s.durationMinutes * 60000 + waiting - elapsed)) }
})
function clockLabel(ms) {
  const seconds = Math.ceil(ms / 1000)
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor(seconds % 3600 / 60)
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
}
const sessionSectors = computed(() => [0, 1, 2].map(index => {
  const times = (session.value?.drivers || []).map(driver => driver.personalSectors?.[index]).filter(time => time > 0)
  return times.length ? Math.min(...times) : null
}))
function sectorClass(driver, value, index) {
  if (!(value > 0)) return ''
  if (mode.value === 'current') {
    const flags = driver.currentSectorFlags?.[index]
    if (flags?.cuts) return ''
    if (flags?.session) return 'record'
    if (flags?.personal) return 'personal-sector'
    return ''
  }
  if (value === sessionSectors.value[index]) return 'record'
  if (value === driver.personalSectors?.[index]) return 'personal-sector'
  return ''
}
const sectorOptions = computed(() => [
  { value: 'current', label: words('Текущий круг','Current lap') },
  { value: 'bestSectors', label: words('Лучший круг','Best lap') }
])
const map = ref(null)
const loadingMap = ref(false)
const trackInfo = ref(null)
const weather = computed(() => {
  const code = String(session.value?.weather || '').toLowerCase().split('_type=')[0]
  if (/thunder|storm/.test(code)) return { label: words('Гроза', 'Thunderstorm'), icon: CloudLightning }
  if (/rain|drizzle|shower/.test(code)) return { label: words('Дождь', 'Rain'), icon: CloudRain }
  if (/overcast|broken|heavy.cloud|dark.cloud/.test(code)) return { label: words('Пасмурно', 'Overcast'), icon: Cloud }
  if (/few.cloud|scattered|partly|light.cloud|mid.cloud/.test(code)) return { label: words('Переменная облачность', 'Partly cloudy'), icon: CloudSun }
  if (/clear|sunny/.test(code)) return { label: words('Ясно', 'Clear'), icon: Sun }
  if (/cloud/.test(code)) return { label: words('Пасмурно', 'Cloudy'), icon: Cloud }
  return null
})
const location = computed(() => {
  const info = trackInfo.value
  if (!info) return ''
  const country = info.country === 'USA' ? words('США', 'USA') : info.country
  const region = info.region || (session.value?.track === 'cota_2022' ? words('Техас', 'Texas') : '')
  const city = info.city === 'Austin' ? words('Остин', 'Austin') : info.city
  return [country, region, city].filter(Boolean).join(' · ')
})
const positions = ref({})
let socket
let reconnectTimer
let socketTrack
let socketLayout
let closed = false
let reconnectDelay = 1000
function connectPositions() {
  if (closed || document.hidden) return
  const url = new URL(API_BASE + '/live-timing/ac/positions', window.location.href)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  const connection = new WebSocket(url)
  socket = connection
  connection.onopen = () => { reconnectDelay = 1000 }
  connection.onmessage = event => {
    const message = JSON.parse(event.data)
    if ('track' in message) {
      if (socketTrack !== message.track || socketLayout !== message.layout) positions.value = {}
      socketTrack = message.track
      socketLayout = message.layout
    } else if (socketTrack === session.value?.track && socketLayout === session.value?.layout) {
      positions.value[message.slot] = { x: message.x, z: message.z }
    }
  }
  connection.onclose = () => {
    if (socket !== connection) return
    socket = null
    if (!closed && !document.hidden) {
      reconnectTimer = setTimeout(connectPositions, reconnectDelay)
      reconnectDelay = Math.min(reconnectDelay * 2, 10000)
    }
  }
  connection.onerror = () => connection.close()
}
function onVisibilityChange() {
  if (document.hidden) {
    clearTimeout(reconnectTimer)
    socket?.close()
  } else if (!socket) {
    connectPositions()
  }
}
onMounted(() => {
  clock = window.setInterval(() => { now.value = Date.now() }, 1000)
  connectPositions()
  document.addEventListener('visibilitychange', onVisibilityChange)
})
onBeforeUnmount(() => {
  clearInterval(clock)
  closed = true
  clearTimeout(reconnectTimer)
  socket?.close()
  document.removeEventListener('visibilitychange', onVisibilityChange)
})
const mapQuery = computed(() => session.value ? new URLSearchParams({track: session.value.track, layout: session.value.layout}).toString() : '')
watch(mapQuery, async (query, _, cleanup) => {
  trackInfo.value = null
  if (!query) return
  const controller = new AbortController()
  cleanup(() => controller.abort())
  try {
    const response = await fetch(API_BASE + '/live-timing/ac/track-info?' + query, { signal: controller.signal })
    if (response.ok) trackInfo.value = await response.json()
  } catch {
    // The map and timing continue to work while track metadata is unavailable.
  }
}, { immediate: true })
watch(mapQuery, async (query, _, cleanup) => {
  map.value = null
  if (!query) return
  const controller = new AbortController()
  let timer
  cleanup(() => { controller.abort(); clearTimeout(timer) })
  async function load() {
    loadingMap.value = true
    try {
      const response = await fetch(API_BASE + '/live-timing/ac/map?' + query, { signal: controller.signal })
      if (!response.ok) throw new Error('Map unavailable')
      const data = await response.json()
      if (!controller.signal.aborted) map.value = data
    } catch {
      if (!controller.signal.aborted) timer = setTimeout(load, 60000)
    } finally {
      if (!controller.signal.aborted) loadingMap.value = false
    }
  }
  await load()
}, { immediate: true })
const dots = computed(() => {
  if (!map.value || !timing.active) return []
  const g = map.value.geometry
  return online.value.map(d => {
    const live = positions.value[d.slot]
    const pos = live && socketTrack === session.value?.track && socketLayout === session.value?.layout ? live : d
    return { driver: d, left: ((pos.x + g.X_OFFSET) / g.SCALE_FACTOR + g.PADDING) / g.WIDTH * 100,
      top: ((pos.z + g.Z_OFFSET) / g.SCALE_FACTOR + g.PADDING) / g.HEIGHT * 100 }
  }).filter(p => Number.isFinite(p.left) && Number.isFinite(p.top))
})
const time = ms => ms > 0 ? formatDuration(ms) : '—'
const status = d => !d.online ? words('Отключился','Disconnected') : d.pit ? words('В боксах','In pits') : words('На трассе','On track')
</script>
<template>
  <section class="live">
    <header class="line"><h1 v-split>Live Timing</h1><span v-reveal="{ delay: 180, y: 10 }" role="status"><i v-if="timing.active" class="ui-dot ui-dot--live live-dot" /> {{ timing.active ? words('Сервер на связи','Server online') : timing.loaded ? words('Сервер недоступен','Server unavailable') : words('Подключение…','Connecting…') }}</span></header>
    <template v-if="session">
      <p v-if="!timing.active || timing.stale" role="status">{{ words('Показаны последние полученные данные.','Showing the last received snapshot.') }}</p>
      <div class="cards">
        <section v-reveal="{ y: 24 }" class="summary">
          <div>
            <div v-reveal="{ delay: 100, y: 8, blur: 0 }" class="ey">Assetto Corsa <span>{{ sessionName }}</span></div>
            <h2 v-reveal="{ delay: 160, y: 14, blur: 4 }" class="track">{{ trackName }}</h2><div v-reveal="{ delay: 200, y: 8 }" class="layout">{{ session.layout }}</div>
          </div>
          <div v-reveal="{ delay: 240, y: 12, blur: 4 }" class="metrics">
            <div class="best-lap">{{ words('Лучший круг сессии','Session best') }}<strong class="record">{{ time(record?.best) }}</strong>{{ record?.name }}</div>
            <div class="session-clock">{{ sessionClock.label }}<strong>{{ sessionClock.value }}</strong></div>
          </div>
        </section>
        <section v-reveal="{ delay: 240, y: 24 }" class="mapcard">
          <div v-if="location" class="map-location"><MapPin :size="16" aria-hidden="true" /><span>{{ location }}</span></div>
          <div v-if="weather" class="map-weather"><component :is="weather.icon" :size="19" aria-hidden="true" /><span>{{ weather.label }}</span></div>
          <div v-if="map" class="outline"><img :src="map.image" :alt="trackName">
            <span v-for="p in dots" :key="p.driver.slot" class="dot" :class="{ pit: p.driver.pit }" :style="{left:p.left+'%', top:p.top+'%'}" :title="p.driver.name">{{ p.driver.position }}</span>
          </div>
          <small v-else>{{ loadingMap ? words('Загрузка карты…','Loading map…') : words('Карта недоступна','Map unavailable') }}</small>
          <div class="map-temperatures">
            <div>{{ words('Воздух','Air') }}<strong>{{ session.air ?? '—' }}°C</strong></div>
            <div>{{ words('Асфальт','Track') }}<strong>{{ session.road ?? '—' }}°C</strong></div>
          </div>
        </section>
      </div>
      <section v-reveal="{ delay: 480, y: 24 }" class="board">
        <div class="boardhead line"><div><h2>{{ words('Таблица сессии','Session leaderboard') }}</h2><small>{{ online.length }} {{ words('онлайн','online') }} · {{ offline.length }} {{ words('отключились','disconnected') }}</small></div>
          <div class="modes">
            <SegmentedControl v-model="mode" :options="sectorOptions" navigation-style :aria-label="words('Секторы','Sectors')" />
          </div>
        </div>
        <div class="scroll"><table>
          <thead><tr><th v-for="label in [words('Поз.','Pos.'),words('Пилот / машина','Driver / car'),words('Круги','Laps'),'S1','S2','S3',words('Последний круг','Last lap'),words('Лучший круг','Best lap'),words('Статус','Status')]" :key="label">{{ label }}</th></tr></thead>
          <tbody v-for="(group,index) in groups" :key="index">
            <tr v-if="index===1 && group.length"><th class="divider" colspan="9">{{ words('Отключившиеся пилоты','Disconnected drivers') }}</th></tr>
            <tr v-if="index===0 && !group.length"><td colspan="9">{{ words('На трассе пока нет пилотов','No drivers connected') }}</td></tr>
            <tr v-for="d in group" :key="d.name+'-'+d.slot" :class="{connected:d.online}">
              <td>{{ d.online ? d.position : '—' }}</td><td><strong>{{ d.name }}</strong><small>{{ d.car }}</small></td><td>{{ d.laps }}</td>
              <td v-for="(s,i) in d[mode]" :key="i" :class="sectorClass(d, s, i)">{{ s>0 ? (s/1000).toFixed(3) : '—' }}</td>
              <td>{{ time(d.last) }}</td><td :class="{record:d.best>0 && record?.best===d.best}">{{ time(d.best) }}</td><td :class="{pitText:d.online && d.pit}">{{ status(d) }}</td>
            </tr>
          </tbody>
        </table></div>
      </section>
      <small v-reveal="{ delay: 600, y: 8 }" class="updated">{{ words('Обновлено','Updated') }} {{ new Date(timing.updated*1000).toLocaleTimeString(locale) }}</small>
    </template>
  </section>
</template>
<style scoped>
.live {max-width:1400px;margin:24px auto 48px;padding:0 var(--gutter);color:var(--c-text)}
.line,.metrics,.modes,.mapcard {display:flex;align-items:center;gap:14px}
.line,.mapcard {justify-content:space-between}
.line h1 {font-size:clamp(30px,4vw,48px);margin:0}
header.line {margin-bottom:16px}
header span,.live small,.metrics {font-size:13px;color:var(--c-text-2)}
.cards {display:grid;grid-template-columns:0.94fr 1.28fr;gap:16px;margin-bottom:18px}
.summary,.mapcard,.board {border:1px solid var(--c-line-strong);border-radius:20px;background:var(--c-surface-solid);overflow:hidden}
.summary,.mapcard {padding:22px 28px}
.summary,.mapcard {background:linear-gradient(110deg,var(--c-surface-solid),var(--c-blue-soft))}
.summary {display:flex;flex-direction:column;justify-content:space-between;gap:32px}
.ey,.layout,th {font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--c-text-2)}
.ey span {margin-left:10px;border:1px solid var(--c-line-strong);border-radius:7px;padding:3px 8px;letter-spacing:0}
.track {text-transform:capitalize;margin:10px 0 2px;font-size:clamp(30px,4vw,48px)}
.metrics {display:grid;grid-template-columns:1fr 1fr;gap:20px 24px;align-items:start}
.metrics div {border-left:1px solid var(--c-line-strong);padding-left:14px}
.metrics .best-lap {grid-column:1 / -1}
.metrics .session-clock {grid-column:1 / -1}
.metrics strong {display:block;font:600 clamp(20px,1.6vw,24px)/1.35 var(--font-mono);color:var(--c-text)}
.metrics .best-lap strong {font-size:clamp(30px,3vw,42px)}
.live .record {color:var(--c-accent-text)}
:root[data-theme=dark] .live .record {color:#c9aaff}
.mapcard {position:relative;justify-content:center;padding-top:68px;padding-bottom:80px}
.map-location,.map-weather {position:absolute;top:24px;display:flex;align-items:center;gap:7px;color:var(--c-text-2);font-size:13px;line-height:1.35}
.map-location {left:28px;max-width:43%}
.map-weather {right:28px;max-width:43%;text-align:right;justify-content:flex-end}
.map-location svg,.map-weather svg {flex:none;color:var(--c-accent-text)}
.map-temperatures {position:absolute;left:28px;right:28px;bottom:20px;display:flex;justify-content:flex-start;gap:32px;color:var(--c-text-2);font-size:13px}
.map-temperatures div {border-left:1px solid var(--c-line-strong);padding-left:14px}
.map-temperatures strong {display:block;color:var(--c-text);font:600 22px/1.35 var(--font-mono)}
.outline {position:relative;width:min(100%,400px);flex:none}
.outline::before {content:'';position:absolute;inset:-12%;z-index:0;pointer-events:none;background:radial-gradient(ellipse,rgba(3,8,20,.48),transparent 70%)}
.outline img {position:relative}
.outline img {width:100%;display:block}.dot {position:absolute;transform:translate(-50%,-50%);transition:left .4s linear,top .4s linear;border:2px solid #102034;background:#78baff;color:#091422;border-radius:100px;min-width:21px;padding:1px 3px;text-align:center;font:700 12px/16px var(--font-mono)}.dot.pit {background:#ffc66c}
.boardhead {padding:18px 24px;flex-wrap:wrap}.boardhead h2 {margin:0;font-size:22px}
.modes {gap:14px}
.scroll {overflow-x:auto}.live table {width:100%;min-width:890px;border-collapse:collapse;text-align:left}
th,td {padding:13px 10px;border-top:1px solid var(--c-line);white-space:nowrap}
th:first-child,td:first-child {padding-left:24px}th {text-align:left;font-size:11px}.divider,thead {background:var(--c-surface-2)}
td {font:500 15px var(--font-mono)}td:nth-child(2),td:last-child {font:14px var(--font-body)}td small {display:block}
.live .personal-sector {color:#16834b}
:root[data-theme=dark] .live .personal-sector {color:#5de39a}
.connected {background:var(--c-blue-soft)}.connected td:first-child {box-shadow:inset 3px 0 var(--bm-blue-bright)}
.pitText {color:var(--c-accent-text)}.updated {display:block;margin-top:12px}
@media(max-width:850px){.cards{grid-template-columns:1fr}.metrics{gap:12px}.mapcard,.summary{padding:18px}.mapcard{padding-top:74px;padding-bottom:76px}.map-location{left:18px;top:20px}.map-weather{right:18px;top:20px}.map-temperatures{left:18px;right:18px;bottom:16px}.boardhead{padding:14px}.modes{flex-wrap:wrap}}
@media(prefers-reduced-motion:reduce){.dot{transition:none}}
</style>
