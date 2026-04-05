<template>
  <div class="dashboard">
    <!-- Metric Cards -->
    <div class="metrics-grid">
      <div
        v-for="(card, idx) in metricCards"
        :key="card.key"
        class="metric-card anim-fade-in-up"
        :class="`stagger-${idx + 1}`"
        :style="{ '--card-color': card.color, '--card-glow': card.glow }"
      >
        <div class="metric-icon">
          <el-icon :size="22"><component :is="card.icon" /></el-icon>
        </div>
        <div class="metric-body">
          <div class="metric-label">{{ card.label }}</div>
          <div class="metric-value mono">{{ card.prefix }}{{ formatNumber(card.value) }}</div>
        </div>
        <div class="metric-bg-icon">
          <el-icon :size="64"><component :is="card.icon" /></el-icon>
        </div>
      </div>
    </div>

    <!-- Revenue Trend -->
    <el-card class="anim-fade-in-up stagger-2" style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <span class="card-title">营收趋势</span>
          <span class="card-subtitle">近12个月收支对比</span>
        </div>
      </template>
      <div v-if="!revenueTrend.length" class="empty-state">
        <el-icon :size="32" color="var(--text-tertiary)"><TrendCharts /></el-icon>
        <p>暂无数据</p>
      </div>
      <div v-else class="trend-chart">
        <div class="trend-bars">
          <div v-for="item in revenueTrend" :key="item.month" class="trend-col">
            <div class="trend-col-bars">
              <div
                class="trend-bar income-bar"
                :style="{ height: barHeight(item.income) + '%' }"
                :title="'收入: ¥' + formatNumber(item.income)"
              />
              <div
                class="trend-bar expense-bar"
                :style="{ height: barHeight(item.expense) + '%' }"
                :title="'支出: ¥' + formatNumber(item.expense)"
              />
            </div>
            <div class="trend-month">{{ item.month.slice(5) }}</div>
          </div>
        </div>
        <div class="trend-legend">
          <span class="legend-item"><i class="legend-dot" style="background:#10b981" />收入</span>
          <span class="legend-item"><i class="legend-dot" style="background:#f43f5e" />支出</span>
        </div>
      </div>
    </el-card>

    <!-- Charts Row -->
    <el-row :gutter="20" class="charts-row">
      <el-col :span="12">
        <el-card class="chart-card anim-fade-in-up stagger-3">
          <template #header>
            <div class="card-header">
              <span class="card-title">客户转化漏斗</span>
              <span class="card-subtitle">各阶段客户分布</span>
            </div>
          </template>
          <div class="funnel-list">
            <div
              v-for="(item, idx) in funnelItems"
              :key="item.stage"
              class="funnel-row"
              :style="{ animationDelay: `${200 + idx * 80}ms` }"
            >
              <div class="funnel-label">{{ item.label }}</div>
              <div class="funnel-bar-track">
                <div
                  class="funnel-bar-fill"
                  :style="{ width: item.percent + '%', background: item.color }"
                />
              </div>
              <div class="funnel-count mono">{{ item.count }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="chart-card anim-fade-in-up stagger-4">
          <template #header>
            <div class="card-header">
              <span class="card-title">项目状态分布</span>
              <span class="card-subtitle">当前项目进度概览</span>
            </div>
          </template>
          <div class="status-list">
            <div
              v-for="(item, idx) in statusItems"
              :key="item.status"
              class="status-row"
              :style="{ animationDelay: `${200 + idx * 80}ms` }"
            >
              <div class="status-dot" :style="{ background: item.color }" />
              <div class="status-label">{{ item.label }}</div>
              <div class="status-bar-track">
                <div
                  class="status-bar-fill"
                  :style="{ width: item.percent + '%', background: item.color }"
                />
              </div>
              <div class="status-count mono">{{ item.count }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Bottom Row: 3 columns -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="8">
        <el-card class="anim-fade-in-up stagger-5">
          <template #header>
            <div class="card-header">
              <span class="card-title">待办事项</span>
              <el-tag v-if="todos.tasks?.length" size="small" type="danger" round>{{ todos.tasks.length }}</el-tag>
            </div>
          </template>
          <div v-if="!todos.tasks?.length" class="empty-state">
            <el-icon :size="32" color="var(--text-tertiary)"><Calendar /></el-icon>
            <p>暂无待办</p>
          </div>
          <div v-for="task in todos.tasks" :key="task.id" class="todo-row">
            <div class="todo-priority" :class="task.priority" />
            <div class="todo-content">
              <div class="todo-left">
                <span class="todo-title">{{ task.title }}</span>
                <el-tag
                  v-if="task.priority"
                  size="small"
                  :type="priorityTagType(task.priority)"
                  class="todo-tag"
                >{{ priorityLabel(task.priority) }}</el-tag>
              </div>
              <span class="todo-due">{{ task.due_date || '无截止日期' }}</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card class="anim-fade-in-up stagger-6">
          <template #header>
            <div class="card-header">
              <span class="card-title">即将到期合同</span>
              <el-tag v-if="todos.expiring_contracts?.length" size="small" type="warning" round>{{ todos.expiring_contracts.length }}</el-tag>
            </div>
          </template>
          <div v-if="!todos.expiring_contracts?.length" class="empty-state">
            <el-icon :size="32" color="var(--text-tertiary)"><Document /></el-icon>
            <p>暂无即将到期合同</p>
          </div>
          <div v-for="c in todos.expiring_contracts" :key="c.id" class="contract-row">
            <div class="contract-info">
              <span class="contract-no mono">{{ c.contract_no }}</span>
              <span class="contract-title">{{ c.title }}</span>
            </div>
            <div class="contract-meta">
              <el-tag
                size="small"
                :type="daysLeft(c.end_date) <= 3 ? 'danger' : 'warning'"
                round
                class="contract-countdown"
              >剩余 {{ daysLeft(c.end_date) }} 天</el-tag>
              <span class="contract-date">
                <el-icon :size="14"><Calendar /></el-icon>
                {{ c.end_date }}
              </span>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card class="anim-fade-in-up stagger-6">
          <template #header>
            <div class="card-header">
              <span class="card-title">提醒事项</span>
              <el-tag v-if="todos.reminders?.length" size="small" type="warning" round>{{ todos.reminders.length }}</el-tag>
            </div>
          </template>
          <div v-if="!todos.reminders?.length" class="empty-state">
            <el-icon :size="32" color="var(--text-tertiary)"><Bell /></el-icon>
            <p>暂无提醒</p>
          </div>
          <div v-for="r in todos.reminders" :key="r.id" class="reminder-row" :class="{ overdue: r.status === 'overdue' }">
            <div class="reminder-indicator" :class="r.status === 'overdue' ? 'overdue' : 'pending'" />
            <div class="reminder-content">
              <div class="reminder-left">
                <span class="reminder-title">{{ r.title }}</span>
                <el-tag v-if="r.is_critical" size="small" type="danger" class="reminder-tag">关键</el-tag>
                <el-tag size="small" :type="reminderTypeTag(r.reminder_type)" class="reminder-tag">{{ reminderTypeLabel(r.reminder_type) }}</el-tag>
              </div>
              <div class="reminder-meta">
                <el-tag v-if="r.status === 'overdue'" size="small" type="danger" round>已逾期</el-tag>
                <span class="reminder-date">{{ r.reminder_date }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Quick Actions -->
    <div class="quick-actions-bar anim-fade-in-up stagger-6">
      <el-card>
        <div class="actions-content">
          <div class="actions-left">
            <span class="actions-title">快捷操作</span>
            <div v-if="lastBackupTime" class="backup-badge">
              <el-icon :size="14"><Clock /></el-icon>
              <span>上次备份: {{ lastBackupTime }}</span>
            </div>
          </div>
          <div class="actions-buttons">
            <el-button @click="$router.push('/customers')">
              <el-icon><Plus /></el-icon>
              新建客户
            </el-button>
            <el-button @click="$router.push('/projects')">
              <el-icon><Plus /></el-icon>
              新建项目
            </el-button>
            <el-button @click="$router.push('/contracts')">
              <el-icon><Plus /></el-icon>
              新建合同
            </el-button>
            <el-button type="primary" @click="handleBackup">
              <el-icon><Download /></el-icon>
              备份数据库
            </el-button>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  TrendCharts, Wallet, Coin, DataBoard,
  Calendar, Document, Clock, Plus, Download, Bell
} from '@element-plus/icons-vue'
import { getDashboard, getCustomerFunnel, getProjectStatus, getTodos, getRevenueTrend, backupDatabase } from '../api/dashboard'

const metrics = ref({ monthly_income: 0, monthly_expense: 0, monthly_profit: 0, active_projects: 0 })
const funnel = ref({})
const projectStatus = ref({})
const todos = ref({ tasks: [], expiring_contracts: [], reminders: [] })
const revenueTrend = ref([])
const lastBackupTime = ref('')

const stageLabels = { potential: '潜在客户', follow_up: '跟进中', deal: '成交', lost: '流失' }
const stageColors = { potential: '#94a3b8', follow_up: '#06b6d4', deal: '#10b981', lost: '#f43f5e' }
const statusLabels = { requirements: '需求', design: '设计', development: '开发', testing: '测试', delivery: '交付', paused: '暂停' }
const statusColors = { requirements: '#94a3b8', design: '#8b5cf6', development: '#06b6d4', testing: '#f59e0b', delivery: '#10b981', paused: '#ef4444' }

const metricCards = computed(() => [
  { key: 'income', label: '本月收入', value: metrics.value.monthly_income, prefix: '¥', color: '#10b981', glow: 'rgba(16, 185, 129, 0.12)', icon: TrendCharts },
  { key: 'expense', label: '本月支出', value: metrics.value.monthly_expense, prefix: '¥', color: '#f43f5e', glow: 'rgba(244, 63, 94, 0.10)', icon: Wallet },
  { key: 'profit', label: '本月利润', value: metrics.value.monthly_profit, prefix: '¥', color: metrics.value.monthly_profit >= 0 ? '#06b6d4' : '#f43f5e', glow: metrics.value.monthly_profit >= 0 ? 'rgba(6, 182, 212, 0.12)' : 'rgba(244, 63, 94, 0.10)', icon: Coin },
  { key: 'projects', label: '进行中项目', value: metrics.value.active_projects, prefix: '', color: '#8b5cf6', glow: 'rgba(139, 92, 246, 0.12)', icon: DataBoard },
])

const funnelItems = computed(() => {
  const entries = Object.entries(funnel.value)
  if (!entries.length) return []
  const max = Math.max(...entries.map(([, v]) => v), 1)
  return entries.map(([stage, count]) => ({
    stage, count,
    label: stageLabels[stage] || stage,
    color: stageColors[stage] || '#94a3b8',
    percent: Math.round((count / max) * 100),
  }))
})

const statusItems = computed(() => {
  const entries = Object.entries(projectStatus.value)
  if (!entries.length) return []
  const max = Math.max(...entries.map(([, v]) => v), 1)
  return entries.map(([status, count]) => ({
    status, count,
    label: statusLabels[status] || status,
    color: statusColors[status] || '#94a3b8',
    percent: Math.round((count / max) * 100),
  }))
})

const formatNumber = (n) => Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 0 })

const maxRevenue = computed(() => {
  if (!revenueTrend.value.length) return 1
  return Math.max(...revenueTrend.value.flatMap(r => [r.income, r.expense]), 1)
})

const barHeight = (value) => {
  if (!value) return 0
  return Math.max(Math.round((value / maxRevenue.value) * 100), 2)
}

const priorityLabel = (p) => ({ high: '高', medium: '中', low: '低' }[p] || p)
const priorityTagType = (p) => ({ high: 'danger', medium: 'warning', low: 'info' }[p] || 'info')

const daysLeft = (dateStr) => {
  if (!dateStr) return 0
  const diff = new Date(dateStr) - new Date()
  return Math.max(0, Math.ceil(diff / 86400000))
}

const reminderTypeLabel = (t) => ({
  annual_report: '年报', tax_filing: '税务', contract_expiry: '合同到期',
  task_deadline: '任务截止', file_expiry: '文件到期', custom: '自定义',
}[t] || t)

const reminderTypeTag = (t) => ({
  annual_report: 'danger', tax_filing: 'danger', contract_expiry: 'warning',
  task_deadline: 'warning', file_expiry: 'info', custom: '',
}[t] || 'info')

const loadData = async () => {
  try {
    const [dashRes, funnelRes, statusRes, todosRes, trendRes] = await Promise.all([
      getDashboard(), getCustomerFunnel(), getProjectStatus(), getTodos(), getRevenueTrend()
    ])
    metrics.value = dashRes.data
    funnel.value = funnelRes.data
    projectStatus.value = statusRes.data
    todos.value = todosRes.data
    revenueTrend.value = trendRes.data || []
  } catch { /* silently degrade */ }
}

const handleBackup = async () => {
  try {
    const { data } = await backupDatabase('./backups')
    lastBackupTime.value = data.timestamp
    ElMessage.success('备份成功: ' + data.backup_path)
  } catch {
    ElMessage.error('备份失败')
  }
}

onMounted(loadData)
</script>

<style scoped>
.dashboard {
  max-width: 1280px;
}

/* ---- Metric Cards ---- */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.metric-card {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 20px;
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
  overflow: hidden;
  transition: all var(--duration-normal) var(--ease-out);
}

.metric-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.metric-icon {
  width: 42px;
  height: 42px;
  border-radius: var(--radius-md);
  background: var(--card-glow);
  color: var(--card-color);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.metric-body {
  flex: 1;
  min-width: 0;
}

.metric-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.metric-bg-icon {
  position: absolute;
  right: -8px;
  bottom: -12px;
  color: var(--card-glow);
  opacity: 0.5;
  pointer-events: none;
}

/* ---- Chart Cards ---- */
.charts-row { margin-top: 20px; }

/* ---- Trend Chart ---- */
.trend-chart { padding: 4px 0; }

.trend-bars {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  height: 120px;
}

.trend-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
}

.trend-col-bars {
  flex: 1;
  display: flex;
  align-items: flex-end;
  gap: 2px;
  width: 100%;
}

.trend-bar {
  flex: 1;
  border-radius: 3px 3px 0 0;
  min-height: 2px;
  transition: height 0.6s var(--ease-out);
}

.income-bar { background: #10b981; }
.expense-bar { background: #f43f5e; opacity: 0.7; }

.trend-month {
  font-size: 10px;
  color: var(--text-tertiary);
  margin-top: 6px;
  white-space: nowrap;
}

.trend-legend {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.chart-card :deep(.el-card__header) {
  padding: 16px 20px 12px !important;
}

.card-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.card-subtitle {
  font-size: 12px;
  color: var(--text-tertiary);
}

/* ---- Funnel ---- */
.funnel-list { display: flex; flex-direction: column; gap: 14px; padding: 4px 0; }

.funnel-row {
  display: grid;
  grid-template-columns: 72px 1fr 40px;
  gap: 10px;
  align-items: center;
  animation: fadeInUp 0.4s var(--ease-out) both;
}

.funnel-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.funnel-bar-track {
  height: 8px;
  background: var(--border-subtle);
  border-radius: 4px;
  overflow: hidden;
}

.funnel-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.8s var(--ease-out);
}

.funnel-count {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  text-align: right;
}

/* ---- Status ---- */
.status-list { display: flex; flex-direction: column; gap: 12px; padding: 4px 0; }

.status-row {
  display: grid;
  grid-template-columns: 8px 56px 1fr 32px;
  gap: 8px;
  align-items: center;
  animation: fadeInUp 0.4s var(--ease-out) both;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.status-bar-track {
  height: 6px;
  background: var(--border-subtle);
  border-radius: 3px;
  overflow: hidden;
}

.status-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.8s var(--ease-out);
}

.status-count {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  text-align: right;
}

/* ---- Todo ---- */
.todo-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-subtle);
}

.todo-row:last-child { border-bottom: none; }

.todo-priority {
  width: 4px;
  height: 28px;
  border-radius: 2px;
  flex-shrink: 0;
}

.todo-priority.urgent { background: var(--brand-rose); }
.todo-priority.high { background: #ef4444; }
.todo-priority.medium { background: var(--brand-amber); }
.todo-priority.low { background: #94a3b8; }

.todo-content {
  flex: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.todo-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.todo-tag {
  font-size: 11px;
  padding: 0 6px;
  height: 18px;
  line-height: 18px;
}

.todo-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.todo-due {
  font-size: 12px;
  color: var(--text-tertiary);
}

/* ---- Contract ---- */
.contract-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-subtle);
}

.contract-row:last-child { border-bottom: none; }

.contract-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.contract-no {
  font-size: 11px;
  color: var(--text-tertiary);
}

.contract-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.contract-date {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.contract-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.contract-countdown {
  font-size: 11px;
}

/* ---- Reminder ---- */
.reminder-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-subtle);
}

.reminder-row:last-child { border-bottom: none; }

.reminder-row.overdue {
  background: rgba(244, 63, 94, 0.04);
  border-radius: 6px;
  padding: 10px 8px;
  margin: 0 -8px;
}

.reminder-indicator {
  width: 4px;
  height: 28px;
  border-radius: 2px;
  flex-shrink: 0;
}

.reminder-indicator.overdue { background: var(--brand-rose); }
.reminder-indicator.pending { background: var(--brand-amber); }

.reminder-content {
  flex: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.reminder-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.reminder-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.reminder-tag {
  font-size: 11px;
  padding: 0 6px;
  height: 18px;
  line-height: 18px;
}

.reminder-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.reminder-date {
  font-size: 12px;
  color: var(--text-tertiary);
}

/* ---- Empty State ---- */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 24px 0;
  color: var(--text-tertiary);
}

.empty-state p {
  font-size: 13px;
  margin: 0;
}

/* ---- Quick Actions ---- */
.quick-actions-bar { margin-top: 20px; }

.actions-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.actions-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.actions-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.backup-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--brand-emerald);
  background: var(--brand-emerald-glow);
  padding: 4px 10px;
  border-radius: 20px;
}

.actions-buttons {
  display: flex;
  gap: 8px;
}

/* ---- Responsive ---- */
@media (max-width: 900px) {
  .metrics-grid { grid-template-columns: repeat(2, 1fr); }
  .actions-content { flex-direction: column; gap: 16px; align-items: flex-start; }
}

@media (max-width: 600px) {
  .metrics-grid { grid-template-columns: 1fr; }
}
</style>
