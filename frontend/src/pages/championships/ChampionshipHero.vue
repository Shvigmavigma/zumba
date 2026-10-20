<script setup>
// Featured view of the selected championship: track artwork of the current
// stage, name, rules, the season schedule as tiles, the stage gantry and key
// numbers. The registration ticket is passed in through the #aside slot.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { CheckCircle2, PlayCircle, Settings2 } from 'lucide-vue-next'
import CountUp from '../../ui/fx/CountUp.vue'
import RacingLines from '../../ui/fx/RacingLines.vue'
import { trackImageFor } from '../../raceDisplay'
import { pilotName } from '../../pilotDisplay'
import { formatInTimeZone } from '../../timezone'
import SeasonTrack from './SeasonTrack.vue'
import { safeHttpUrl } from '../../safeUrl'
import { cleanText, scoringLabel, seasonProgress, statusKey, statusTone } from './helpers'

const props = defineProps({
  championship: { type: Object, required: true },
  assets: { type: Object, default: null },
  canManage: { type: Boolean, default: false }
})
const emit = defineEmits(['manage'])

const DESCRIPTION_CLAMP = 260
const { t } = useI18n()
const expanded = ref(false)
const now = Date.now()

const season = computed(() => seasonProgress(props.championship.stages || []))
const description = computed(() => cleanText(props.championship.description))
const isLong = computed(() => description.value.length > DESCRIPTION_CLAMP)
const tone = computed(() => statusTone(props.championship.status))
const leader = computed(() => props.championship.standings?.[0] || null)

/** Artwork of the current stage, otherwise of any stage that has one. */
const image = computed(() => {
  const candidates = [season.value.current, ...season.value.stages.map((item) => item.stage)].filter(Boolean)
  for (const stage of candidates) {
    const url = trackImageFor(props.assets, { game: stage.game || props.championship.game, track: stage.track })
    if (url) return url
  }
  return ''
})

const schedule = computed(() => {
  const items = [
    { key: 'regStart', label: t('fields.registrationStart'), value: props.championship.registration_start },
    { key: 'regEnd', label: t('fields.registrationEnd'), value: props.championship.registration_end },
    { key: 'start', label: t('championships.championshipStart'), value: props.championship.championship_start },
    { key: 'end', label: t('championships.championshipEnd'), value: props.championship.championship_end }
  ].map((item) => ({ ...item, passed: new Date(item.value).getTime() < now }))
  const nextIndex = items.findIndex((item) => !item.passed)
  return items.map((item, index) => ({ ...item, isNext: index === nextIndex }))
})

function day(value) {
  return formatInTimeZone(value, { day: 'numeric', month: 'short' }).replace('.', '')
}

function yearTime(value) {
  return formatInTimeZone(value, { year: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <article v-spotlight class="hero ui-glass">
    <div class="hero__media" aria-hidden="true">
      <img v-if="image" v-track-art class="hero__image" :src="image" alt="" />
      <div v-else class="hero__image hero__image--fallback"><RacingLines :count="12" /></div>
    </div>
    <div class="hero__shade" aria-hidden="true"></div>

    <div class="hero__body">
      <div class="hero__main">
        <header class="hero__head">
          <span class="ui-chip ui-chip--solid">{{ championship.game }}</span>
          <span class="ui-chip hero__status">
            <span class="ui-dot" :class="[tone ? `ui-dot--${tone}` : '', { 'ui-dot--live': championship.status === 'registration_open' || championship.status === 'active' }]"></span>
            {{ statusKey(championship.status) ? t(statusKey(championship.status)) : championship.status }}
          </span>
          <span v-if="championship.is_team_event" class="ui-chip">{{ t('champPage.team') }}</span>
          <span v-if="!championship.is_published" class="ui-chip ui-chip--amber">{{ t('champPage.unpublished') }}</span>
        </header>

        <h2 v-split class="hero__title ui-display">{{ championship.name }}</h2>

        <div class="hero__about">
          <p class="hero__desc" :class="{ 'is-clamped': isLong && !expanded }">{{ description || t('championships.noDescription') }}</p>
          <button v-if="isLong" class="hero__more ui-link" type="button" :aria-expanded="expanded" @click="expanded = !expanded">
            {{ expanded ? t('champPage.hero.less') : t('champPage.hero.more') }}
          </button>
        </div>

        <ul class="hero__tags" :aria-label="t('champPage.hero.rules')">
          <li v-for="name in championship.classes" :key="name"><span class="ui-chip ui-chip--blue">{{ name }}</span></li>
          <li><span class="ui-chip">{{ t('champPage.hero.scoring', { system: scoringLabel(championship.scoring_system) }) }}</span></li>
          <li v-if="championship.pole_bonus_enabled"><span class="ui-chip">{{ t('championships.poleBonus') }}</span></li>
          <li v-if="championship.car_change_allowed"><span class="ui-chip">{{ t('championships.carCanChange') }}</span></li>
        </ul>

        <ol class="hero__schedule">
          <li
            v-for="(item, index) in schedule"
            :key="item.key"
            v-reveal="{ delay: 120 + index * 70, y: 10, blur: 4 }"
            class="hero__slot"
            :class="{ 'is-passed': item.passed, 'is-next': item.isNext }"
          >
            <span class="hero__slot-label">{{ item.label }}</span>
            <strong class="ui-num">{{ day(item.value) }}</strong>
            <span class="hero__slot-sub ui-num">
              <CheckCircle2 v-if="item.passed" :size="12" aria-hidden="true" />{{ yearTime(item.value) }}
            </span>
          </li>
        </ol>

        <SeasonTrack class="hero__season" :stages="championship.stages || []" />

        <dl class="hero__stats">
          <div class="hero__stat">
            <dt>{{ t('fields.participants') }}</dt>
            <dd><CountUp :value="championship.participant_count || 0" /></dd>
          </div>
          <div class="hero__stat">
            <dt>{{ t('champPage.hero.pending') }}</dt>
            <dd><CountUp :value="championship.pending_count || 0" /></dd>
          </div>
          <div class="hero__stat">
            <dt>{{ t('championships.stages') }}</dt>
            <dd class="ui-num">{{ season.finished }}<small> / {{ season.total }}</small></dd>
          </div>
          <div class="hero__stat hero__stat--leader">
            <dt>{{ t('champPage.hero.leader') }}</dt>
            <dd v-if="leader">
              <RouterLink :to="`/pilots/${leader.user_id}`">{{ pilotName(leader, leader.login) }}</RouterLink>
              <small class="ui-num">{{ t('champPage.hero.points', { points: leader.points }) }}</small>
            </dd>
            <dd v-else class="hero__stat-empty">{{ t('champPage.hero.noLeader') }}</dd>
          </div>
        </dl>

        <footer v-if="championship.video_url || canManage" class="hero__actions">
          <a v-if="safeHttpUrl(championship.video_url)" class="ui-btn ui-btn--outline" :href="safeHttpUrl(championship.video_url)" target="_blank" rel="noreferrer">
            <PlayCircle :size="17" />{{ t('championships.video') }}
          </a>
          <button v-if="canManage" class="ui-btn ui-btn--ghost" type="button" @click="emit('manage')">
            <Settings2 :size="17" />{{ t('champPage.manage.title') }}
            <span v-if="championship.pending_count" class="hero__badge ui-num">{{ championship.pending_count }}</span>
          </button>
        </footer>
      </div>

      <aside class="hero__aside">
        <slot name="aside" />
      </aside>
    </div>
  </article>
</template>

<style scoped>
.hero {
  position: relative;
  overflow: hidden;
  /* clip (unlike hidden) is not a scroll container, so the ticket can stay sticky. */
  overflow: clip;
  border-radius: var(--r-xl);
}

.hero__media {
  position: absolute;
  inset: 0 0 0 28%;
  z-index: 0;
  overflow: hidden;
  -webkit-mask-image: linear-gradient(90deg, transparent 0%, #000 42%);
  mask-image: linear-gradient(90deg, transparent 0%, #000 42%);
}

.hero__image {
  position: relative;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.6;
  animation: hero-drift 26s var(--ease-out) infinite alternate;
}

.hero__image--fallback {
  opacity: 1;
  background:
    radial-gradient(48% 60% at 72% 30%, color-mix(in srgb, var(--bm-blue) 42%, transparent), transparent 70%),
    radial-gradient(30% 40% at 90% 90%, color-mix(in srgb, var(--bm-cyan) 14%, transparent), transparent 70%),
    repeating-linear-gradient(115deg, transparent 0 22px, color-mix(in srgb, var(--c-text) 4%, transparent) 22px 23px);
}

:root[data-theme='light'] .hero__image {
  opacity: 0.28;
}

:root[data-theme='light'] .hero__image--fallback {
  opacity: 0.9;
}

.hero__shade {
  position: absolute;
  inset: 0;
  z-index: 0;
  background: linear-gradient(90deg, color-mix(in srgb, var(--c-bg) 72%, transparent) 0%, color-mix(in srgb, var(--c-bg) 38%, transparent) 55%, color-mix(in srgb, var(--c-bg) 10%, transparent) 100%);
  pointer-events: none;
}

@keyframes hero-drift {
  from {
    transform: scale(1.04) translate3d(0, 0, 0);
  }
  to {
    transform: scale(1.12) translate3d(-2%, -1%, 0);
  }
}

.hero__body {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 400px);
  gap: clamp(20px, 3vw, 40px);
  align-items: start;
  padding: clamp(20px, 3.2vw, 40px);
}

.hero__main {
  display: grid;
  align-content: start;
  gap: 18px;
  min-width: 0;
}

.hero__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.hero__status {
  --chip-bg: color-mix(in srgb, var(--c-bg) 50%, transparent);
  --chip-fg: var(--c-text);
}

.hero__title {
  max-width: 18ch;
  color: var(--c-text);
  font-size: clamp(30px, 4.6vw, 64px);
  overflow-wrap: anywhere;
  text-wrap: balance;
}

.hero__about {
  display: grid;
  justify-items: start;
  gap: 6px;
  max-width: 66ch;
}

.hero__desc {
  margin: 0;
  color: var(--c-text-2);
  font-size: 15.5px;
  line-height: 1.6;
  white-space: pre-line;
}

.hero__desc.is-clamped {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
}

.hero__more {
  padding: 0;
  border: 0;
  background: none;
  cursor: pointer;
  font-size: 13.5px;
}

.hero__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.hero__schedule {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.hero__slot {
  display: grid;
  align-content: start;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-md);
  background: color-mix(in srgb, var(--c-bg) 45%, transparent);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  transition: border-color var(--dur-2), transform var(--dur-3) var(--ease-ios);
}

.hero__slot:hover {
  transform: translateY(-2px);
}

.hero__slot.is-next {
  border-color: var(--c-blue-line);
  background: color-mix(in srgb, var(--bm-blue) 16%, color-mix(in srgb, var(--c-bg) 50%, transparent));
  box-shadow: 0 10px 30px color-mix(in srgb, var(--bm-blue) 18%, transparent);
}

.hero__slot.is-passed {
  opacity: 0.6;
}

.hero__slot-label {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  line-height: 1.35;
  text-transform: uppercase;
}

.hero__slot.is-next .hero__slot-label {
  color: var(--c-accent-text);
}

.hero__slot strong {
  color: var(--c-text);
  font-size: 19px;
  font-weight: 600;
}

.hero__slot-sub {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--c-text-3);
  font-size: 11.5px;
}

.hero__season {
  padding: 16px 18px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-lg);
  background: color-mix(in srgb, var(--c-bg) 40%, transparent);
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
}

.hero__stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 0.7fr)) minmax(0, 1.4fr);
  gap: 1px;
  margin: 0;
  overflow: hidden;
  border: 1px solid var(--c-line);
  border-radius: var(--r-lg);
  background: var(--c-line);
}

.hero__stat {
  display: grid;
  align-content: start;
  gap: 6px;
  min-width: 0;
  padding: 12px 16px;
  background: color-mix(in srgb, var(--c-surface-solid) 82%, transparent);
}

.hero__stat dt {
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.hero__stat dd {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 10px;
  min-width: 0;
  margin: 0;
  color: var(--c-text);
  font-size: 24px;
  font-weight: 600;
  line-height: 1.1;
}

.hero__stat dd small {
  color: var(--c-text-3);
  font-size: 13px;
  font-weight: 500;
}

.hero__stat--leader dd {
  font-size: 15px;
}

.hero__stat--leader a {
  overflow: hidden;
  color: var(--c-text);
  font-weight: 650;
  text-decoration: none;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hero__stat--leader a:hover {
  color: var(--c-accent-text);
}

.hero__stat-empty {
  color: var(--c-text-3) !important;
  font-size: 13.5px !important;
  font-weight: 500 !important;
}

.hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.hero__badge {
  display: inline-grid;
  place-items: center;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: var(--r-pill);
  background: var(--bm-red);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
}

.hero__aside {
  position: sticky;
  top: calc(var(--header-h) + 16px);
  min-width: 0;
}

@media (max-width: 1180px) {
  /* One column: the ticket moves up, right after the name and rules. */
  .hero__body {
    grid-template-columns: minmax(0, 1fr);
    gap: 18px;
  }

  .hero__main {
    display: contents;
  }

  .hero__aside {
    position: static;
    order: 1;
  }

  .hero__schedule,
  .hero__season,
  .hero__stats,
  .hero__actions {
    order: 2;
  }

  .hero__media {
    inset: 0 0 40% 0;
    -webkit-mask-image: linear-gradient(180deg, #000 20%, transparent);
    mask-image: linear-gradient(180deg, #000 20%, transparent);
  }

  .hero__shade {
    background: linear-gradient(180deg, color-mix(in srgb, var(--c-bg) 20%, transparent) 0%, color-mix(in srgb, var(--c-bg) 55%, transparent) 40%, color-mix(in srgb, var(--c-bg) 70%, transparent) 100%);
  }
}

@media (max-width: 860px) {
  .hero__schedule {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .hero__stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .hero__stat--leader {
    grid-column: 1 / -1;
  }
}

@media (max-width: 520px) {
  .hero__stat {
    padding: 10px 12px;
  }

  .hero__stat dd {
    font-size: 20px;
  }

  .hero__slot strong {
    font-size: 16px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero__image {
    animation: none;
  }
}
</style>
