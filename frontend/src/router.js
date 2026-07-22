import { createRouter, createWebHistory } from 'vue-router'
import MainMenu from './pages/MainMenu.vue'
import PilotList from './pages/PilotList.vue'
import PilotDetails from './pages/PilotDetails.vue'
import Login from './pages/Login.vue'
import Registration from './pages/Registration.vue'
import Profile from './pages/Profile.vue'
import RaceDetails from './pages/RaceDetails.vue'
import RaceEdit from './pages/RaceEdit.vue'
import RaceAdminList from './pages/RaceAdminList.vue'
import RaceCalendar from './pages/RaceCalendar.vue'
import AppealModeration from './pages/AppealModeration.vue'
import BannerEdit from './pages/BannerEdit.vue'
import NewsManage from './pages/NewsManage.vue'
import AdminUserList from './pages/AdminUserList.vue'
import UserEditModeration from './pages/UserEditModeration.vue'
import { state } from './store'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: MainMenu },
    { path: '/pilots', component: PilotList },
    { path: '/pilots/:id', component: PilotDetails },
    { path: '/login', component: Login },
    { path: '/register', component: Registration },
    { path: '/profile', component: Profile, meta: { auth: true } },
    { path: '/races/new', component: RaceEdit, meta: { roles: ['admin', 'moder'] } },
    { path: '/races/manage', component: RaceAdminList, meta: { roles: ['admin', 'moder'] } },
    { path: '/races/:id', component: RaceDetails, meta: { auth: true } },
    { path: '/races/:id/edit', component: RaceEdit, meta: { roles: ['admin', 'moder'] } },
    { path: '/calendar', component: RaceCalendar },
    { path: '/appeals', component: AppealModeration, meta: { roles: ['admin', 'moder', 'marshall'] } },
    { path: '/banners', component: BannerEdit, meta: { roles: ['admin', 'moder', 'smm'] } },
    { path: '/news/manage', component: NewsManage, meta: { roles: ['admin', 'moder', 'smm'] } },
    { path: '/admin/users', component: AdminUserList, meta: { roles: ['admin'] } },
    { path: '/moderation/users', component: UserEditModeration, meta: { roles: ['admin', 'moder'] } }
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
