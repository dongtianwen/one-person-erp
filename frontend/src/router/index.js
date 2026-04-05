import { createRouter, createWebHistory } from 'vue-router'
import Layout from '../components/Layout.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue')
      },
      {
        path: 'customers',
        name: 'Customers',
        component: () => import('../views/Customers.vue')
      },
      {
        path: 'customers/:id',
        name: 'CustomerDetail',
        component: () => import('../views/CustomerDetail.vue')
      },
      {
        path: 'projects',
        name: 'Projects',
        component: () => import('../views/Projects.vue')
      },
      {
        path: 'contracts',
        name: 'Contracts',
        component: () => import('../views/Contracts.vue')
      },
      {
        path: 'finances',
        name: 'Finances',
        component: () => import('../views/Finances.vue')
      },
      {
        path: 'reminders',
        name: 'Reminders',
        component: () => import('../views/Reminders.vue')
      },
      {
        path: 'file-indexes',
        name: 'FileIndexes',
        component: () => import('../views/FileIndexes.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  if (to.meta.requiresAuth !== false && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
