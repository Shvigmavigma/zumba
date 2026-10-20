<script setup>
// Site footer: community links, direct contacts and project support with the
// top donations, available on every page.
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowUpRight, HeartHandshake, Mail, MessageCircle, Music2, Radio, Scale, Send, Users } from 'lucide-vue-next'
import { api } from '../api'
import { brandingSettings } from '../brandingSettings'
import { safeHttpUrl } from '../safeUrl'
import StartLights from '../ui/fx/StartLights.vue'

const { t } = useI18n()
const donations = ref({ donation_url: '', top_donations: [] })
const year = new Date().getFullYear()

const topDonations = computed(() => (donations.value.top_donations || [])
  .filter((donation) => donation?.name || donation?.amount)
  .slice(0, 3))

const socials = computed(() => [
  { key: 'discord', icon: Users, label: t('main.discordServer'), href: 'https://discord.gg/bmrlac', text: 'discord.gg/bmrlac' },
  { key: 'telegram', icon: Send, label: t('main.telegramChannel'), href: 'https://t.me/bmrlleague', text: '@bmrlleague' },
  { key: 'tiktok', icon: Music2, label: t('main.tiktok'), href: 'https://www.tiktok.com/@beamngrl', text: '@beamngrl' },
  { key: 'twitch', icon: Radio, label: 'Twitch', href: 'https://www.twitch.tv/bmrlracing', text: 'bmrlracing' }
])

const emails = ['37foneziazaz0909@gmail.com']

onMounted(async () => {
  try {
    donations.value = await api('/app-settings/donations')
  } catch {
    donations.value = { donation_url: '', top_donations: [] }
  }
})
</script>

<template>
  <footer class="foot">
    <div class="foot__inner ui-shell ui-shell--wide">
      <div class="foot__panel ui-glass">
        <section class="foot__brand" v-reveal>
          <img class="foot__logo foot__logo--light" :src="brandingSettings.light_logo_url" alt="BMRL" />
          <img class="foot__logo foot__logo--dark" :src="brandingSettings.dark_logo_url" alt="BMRL" />
          <p class="foot__motto ui-display">{{ t('ui.footer.motto') }}</p>
          <p class="foot__about">{{ t('ui.footer.about') }}</p>
          <StartLights size="sm" :lit="0" :label="t('ui.footer.lightsLabel')" />
        </section>

        <section class="foot__col" v-reveal="80">
          <h2 class="ui-eyebrow">{{ t('main.community') }}</h2>
          <a v-for="item in socials" :key="item.key" class="foot__social" :href="item.href" target="_blank" rel="noopener noreferrer">
            <span class="foot__social-icon"><component :is="item.icon" :size="17" /></span>
            <span class="foot__social-text">
              <b>{{ item.label }}</b>
              <small>{{ item.text }}</small>
            </span>
            <ArrowUpRight class="foot__arrow" :size="16" />
          </a>
        </section>

        <section class="foot__col" v-reveal="140">
          <h2 class="ui-eyebrow">{{ t('main.contacts') }}</h2>
          <p class="foot__hint">{{ t('main.contactSubtitle') }}</p>
          <div class="foot__contact">
            <span class="foot__contact-label"><Mail :size="15" />{{ t('main.contactMail') }}</span>
            <a v-for="email in emails" :key="email" class="foot__link" :href="`mailto:${email}`">{{ email }}</a>
          </div>
          <div class="foot__contact">
            <span class="foot__contact-label"><MessageCircle :size="15" />{{ t('main.contactDiscord') }}</span>
            <span class="foot__value ui-mono">pianino22</span>
          </div>
        </section>

        <section class="foot__col foot__support" v-reveal="200">
          <h2 class="ui-eyebrow">{{ t('main.supportProject') }}</h2>
          <p class="foot__hint">{{ t('main.supportHint') }}</p>
          <a v-if="safeHttpUrl(donations.donation_url)" v-spark="'#ff6b7a'" class="ui-btn ui-btn--primary" :href="safeHttpUrl(donations.donation_url)" target="_blank" rel="noopener noreferrer">
            <HeartHandshake :size="17" />{{ t('main.supportProject') }}
          </a>
          <div class="foot__donations">
            <span class="ui-eyebrow">{{ t('main.topDonations') }}</span>
            <span v-if="!topDonations.length" class="foot__hint">{{ t('main.noTopDonations') }}</span>
            <div v-for="(donation, index) in topDonations" :key="`${donation.name}-${donation.amount}`" class="foot__donation">
              <span class="foot__place ui-num">P{{ index + 1 }}</span>
              <span class="foot__donor">
                <b>{{ donation.name }}</b>
                <small>{{ donation.message || t('main.donationCommentSpace') }}</small>
              </span>
              <em class="ui-num">{{ donation.amount }}</em>
            </div>
          </div>
        </section>
      </div>
      <div class="foot__base">
        <span>© {{ year }} BMRL · {{ t('ui.footer.rights') }}</span>
        <RouterLink class="foot__legal" :to="{ path: '/legal', query: { from: 'main' } }"><Scale :size="14" />{{ t('ui.footer.legal') }}</RouterLink>
        <span class="ui-mono">{{ t('ui.footer.tagline') }}</span>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.foot {
  padding: 24px 0 calc(28px + var(--tabbar-h));
}

.foot__panel {
  display: grid;
  grid-template-columns: minmax(240px, 1.3fr) repeat(3, minmax(0, 1fr));
  gap: clamp(20px, 3vw, 44px);
  padding: clamp(22px, 3.4vw, 44px);
  border-radius: var(--r-xl);
}

.foot__brand {
  display: grid;
  align-content: start;
  gap: 14px;
}

.foot__logo {
  width: auto;
  height: 34px;
  object-fit: contain;
  object-position: left;
}

.foot__logo--dark,
:root[data-theme='dark'] .foot__logo--light {
  display: none;
}

:root[data-theme='dark'] .foot__logo--dark {
  display: block;
}

.foot__motto {
  color: var(--c-text);
  font-size: clamp(20px, 2vw, 26px);
}

.foot__about,
.foot__hint {
  margin: 0;
  color: var(--c-text-2);
  font-size: 14px;
  line-height: 1.55;
}

.foot__col {
  display: grid;
  align-content: start;
  gap: 12px;
  min-width: 0;
}

.foot__col h2 {
  margin-bottom: 4px;
}

.foot__social {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
  margin: 0 -8px;
  border-radius: var(--r-md);
  color: var(--c-text);
  text-decoration: none;
  transition: background-color var(--dur-2);
}

.foot__social:hover {
  background: var(--c-blue-soft);
}

.foot__social-icon {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  width: 36px;
  height: 36px;
  border: 1px solid var(--c-line);
  border-radius: 11px;
  background: var(--c-sunken);
  color: var(--c-accent-text);
}

.foot__social-text {
  display: grid;
  flex: 1 1 auto;
  min-width: 0;
}

.foot__social-text b {
  font-size: 14px;
  font-weight: 600;
}

.foot__social-text small {
  overflow: hidden;
  color: var(--c-text-3);
  font-family: var(--font-mono);
  font-size: 11.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.foot__arrow {
  color: var(--c-text-3);
  transition: transform var(--dur-2) var(--ease-ios), color var(--dur-2);
}

.foot__social:hover .foot__arrow {
  color: var(--c-accent-text);
  transform: translate(2px, -2px);
}

.foot__contact {
  display: grid;
  gap: 4px;
}

.foot__contact-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--c-text-3);
  font-size: 12.5px;
}

.foot__link,
.foot__value {
  overflow-wrap: anywhere;
  color: var(--c-text);
  font-size: 14px;
  text-decoration: none;
}

.foot__link:hover {
  color: var(--c-accent-text);
}

.foot__donations {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  background: var(--c-sunken);
}

.foot__donation {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
}

.foot__place {
  color: var(--c-accent-text);
  font-size: 12px;
}

.foot__donor {
  display: grid;
  min-width: 0;
}

.foot__donor b {
  font-size: 13.5px;
}

.foot__donor small {
  overflow: hidden;
  color: var(--c-text-3);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.foot__donation em {
  color: var(--c-text);
  font-size: 13px;
  font-style: normal;
}

.foot__base {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px 20px;
  padding: 16px 8px 0;
  color: var(--c-text-3);
  font-size: 12px;
}

.foot__legal {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--c-text-2);
  font-weight: 600;
  text-decoration: none;
  transition: color var(--dur-1);
}

.foot__legal:hover {
  color: var(--c-accent-text);
}

@media (max-width: 1100px) {
  .foot__panel {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .foot__panel {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
