import TestBuild from '../views/TestBuild.vue'
import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import ScanPage from '../views/ScanPage.vue'
import Schedule from '../views/Schedule.vue'
import History from '../views/History.vue'
import Rules from '../views/Rules.vue'
import Settings from '../views/Settings.vue'
import Sites from '../views/Sites.vue'
import Assets from '../views/Assets.vue'
import SiteMonitor from '../views/SiteMonitor.vue'
import NotificationSettings from '../views/NotificationSettings.vue'
import Login from '../views/Login.vue'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/login', name: 'Login', component: Login },
  { path: '/dashboard', name: 'Dashboard', component: Dashboard },
  { path: '/scan', name: 'Scan', component: ScanPage },
  { path: '/schedule', name: 'Schedule', component: Schedule },
  { path: '/history', name: 'History', component: History },
  { path: '/rules', name: 'Rules', component: Rules },
  { path: '/settings', name: 'Settings', component: Settings },
  { path: '/sites', name: 'Sites', component: Sites },
  { path: '/assets', name: 'Assets', component: Assets },
  { path: '/test', name: 'TestBuild', component: TestBuild },
  { path: '/monitor', name: 'SiteMonitor', component: SiteMonitor },
  { path: '/notifications', name: 'NotificationSettings', component: NotificationSettings },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Auth guard
router.beforeEach((to, from, next) => {
  const publicPaths = ['/login']
  if (publicPaths.includes(to.path)) {
    next()
  } else {
    const token = localStorage.getItem('libra_token')
    if (!token) {
      next('/login')
    } else {
      next()
    }
  }
})

export default router
