<script setup>
// Live preview of the pilot licence while registering: fills in as the pilot
// types, tilts with a holographic glare (React Bits "ProfileCard" idea).
// Like a driving licence it carries security foil (LicenceFoil); a new pilot
// starts on the rookie finish that profile licences grow out of.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { BadgeCheck, CircleDashed } from 'lucide-vue-next'
import { brandingSettings } from '../../brandingSettings'
import LicenceFoil from '../../components/licence/LicenceFoil.vue'
import { countryLabel } from '../../i18nLabels'

const props = defineProps({
  form: { type: Object, required: true },
  steamConnected: { type: Boolean, default: false }
})

const { t } = useI18n()
const name = computed(() => [props.form.first_name, props.form.last_name].map((part) => String(part || '').trim()).filter(Boolean).join(' '))
const number = computed(() => (/^\d{1,3}$/.test(String(props.form.pilot_number || '')) ? String(props.form.pilot_number).padStart(3, '0') : '000'))
const initials = computed(() => {
  const source = name.value || String(props.form.nickname || '').trim()
  if (!source) return 'BM'
  return source.split(/\s+/).map((part) => part[0]).join('').slice(0, 2).toUpperCase()
})
</script>

<template>
  <article v-tilt="10" class="licence" :style="{ '--accent': form.avatar_color || '#1652d8' }">
    <span class="ui-glare" aria-hidden="true"></span>
    <span class="licence__holo" aria-hidden="true"></span>
    <LicenceFoil rank="rookie" />
    <header class="licence__head">
      <img class="licence__logo" :src="brandingSettings.dark_logo_url" alt="BMRL" />
      <span class="licence__kind">{{ t('authPage.register.preview.eyebrow') }}</span>
    </header>

    <div class="licence__body">
      <span class="licence__avatar">{{ initials }}</span>
      <div class="licence__who">
        <strong :class="{ 'is-empty': !name }">{{ name || t('authPage.register.preview.name') }}</strong>
        <span :class="{ 'is-empty': !form.nickname }">{{ form.nickname || t('authPage.register.preview.nickname') }}</span>
        <span v-if="form.country" class="licence__country">{{ countryLabel(t, form.country) }}</span>
      </div>
      <div class="licence__plate" :aria-label="t('authPage.register.preview.number')">
        <small>{{ t('authPage.register.preview.number') }}</small>
        <b class="ui-num">#{{ number }}</b>
      </div>
    </div>

    <footer class="licence__foot">
      <span class="licence__games">
        <span v-for="game in form.games" :key="game" class="licence__game">{{ game }}</span>
      </span>
      <span class="licence__steam" :class="{ 'is-ok': steamConnected }">
        <BadgeCheck v-if="steamConnected" :size="15" />
        <CircleDashed v-else :size="15" />
        {{ steamConnected ? t('authPage.register.preview.steamOk') : t('authPage.register.preview.steamMissing') }}
      </span>
    </footer>
  </article>
</template>

<style scoped>
.licence {
  position: relative;
  display: grid;
  gap: 22px;
  width: min(460px, 100%);
  padding: 22px;
  overflow: hidden;
  isolation: isolate;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 24px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--accent) 30%, #0b1324), #060a13 65%),
    #060a13;
  box-shadow: 0 30px 70px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.12);
  color: #fff;
}

.licence::after {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, var(--bm-blue), var(--bm-cyan));
  content: '';
}

/* Iridescent foil that shifts with the tilt glare position. */
.licence__holo {
  position: absolute;
  inset: 0;
  z-index: -1;
  background: linear-gradient(115deg, transparent 20%, rgba(79, 216, 234, 0.16) 40%, rgba(124, 92, 255, 0.14) 50%, rgba(22, 82, 216, 0.16) 60%, transparent 80%) var(--gx, 50%) var(--gy, 50%) / 250% 250%;
  mix-blend-mode: screen;
  opacity: calc(0.35 + var(--glare, 0) * 0.65);
  transition: opacity 400ms var(--ease-out);
}

.licence__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.licence__logo {
  height: 22px;
  width: auto;
}

.licence__kind {
  color: rgba(255, 255, 255, 0.6);
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.16em;
  text-align: right;
  text-transform: uppercase;
}

.licence__body {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 16px;
}

.licence__avatar {
  display: grid;
  place-items: center;
  width: 64px;
  height: 64px;
  border: 2px solid rgba(255, 255, 255, 0.85);
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.08), 0 0 30px color-mix(in srgb, var(--accent) 60%, transparent);
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 800;
}

.licence__who {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.licence__who strong {
  overflow: hidden;
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 800;
  line-height: 1.1;
  text-overflow: ellipsis;
  text-transform: uppercase;
  white-space: nowrap;
}

.licence__who span {
  overflow: hidden;
  color: rgba(255, 255, 255, 0.72);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.licence__who .is-empty {
  color: rgba(255, 255, 255, 0.32);
}

.licence__country {
  font-family: var(--font-mono);
  font-size: 11px !important;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.licence__plate {
  display: grid;
  justify-items: center;
  gap: 2px;
  padding: 8px 12px;
  border-radius: 12px;
  background: #fff;
  color: #05070d;
}

.licence__plate small {
  font-family: var(--font-mono);
  font-size: 8.5px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.licence__plate b {
  font-size: 24px;
  font-weight: 700;
  line-height: 1;
}

.licence__foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-top: 14px;
  border-top: 1px dashed rgba(255, 255, 255, 0.16);
}

.licence__games {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.licence__game {
  padding: 3px 8px;
  border-radius: 6px;
  background: var(--bm-blue);
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 700;
}

.licence__steam {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
}

.licence__steam.is-ok {
  color: #4ade80;
}
</style>
