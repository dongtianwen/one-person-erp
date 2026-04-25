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
      },
      {
        path: 'quotations',
        name: 'Quotations',
        component: () => import('../views/Quotations.vue')
      },
      {
        path: 'settings/templates',
        name: 'Templates',
        component: () => import('../views/Templates.vue')
      },
      {
        path: 'settings/company',
        name: 'CompanySettings',
        component: () => import('../views/CompanySettings.vue')
      },
      {
        path: 'exports',
        name: 'Exports',
        component: () => import('../views/Exports.vue')
      },
      {
        path: 'workflow-guide',
        name: 'WorkflowGuide',
        component: () => import('../views/WorkflowGuide.vue')
      },
      {
        path: 'agents/decision',
        name: 'AgentBusinessDecision',
        component: () => import('../views/AgentBusinessDecision.vue')
      },
      {
        path: 'agents/logs',
        name: 'AgentLogs',
        component: () => import('../views/AgentLogs.vue')
      },
      {
        path: 'agents/settings',
        name: 'AgentSettings',
        component: () => import('../views/AgentSettings.vue')
      },
      {
        path: 'assistant/qa',
        name: 'QaAssistant',
        component: () => import('../views/QaAssistant.vue')
      },
      {
        path: 'minutes',
        name: 'MinutesList',
        component: () => import('../views/minutes/MinutesListView.vue')
      },
      {
        path: 'minutes/:id',
        name: 'MinutesDetail',
        component: () => import('../views/minutes/MinutesDetailView.vue')
      },
      {
        path: 'tools/entries',
        name: 'ToolEntries',
        component: () => import('../views/tools/ToolEntriesView.vue')
      },
      {
        path: 'leads',
        name: 'Leads',
        component: () => import('../views/leads/LeadsView.vue')
      },
      {
        path: ':pathMatch(.*)*',
        name: 'NotFound',
        component: () => import('../views/Dashboard.vue'),
        beforeEnter: (to, from, next) => {
          next('/dashboard')
        }
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
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else {
    next()
  }
})

export default router
