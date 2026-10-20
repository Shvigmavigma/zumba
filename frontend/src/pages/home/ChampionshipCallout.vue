<script setup>
// A championship on the home page: open registration, or a season under way.
// Beside the name runs the season's route: one stop per round (driven, live or
// next, still ahead) with its track and date, and the circuit of the round to
// look forward to is drawn in ink behind it. Open registration gets a
// travelling border beam (the thing to act on); a running season shows who
// leads it and by how much.
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowRight, Flag, Trophy } from 'lucide-vue-next'
import UserAvatar from '../../components/UserAvatar.vue'
import { pilotName } from '../../pilotDisplay'
import { loadRaceAssets, trackImageFor } from '../../raceDisplay'
import { formatInTimeZone } from '../../timezone'
import { state } from '../../store'
import { rankStandings, seasonProgress } from '../championships/helpers'

// Past these many rounds the stops drop their track names, then their dates.
const ROOMY_ROUNDS = 5
const DENSE_ROUNDS = 9

const props = defineProps({
  championship: { type: Object, required: true }
})

const { t } = useI18n()
const assets = ref(null)

const season = computed(() => seasonProgress(props.championship.stages || []))
const stageCount = computed(() => props.championship.stage_count ?? season.value.total)
const registered = computed(() => props.championship.my_registration_status === 'approved')
const isOpen = computed(() => props.championship.status === 'registration_open')
const ranked = computed(() => rankStandings(props.championship.standings || []))
/** Who leads once anybody has scored, and by how much over the second. */
const leader = computed(() => {
  const [first, second] = ranked.value
  if (!first || !(Number(first.points) > 0)) return null
  return { pilot: first, name: pilotName(first, first.login), points: Number(first.points), lead: second ? second.gap : null }
})
const pilots = computed(() => Number(props.championship.participant_count) || 0)
const stops = computed(() => season.value.stages.map(({ stage, round, phase }) => {
  const track = stage.track || stage.name || ''
  const date = stage.datetime_start ? shortDate(stage.datetime_start) : ''
  return { id: stage.id, round, phase, track, date, title: [`R${round}`, track, date].filter(Boolean).join(' · ') }
}))
const density = computed(() => {
  if (stops.value.length > DENSE_ROUNDS) return 'is-packed'
  return stops.value.length > ROOMY_ROUNDS ? 'is-dense' : ''
})
/** The round to look forward to: live or next, or the last one once all are driven. */
const focusStage = computed(() => season.value.current || season.value.stages.at(-1)?.stage || null)
const art = computed(() => {
  const stage = focusStage.value
  return stage ? trackImageFor(assets.value, { game: stage.game || props.championship.game, track: stage.track }) : ''
})

function shortDate(value) {
  return formatInTimeZone(value, { day: '2-digit', month: '2-digit' })
}

function stageWord(count) {
  if (state.locale !== 'ru') return t(count === 1 ? 'championships.stageWordOne' : 'championships.stageWordMany')
  const mod10 = count % 10
  const mod100 = count % 100
  if (mod10 === 1 && mod100 !== 11) return t('championships.stageWordOne')
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return t('championships.stageWordFew')
  return t('championships.stageWordMany')
}

onMounted(async () => {
  try {
    assets.value = await loadRaceAssets()
  } catch {
    // The circuit is decoration: the card is complete without it.
    assets.value = null
  }
})
</script>

<template>
  <RouterLink class="champ ui-glass" :class="{ 'ui-beam': isOpen, 'has-route': stops.length, 'is-live': !isOpen }" to="/championships">
    <span class="champ__bg" aria-hidden="true">
      <span class="champ__hatch"></span>
      <span class="champ__glow"></span>
      <img v-if="art" :key="art" v-track-art class="champ__art ui-ink" :src="art" alt="" />
    </span>

    <span class="champ__icon"><Flag :size="20" /></span>
    <span class="champ__text">
      <span class="ui-eyebrow ui-eyebrow--accent">{{ isOpen ? t('main.championshipOpen') : t('home.championship.live') }}</span>
      <strong class="champ__name">{{ championship.name }}</strong>
      <span class="champ__meta">
        <span class="ui-chip ui-chip--solid">{{ championship.game }}</span>
        <span v-if="isOpen" class="ui-chip">{{ stageCount }} {{ stageWord(stageCount) }}</span>
        <span v-else class="ui-chip ui-num">{{ t('home.championship.driven', { done: season.finished, total: stageCount }) }}</span>
        <span v-if="pilots" class="ui-chip">{{ t('home.championship.pilots', { count: pilots }) }}</span>
        <span v-if="isOpen && championship.registration_end" class="ui-chip">{{ t('home.next.closes') }} · {{ shortDate(championship.registration_end) }}</span>
        <span v-if="registered" class="ui-chip ui-chip--green">{{ t('championships.requestApproved') }}</span>
      </span>
    </span>

    <ol v-if="stops.length" class="champ__route" :class="density" :aria-label="t('home.championship.route')">
      <li v-for="stop in stops" :key="stop.id" class="stop" :class="`is-${stop.phase}`" :title="stop.title">
        <span class="stop__dot"></span>
        <span class="stop__round ui-num">R{{ stop.round }}</span>
        <span class="stop__track">{{ stop.track }}</span>
        <span class="stop__date ui-num">{{ stop.date }}</span>
      </li>
    </ol>

    <span v-if="!isOpen && leader" class="champ__leader">
      <span class="champ__leader-label"><Trophy :size="13" />{{ t('home.championship.leader') }}</span>
      <span class="champ__leader-who">
        <UserAvatar mini :src="leader.pilot.avatar_url" :color="leader.pilot.avatar_color" :label="leader.name" />
        <strong>{{ leader.name }}</strong>
      </span>
      <span class="champ__leader-score ui-num">
        {{ leader.points }} {{ t('champPage.standings.pts') }}
        <small v-if="leader.lead !== null">{{ t('home.championship.lead', { points: leader.lead }) }}</small>
      </span>
    </span>
    <span class="champ__cta">{{ isOpen ? t('home.championship.cta') : t('home.championship.table') }}<ArrowRight :size="16" /></span>
  </RouterLink>
</template>

<style scoped>
.champ {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 18px clamp(16px, 2vw, 28px);
  min-height: 116px;
  padding: 18px clamp(18px, 2vw, 26px);
  border-radius: var(--r-xl);
  color: var(--c-text);
  text-decoration: none;
  transition: transform var(--dur-3) var(--ease-ios);
}

.champ.has-route {
  grid-template-columns: auto minmax(280px, 1fr) minmax(0, 1.1fr) auto;
}

/* A running season: the leader sits between the route and the way in. */
.champ.is-live.has-route {
  grid-template-columns: auto minmax(240px, 1fr) minmax(0, 1fr) auto auto;
}

.champ.is-live:not(.has-route) {
  grid-template-columns: auto minmax(0, 1fr) auto auto;
}

.champ:hover {
  transform: translateY(-2px);
}

.champ > :not(.champ__bg) {
  position: relative;
}

/* ---------- Backdrop: speed hatch, a glow and the circuit in ink ---------- */
/* Clipped here, not on the card: the border beam sits one pixel outside it. */
.champ__bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
  border-radius: inherit;
  pointer-events: none;
}

.champ__hatch {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(115deg, transparent 0 20px, color-mix(in srgb, var(--c-text) 5%, transparent) 20px 21px);
  -webkit-mask-image: linear-gradient(90deg, transparent 20%, #000 60%);
  mask-image: linear-gradient(90deg, transparent 20%, #000 60%);
}

.champ__glow {
  position: absolute;
  top: -70%;
  right: 4%;
  width: 48%;
  height: 240%;
  background: radial-gradient(closest-side, color-mix(in srgb, var(--bm-blue) 24%, transparent), transparent);
  transition: opacity var(--dur-3) var(--ease-out);
}

.champ__art {
  position: absolute;
  top: 50%;
  right: clamp(110px, 11vw, 180px);
  width: clamp(240px, 26vw, 400px);
  height: 210%;
  object-fit: contain;
  opacity: 0.26;
  transform: translateY(-50%) rotate(-8deg);
  transition: transform 900ms var(--ease-out), opacity var(--dur-3) var(--ease-out);
}

.champ:hover .champ__art {
  opacity: 0.4;
  transform: translateY(-50%) rotate(-8deg) scale(1.06);
}

/* ---------- Name and facts ---------- */
.champ__icon {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: 15px;
  background: var(--bm-blue);
  color: #fff;
  box-shadow: var(--shadow-blue);
}

.champ__text {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.champ__name {
  /* Up to two lines: a championship's full name matters more than a tidy row. */
  display: -webkit-box;
  overflow: hidden;
  font-family: var(--font-display);
  font-size: clamp(15px, 1.6vw, 19px);
  font-weight: 700;
  line-height: 1.2;
  overflow-wrap: anywhere;
  text-transform: uppercase;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

.champ__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

/* ---------- The season's route ---------- */
.champ__route {
  display: grid;
  grid-auto-columns: minmax(0, 1fr);
  grid-auto-flow: column;
  min-width: 0;
  margin: 0;
  padding: 0;
  list-style: none;
  /* The road runs on past the first and the last stop and fades out. */
  -webkit-mask-image: linear-gradient(90deg, transparent, #000 10%, #000 90%, transparent);
  mask-image: linear-gradient(90deg, transparent, #000 10%, #000 90%, transparent);
}

.stop {
  position: relative;
  display: grid;
  justify-items: center;
  gap: 2px;
  min-width: 0;
  text-align: center;
}

/* The road: half a segment on either side of the dot, dashed until driven. */
.stop::before,
.stop::after {
  position: absolute;
  top: 6px;
  width: 50%;
  height: 2px;
  background: repeating-linear-gradient(90deg, var(--c-line-strong) 0 6px, transparent 6px 11px);
  content: '';
}

.stop::before {
  left: 0;
}

.stop::after {
  right: 0;
}

.stop.is-done::before,
.stop.is-done::after,
.stop.is-live::before,
.stop.is-next::before {
  background: var(--bm-blue-bright);
}

.stop__dot {
  position: relative;
  z-index: 1;
  width: 14px;
  height: 14px;
  margin-bottom: 6px;
  border: 2px solid var(--c-text-3);
  border-radius: 50%;
  background: var(--c-surface-solid);
}

.stop.is-done .stop__dot,
.stop.is-live .stop__dot,
.stop.is-next .stop__dot {
  border-color: var(--bm-blue-bright);
  background: var(--bm-blue-bright);
}

/* The round to look forward to beats. */
.stop.is-live .stop__dot::after,
.stop.is-next .stop__dot::after {
  position: absolute;
  inset: -2px;
  border-radius: 50%;
  background: var(--bm-blue-bright);
  content: '';
  animation: champ-beat 2.4s var(--ease-out) infinite;
}

@keyframes champ-beat {
  0% {
    opacity: 0.6;
    transform: scale(1);
  }
  70%,
  100% {
    opacity: 0;
    transform: scale(3);
  }
}

.stop__round {
  color: var(--c-text-2);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.stop__track {
  max-width: 100%;
  padding-inline: 6px;
  overflow: hidden;
  color: var(--c-text-2);
  font-size: 12.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stop__date {
  color: var(--c-text-3);
  font-size: 11.5px;
}

.stop.is-live .stop__round,
.stop.is-next .stop__round {
  color: var(--c-accent-text);
}

.stop.is-live .stop__track,
.stop.is-next .stop__track {
  color: var(--c-text);
  font-weight: 600;
}

.champ__route.is-dense .stop__track,
.champ__route.is-packed .stop__track,
.champ__route.is-packed .stop__date {
  display: none;
}

/* ---------- Who leads ---------- */
/* Solid, so the circuit drawn behind the plate does not run through the leader's name. */
.champ__leader {
  display: grid;
  gap: 5px;
  min-width: 0;
  padding: 10px 14px;
  border: 1px solid color-mix(in srgb, var(--bm-gold) 46%, var(--c-line));
  border-radius: var(--r-lg);
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--bm-gold) 16%, transparent), transparent 72%),
    var(--c-surface-solid);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.28), inset 0 1px 0 color-mix(in srgb, var(--bm-gold) 22%, transparent);
}

.champ__leader-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: color-mix(in srgb, var(--bm-gold) 80%, var(--c-text));
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.champ__leader-who {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.champ__leader-who strong {
  max-width: 16ch;
  overflow: hidden;
  font-size: 14px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.champ__leader-score {
  color: var(--c-text);
  font-size: 13px;
  font-weight: 700;
}

.champ__leader-score small {
  margin-left: 6px;
  color: var(--c-text-2);
  font-size: 11.5px;
  font-weight: 600;
}

.champ__cta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--c-accent-text);
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  transition: gap var(--dur-2) var(--ease-ios);
}

.champ:hover .champ__cta {
  gap: 12px;
}

@media (max-width: 1000px) {
  .champ,
  .champ.has-route,
  .champ.is-live.has-route,
  .champ.is-live:not(.has-route) {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .champ__route,
  .champ__leader,
  .champ__cta {
    grid-column: 1 / -1;
  }

  .champ__leader {
    justify-self: start;
  }

  .champ__art {
    top: 0;
    right: -30px;
    width: 240px;
    height: 130px;
    transform: rotate(-8deg);
  }

  .champ:hover .champ__art {
    transform: rotate(-8deg) scale(1.06);
  }
}

@media (prefers-reduced-motion: reduce) {
  .champ,
  .champ__art {
    transition: none;
  }

  .stop.is-live .stop__dot::after,
  .stop.is-next .stop__dot::after {
    animation: none;
    opacity: 0;
  }
}
</style>
