<template>
  <div class="login-wrapper">
    <!-- Left: Brand Visual -->
    <div class="login-brand">
      <div class="brand-grid">
        <div v-for="i in 20" :key="i" class="grid-cell" :class="`cell-${i}`" />
      </div>
      <div class="brand-content">
        <div class="brand-logo">
          <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="4" y="4" width="40" height="40" rx="10" stroke="currentColor" stroke-width="2.5" />
            <path d="M16 24L22 30L34 18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
            <circle cx="36" cy="12" r="4" fill="var(--brand-cyan)" opacity="0.6" />
          </svg>
        </div>
        <h1 class="brand-title">天枢</h1>
        <p class="brand-tagline">智能项目管理 · 精准数据决策</p>
        <div class="brand-features">
          <div class="feature-item anim-fade-in-up stagger-1">
            <span class="feature-dot" />
            <span>客户全生命周期管理</span>
          </div>
          <div class="feature-item anim-fade-in-up stagger-2">
            <span class="feature-dot" />
            <span>项目进度实时追踪</span>
          </div>
          <div class="feature-item anim-fade-in-up stagger-3">
            <span class="feature-dot" />
            <span>财务数据智能分析</span>
          </div>
        </div>
      </div>
      <div class="brand-footer">
        <span>&copy; 2026 天枢</span>
      </div>
    </div>

    <!-- Right: Login Form -->
    <div class="login-form-side">
      <div class="login-form-container anim-fade-in">
        <div class="form-header">
          <h2>欢迎回来</h2>
          <p>登录以继续使用天枢</p>
        </div>

        <el-form :model="form" @submit.prevent="handleLogin" class="login-form-body">
          <div class="field-group">
            <label class="field-label">用户名</label>
            <el-input
              v-model="form.username"
              placeholder="请输入用户名"
              size="large"
              :prefix-icon="User"
            />
          </div>

          <div class="field-group">
            <label class="field-label">密码</label>
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              size="large"
              :prefix-icon="Lock"
              show-password
              @keyup.enter="handleLogin"
            />
          </div>

          <div class="field-options">
            <el-checkbox v-model="form.remember">记住登录状态</el-checkbox>
          </div>

          <el-button
            type="primary"
            size="large"
            :loading="loading"
            @click="handleLogin"
            class="login-btn"
          >
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form>

        <div class="login-footer">
          <span class="footer-text">天枢 v1.13</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { login } from '../api/auth'
import { useAuthStore } from '../store/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const form = reactive({ username: '', password: '', remember: false })

const handleLogin = async () => {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const { data } = await login(form.username, form.password)
    authStore.login(data)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e) {
    // Error handled by interceptor
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrapper {
  display: flex;
  min-height: 100vh;
  background: var(--surface-base);
}

/* ---- Left Brand Panel ---- */
.login-brand {
  position: relative;
  flex: 0 0 52%;
  background: var(--surface-sidebar);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

/* Animated grid cells */
.brand-grid {
  position: absolute;
  inset: 0;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  grid-template-rows: repeat(4, 1fr);
  gap: 4px;
  padding: 24px;
  opacity: 0.08;
}

.grid-cell {
  border: 1px solid var(--brand-cyan);
  border-radius: 4px;
  animation: cellPulse 4s ease-in-out infinite;
}

.cell-1  { animation-delay: 0s; }
.cell-3  { animation-delay: 0.3s; }
.cell-5  { animation-delay: 0.6s; }
.cell-7  { animation-delay: 0.15s; }
.cell-9  { animation-delay: 0.45s; }
.cell-11 { animation-delay: 0.75s; }
.cell-13 { animation-delay: 0.9s; }
.cell-15 { animation-delay: 0.2s; }
.cell-17 { animation-delay: 0.5s; }
.cell-19 { animation-delay: 0.8s; }

@keyframes cellPulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; border-color: var(--brand-cyan-light); }
}

.brand-content {
  position: relative;
  z-index: 1;
  text-align: center;
  color: var(--text-inverse);
}

.brand-logo {
  width: 56px;
  height: 56px;
  margin: 0 auto 20px;
  color: var(--brand-cyan);
}

.brand-title {
  font-size: 42px;
  font-weight: 700;
  letter-spacing: -0.03em;
  margin: 0 0 8px;
  background: linear-gradient(135deg, #fff 40%, var(--brand-cyan-light));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.brand-tagline {
  font-size: 15px;
  color: var(--text-inverse-muted);
  margin: 0 0 48px;
  letter-spacing: 0.04em;
}

.brand-features {
  display: flex;
  flex-direction: column;
  gap: 14px;
  align-items: flex-start;
  margin: 0 auto;
  width: fit-content;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
}

.feature-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--brand-cyan);
  box-shadow: 0 0 8px var(--brand-cyan);
  flex-shrink: 0;
}

.brand-footer {
  position: absolute;
  bottom: 24px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.25);
}

/* ---- Right Form Panel ---- */
.login-form-side {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.login-form-container {
  width: 100%;
  max-width: 380px;
}

.form-header {
  margin-bottom: 36px;
}

.form-header h2 {
  font-size: 26px;
  font-weight: 700;
  margin: 0 0 6px;
  letter-spacing: -0.02em;
}

.form-header p {
  color: var(--text-secondary);
  margin: 0;
  font-size: 14px;
}

.field-group {
  margin-bottom: 20px;
}

.field-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.field-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 15px;
  font-weight: 600;
  border-radius: var(--radius-md);
  letter-spacing: 0.08em;
}

.login-footer {
  text-align: center;
  margin-top: 40px;
}

.footer-text {
  font-size: 12px;
  color: var(--text-tertiary);
}

/* ---- Responsive ---- */
@media (max-width: 900px) {
  .login-brand { display: none; }
  .login-form-side { padding: 24px; }
}
</style>
