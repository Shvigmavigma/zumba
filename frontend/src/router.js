import { createRouter, createWebHistory } from 'vue-router'
// Only the home page ships in the main bundle; every other screen loads on demand.
import MainMenu from './pages/MainMenu.vue'
import { state } from './store'

const PilotList = () => import('./pages/PilotList.vue')
const PilotDetails = () => import('./pages/PilotDetails.vue')
const Login = () => import('./pages/Login.vue')
const Registration = () => import('./pages/Registration.vue')
const Profile = () => import('./pages/Profile.vue')
const ProfileEdit = () => import('./pages/ProfileEdit.vue')
const RaceDetails = () => import('./pages/RaceDetails.vue')
const RaceEdit = () => import('./pages/RaceEdit.vue')
const RaceAdminList = () => import('./pages/RaceAdminList.vue')
const RaceCalendar = () => import('./pages/RaceCalendar.vue')
const AppealModeration = () => import('./pages/AppealModeration.vue')
const BannerEdit = () => import('./pages/BannerEdit.vue')
const NewsManage = () => import('./pages/NewsManage.vue')
const AdminUserList = () => import('./pages/AdminUserList.vue')
const UserEditModeration = () => import('./pages/UserEditModeration.vue')
const TeamList = () => import('./pages/TeamList.vue')
const HallOfFame = () => import('./pages/HallOfFame.vue')
const ChampionshipList = () => import('./pages/ChampionshipList.vue')
const FuelCalculator = () => import('./pages/FuelCalculator.vue')
const Competitions = () => import('./pages/Competitions.vue')
const CompetitionBracket = () => import('./pages/CompetitionBracket.vue')
const LegalIndex = () => import('./pages/LegalIndex.vue')
const LegalDocuments = () => import('./pages/LegalDocuments.vue')

// Matches the leave phase of the route transition so the old page fades out in place.
const ROUTE_LEAVE_MS = 200

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior(to, from, savedPosition) {
    if (to.path === from.path) return false
    return new Promise((resolve) => {
      window.setTimeout(() => resolve(savedPosition || { top: 0 }), ROUTE_LEAVE_MS)
    })
  },
  routes: [
    { path: '/', component: MainMenu, meta: { design: true } },
    { path: '/pilots', component: PilotList, meta: { design: true } },
    { path: '/pilots/:id', component: PilotDetails, meta: { design: true } },
    { path: '/teams', component: TeamList, meta: { design: true } },
    { path: '/championships', component: ChampionshipList, meta: { design: true } },
    { path: '/hall-of-fame', component: HallOfFame, meta: { design: true } },
    { path: '/fuel-calculator', component: FuelCalculator, meta: { design: true } },
    { path: '/login', component: Login, meta: { design: true } },
    { path: '/register', component: Registration, meta: { design: true } },
    { path: '/profile', component: Profile, meta: { auth: true, design: true } },
    { path: '/profile/edit', component: ProfileEdit, meta: { auth: true, design: true } },
    { path: '/races/new', component: RaceEdit, meta: { roles: ['admin', 'moder'] } },
    { path: '/races/manage', component: RaceAdminList, meta: { roles: ['admin', 'moder'] } },
    { path: '/races/:id', component: RaceDetails, meta: { auth: true, design: true } },
    { path: '/races/:id/edit', component: RaceEdit, meta: { roles: ['admin', 'moder'] } },
    { path: '/calendar', component: RaceCalendar, meta: { design: true } },
    { path: '/appeals', component: AppealModeration, meta: { roles: ['admin', 'moder', 'marshall'] } },
    { path: '/banners', component: BannerEdit, meta: { roles: ['admin', 'moder', 'smm'] } },
    { path: '/news/manage', component: NewsManage, meta: { roles: ['admin', 'moder', 'smm'] } },
    { path: '/admin/users', component: AdminUserList, meta: { roles: ['admin'] } },
    { path: '/moderation/users', component: UserEditModeration, meta: { roles: ['admin', 'moder'] } },
    { path: '/competitions/manage', name: 'competition-manage', component: Competitions, meta: { roles: ['admin', 'moder'] } },
    { path: '/competitions/bracket/:token', name: 'competition-bracket', component: CompetitionBracket },
    { path: '/competitions/view/:token', name: 'competition-view', component: Competitions },
    { path: '/legal', component: LegalIndex, meta: { design: true } },
    { path: '/privacy-policy', component: LegalDocuments, meta: { design: true, legalDocument: 'privacy' } },
    { path: '/terms', component: LegalDocuments, meta: { design: true, legalDocument: 'terms' } },
    { path: '/cookies', component: LegalDocuments, meta: { design: true, legalDocument: 'cookies' } }
  ]
})

router.beforeEach((to) => {
  if ((to.meta.auth || to.meta.roles) && !state.user) {
    return '/register'
  }
  if ((to.meta.auth || to.meta.roles) && state.user?.status !== 'active') {
    return '/'
  }
  if (to.meta.roles && !to.meta.roles.includes(state.user?.role)) {
    return '/'
  }
})

export default router
