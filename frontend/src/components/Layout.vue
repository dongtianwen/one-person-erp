<template>
  <el-container class="layout-container">
    <!-- Sidebar -->
    <el-aside :width="collapsed ? '64px' : '220px'" class="sidebar">
      <div class="sidebar-logo" @click="collapsed = !collapsed">
        <div class="logo-icon">
          <svg viewBox="0 0 32 32" fill="none">
            <rect x="2" y="2" width="28" height="28" rx="7" stroke="currentColor" stroke-width="2" />
            <path d="M10 16L14 20L22 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
        <span v-if="!collapsed" class="logo-text">数标云管</span>
      </div>

      <el-menu
        :default-active="route.path"
        router
        :collapse="collapsed"
        background-color="#0f172a"
        text-color="rgba(255,255,255,0.65)"
        active-text-color="#22d3ee"
        class="sidebar-menu"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>仪表盘</template>
        </el-menu-item>
        <el-menu-item index="/customers">
          <el-icon><User /></el-icon>
          <template #title>客户管理</template>
        </el-menu-item>
        <el-menu-item index="/projects">
          <el-icon><Folder /></el-icon>
          <template #title>项目管理</template>
        </el-menu-item>
        <el-menu-item index="/contracts">
          <el-icon><Document /></el-icon>
          <template #title>合同管理</template>
        </el-menu-item>
        <el-menu-item index="/finances">
          <el-icon><Money /></el-icon>
          <template #title>财务管理</template>
        </el-menu-item>
        <el-menu-item index="/reminders">
          <el-icon><Bell /></el-icon>
          <template #title>提醒管理</template>
        </el-menu-item>
        <el-menu-item index="/file-indexes">
          <el-icon><FolderOpened /></el-icon>
          <template #title>文件管理</template>
        </el-menu-item>
        <el-menu-item index="/quotations">
          <el-icon><Tickets /></el-icon>
          <template #title>报价单</template>
        </el-menu-item>
        <el-menu-item index="/exports">
          <el-icon><Download /></el-icon>
          <template #title>数据导出</template>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-bottom">
        <div class="collapse-btn" @click="collapsed = !collapsed">
          <el-icon :size="16">
            <component :is="collapsed ? 'Expand' : 'Fold'" />
          </el-icon>
        </div>
      </div>
    </el-aside>

    <!-- Main Area -->
    <el-container class="main-area">
      <el-header class="app-header" height="56px">
        <div class="breadcrumb-item">{{ currentPageTitle }}</div>
        <div class="header-right">
          <el-dropdown @command="handleCommand" trigger="click">
            <div class="user-trigger">
              <div class="user-avatar">{{ (authStore.user?.username || '管')[0] }}</div>
              <span class="user-name">{{ authStore.user?.username || '管理员' }}</span>
              <el-icon :size="12"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'
import {
  DataAnalysis, User, Folder, Document, Money, Bell, FolderOpened, Tickets, Download,
  ArrowDown, SwitchButton, Expand, Fold
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const collapsed = ref(false)

const pageTitles = {
  '/dashboard': '仪表盘',
  '/customers': '客户管理',
  '/projects': '项目管理',
  '/contracts': '合同管理',
  '/finances': '财务管理',
  '/reminders': '提醒管理',
  '/file-indexes': '文件管理',
  '/quotations': '报价单管理',
  '/exports': '数据导出',
}

const currentPageTitle = computed(() => pageTitles[route.path] || '数标云管')

onMounted(() => {
  if (authStore.isAuthenticated()) {
    authStore.fetchUser()
  }
})

const handleCommand = (command) => {
  if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout-container { height: 100vh; overflow: hidden; }

/* Sidebar */
.sidebar {
  background: #0f172a !important;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: width 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.sidebar::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 40%;
  background: linear-gradient(to top, rgba(6, 182, 212, 0.04), transparent);
  pointer-events: none;
  z-index: 0;
}

/* Logo */
.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 18px;
  height: 56px;
  cursor: pointer;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  flex-shrink: 0;
}

.logo-icon {
  width: 28px;
  height: 28px;
  color: #0891b2;
  flex-shrink: 0;
}

.logo-text {
  font-size: 17px;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.01em;
  white-space: nowrap;
}

/* Override el-menu to fit our design */
.sidebar-menu {
  flex: 1;
  border-right: none !important;
  padding: 8px;
}

.sidebar-menu .el-menu-item {
  height: 44px;
  line-height: 44px;
  border-radius: 10px;
  margin-bottom: 2px;
}

.sidebar-menu .el-menu-item:hover {
  background: rgba(255, 255, 255, 0.06) !important;
}

.sidebar-menu .el-menu-item.is-active {
  background: rgba(6, 182, 212, 0.1) !important;
  position: relative;
}

.sidebar-menu .el-menu-item.is-active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  border-radius: 0 3px 3px 0;
  background: #0891b2;
  box-shadow: 0 0 8px rgba(8, 145, 178, 0.5);
}

/* Bottom */
.sidebar-bottom {
  padding: 12px 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  flex-shrink: 0;
}

.collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.35);
  cursor: pointer;
  transition: all 0.15s;
}

.collapse-btn:hover {
  color: rgba(255, 255, 255, 0.7);
  background: rgba(255, 255, 255, 0.04);
}

/* Main Area */
.main-area {
  background: var(--surface-base);
  display: flex;
  flex-direction: column;
}

/* Header */
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: var(--surface-card);
  border-bottom: 1px solid var(--border-default);
  height: 56px;
}

.breadcrumb-item {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.header-right {
  display: flex;
  align-items: center;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 10px;
  transition: background 0.15s;
}

.user-trigger:hover {
  background: var(--surface-base);
}

.user-avatar {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: linear-gradient(135deg, #0891b2, #0369a1);
  color: white;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

/* Main Content */
.app-main {
  padding: 24px;
  overflow-y: auto;
  background: var(--surface-base);
}

/* Page transition */
.page-enter-active {
  animation: fadeInUp 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.page-leave-active {
  animation: fadeIn 0.15s ease reverse;
}
</style>
