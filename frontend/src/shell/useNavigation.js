import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { CalendarDays, Calculator, Flag, Home, Image, ListChecks, Medal, Newspaper, Settings2, Shield, Trophy, User, Users, Vote } from 'lucide-vue-next'
import { state } from '../store'

/**
 * Role-aware navigation shared by the header, the mobile sheet and the command palette.
 * Public links stay in the main bar; staff tools are grouped separately.
 */
export function useNavigation() {
  const { t } = useI18n()
  const role = computed(() => state.user?.role)
  const isActive = computed(() => state.user?.status === 'active')
  const has = (roles) => isActive.value && roles.includes(role.value)

  const publicItems = computed(() => [
    { key: 'main', to: '/', label: t('nav.main'), icon: Home },
    { key: 'calendar', to: '/calendar', label: t('nav.calendar'), icon: CalendarDays },
    { key: 'championships', to: '/championships', label: t('nav.championships'), icon: Flag },
    { key: 'pilots', to: '/pilots', label: t('nav.pilots'), icon: Users },
    { key: 'teams', to: '/teams', label: t('nav.teams'), icon: Trophy },
    { key: 'hallOfFame', to: '/hall-of-fame', label: t('nav.hallOfFame'), icon: Medal },
    { key: 'fuel', to: '/fuel-calculator', label: t('nav.fuel'), icon: Calculator }
  ])

  const staffItems = computed(() => [
    { key: 'races', to: '/races/manage', label: t('nav.races'), icon: ListChecks, visible: has(['admin', 'moder']) },
    { key: 'appeals', to: '/appeals', label: t('nav.appeals'), icon: Shield, visible: has(['admin', 'moder', 'marshall']) },
    { key: 'moderation', to: '/moderation/users', label: t('nav.moderation'), icon: User, visible: has(['admin', 'moder']) },
    { key: 'banners', to: '/banners', label: t('nav.banners'), icon: Image, visible: has(['admin', 'moder', 'smm']) },
    { key: 'news', to: '/news/manage', label: t('nav.news'), icon: Newspaper, visible: has(['admin', 'moder', 'smm']) },
    { key: 'competitions', to: '/competitions/manage', label: t('nav.competitions'), icon: Vote, visible: has(['admin', 'moder']) },
    { key: 'admin', to: '/admin/users', label: t('nav.admin'), icon: Settings2, visible: has(['admin']) }
  ].filter((item) => item.visible))

  return { publicItems, staffItems }
}
