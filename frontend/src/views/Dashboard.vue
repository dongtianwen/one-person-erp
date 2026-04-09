<template>
  <div class="dashboard">
    <!-- Metric Cards -->
    <div class="metrics-grid">
      <div
        v-for="(card, idx) in metricCards"
        :key="card.key"
        class="metric-card anim-fade-in-up"
        :class="[`stagger-${idx + 1}`, { clickable: true }]"
        :style="{ '--card-color': card.color, '--card-glow': card.glow, cursor: 'pointer' }"
        @click="goToCard(card.key)"
      >
        <div class="metric-icon">
          <el-icon :size="22"><component :is="card.icon" /></el-icon>
        </div>
        <div class="metric-body">
          <div class="metric-label">{{ card.label }}</div>
          <div class="metric-value mono">{{ card.prefix }}{{ formatNumber(card.value) }}{{ card.suffix || '' }}</div>
        </div>
        <div class="metric-bg-icon">
          <el-icon :size="64"><component :is="card.icon" /></el-icon>
        </div>
      </div>
    </div>

    <!-- 现金流30天预警 -->
    <el-alert
      v-if="cashflow30dWarning"
      :title="cashflow30dWarning"
      type="error"
      show-icon
      :closable="false"
      style="margin-top: 16px"
    />

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

    <!-- v1.3 Cashflow Forecast + Tax Summary -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="16">
        <el-card class="anim-fade-in-up">
          <template #header>
            <div class="card-header">
              <span class="card-title">现金流预测</span>
              <span class="card-subtitle">未来90天收支趋势</span>
            </div>
          </template>
          <div v-if="cashflowError" class="empty-state">
            <p style="color: var(--brand-rose)">{{ cashflowError }}</p>
          </div>
          <div v-else-if="!cashflowData.forecast.length" class="empty-state">
            <el-icon :size="32" color="var(--text-tertiary)"><TrendCharts /></el-icon>
            <p>暂无数据</p>
          </div>
          <div v-else class="cashflow-chart">
            <div class="cashflow-bars">
              <div v-for="(week, idx) in cashflowData.forecast" :key="idx" class="cashflow-col">
                <div class="cashflow-col-bars">
                  <div class="cashflow-bar income-bar" :style="{ height: cfBarHeight(week.income) + '%' }" :title="'收入: ¥' + formatNumber(week.income)" />
                  <div class="cashflow-bar expense-bar" :style="{ height: cfBarHeight(week.expense) + '%' }" :title="'支出: ¥' + formatNumber(week.expense)" />
                  <div class="cashflow-bar net-bar" :style="{ height: cfBarHeight(week.net) + '%', background: week.net >= 0 ? '#06b6d4' : '#f43f5e' }" :title="'净额: ¥' + formatNumber(week.net)" />
                </div>
                <div class="cashflow-week">W{{ idx + 1 }}</div>
              </div>
            </div>
            <div class="trend-legend">
              <span class="legend-item"><i class="legend-dot" style="background:#10b981" />收入</span>
              <span class="legend-item"><i class="legend-dot" style="background:#f43f5e" />支出</span>
              <span class="legend-item"><i class="legend-dot" style="background:#06b6d4" />净额</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card class="anim-fade-in-up" v-loading="taxLoading">
          <template #header>
            <div class="card-header">
              <span class="card-title">季度增值税汇总</span>
              <div class="tax-quarter-select">
                <el-select v-model="taxQuarter" size="small" style="width: 140px" @change="loadTaxSummary">
                  <el-option v-for="q in [1,2,3,4]" :key="q" :label="`${taxYear}年 Q${q}`" :value="q" />
                </el-select>
              </div>
            </div>
          </template>
          <div class="tax-summary-grid">
            <div class="tax-item">
              <div class="tax-label">销项税额</div>
              <div class="tax-value mono positive">¥{{ Number(taxSummary.output_tax_total || 0).toFixed(2) }}</div>
            </div>
            <div class="tax-item">
              <div class="tax-label">进项税额</div>
              <div class="tax-value mono" style="color: #f43f5e">¥{{ Number(taxSummary.input_tax_total || 0).toFixed(2) }}</div>
            </div>
            <div class="tax-item highlight">
              <div class="tax-label">应纳税额</div>
              <div class="tax-value mono" :style="{ color: (taxSummary.tax_payable || 0) >= 0 ? '#06b6d4' : '#f43f5e' }">¥{{ Number(taxSummary.tax_payable || 0).toFixed(2) }}</div>
            </div>
          </div>
          <div class="tax-disclaimer">* 数据仅供参考，实际申报以税务机关为准</div>
        </el-card>
      </el-col>
    </el-row>

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

    <!-- v1.7 WIP 看板 -->
    <el-card class="anim-fade-in-up" style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <span class="card-title">进行中项目 (WIP)</span>
          <el-tag v-if="wipProjects.length" size="small" type="primary" round>{{ wipProjects.length }} 个</el-tag>
        </div>
      </template>
      <!-- v1.7 WIP 超限警告 -->
      <el-alert
        v-if="wipProjects.length > 2"
        type="warning"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
      >
        <template #title>
          当前有 {{ wipProjects.length }} 个项目并行，注意精力分配
        </template>
      </el-alert>
      <div v-if="!wipProjects.length" class="empty-state">
        <el-icon :size="32" color="var(--text-tertiary)"><DataBoard /></el-icon>
        <p>暂无进行中的项目</p>
      </div>
      <el-table v-else :data="wipProjects" stripe size="small">
        <el-table-column prop="name" label="项目名称" min-width="160" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusTypes[row.status] || 'info'" size="small">
              {{ statusLabels[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="120">
          <template #default="{ row }">
            <div class="progress-cell">
              <el-progress
                :percentage="row.progress || 0"
                :stroke-width="6"
                :color="progressColor(row.progress)"
                :show-text="false"
              />
              <span class="progress-label mono">{{ row.progress || 0 }}%</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="start_date" label="开始日期" width="100">
          <template #default="{ row }">
            <span class="mono">{{ row.start_date || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="end_date" label="结束日期" width="100">
          <template #default="{ row }">
            <span class="mono">{{ row.end_date || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="goToProject(row.id)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

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

    <!-- Backup History -->
    <el-card v-if="backups.length" class="anim-fade-in-up" style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <span class="card-title">备份历史</span>
          <el-tag size="small" round>{{ backups.length }} 个文件</el-tag>
        </div>
      </template>
      <el-table :data="backups" style="width: 100%" size="small">
        <el-table-column prop="filename" label="文件名" min-width="200">
          <template #default="{ row }">
            <span class="mono" style="font-size: 12px">{{ row.filename }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="size" label="大小" width="100">
          <template #default="{ row }">
            <span class="mono">{{ formatFileSize(row.size) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="备份时间" width="180">
          <template #default="{ row }">
            <span class="mono" style="font-size: 12px">{{ row.created_at?.replace('T', ' ') }}</span>
          </template>
        </el-table-column>
        <el-table-column label="校验状态" width="120">
          <template #default="{ row }">
            <el-tag v-if="!row.verification" type="info" size="small" round>未校验</el-tag>
            <el-tag v-else-if="row.verification.valid" type="success" size="small" round>通过</el-tag>
            <el-tag v-else type="danger" size="small" round>失败</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleVerify(row.filename)" :loading="verifyingId === row.filename">
              校验
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  TrendCharts, Wallet, Coin, DataBoard, Tickets,
  Calendar, Document, Clock, Plus, Download, Bell
} from '@element-plus/icons-vue'
import { getDashboard, getCustomerFunnel, getProjectStatus, getTodos, getRevenueTrend, backupDatabase, listBackups, verifyBackup, getCashflowForecast, getTaxSummary } from '../api/dashboard'
import { getProjects } from '../api/projects'

const functor = ref(null)
const router = useRouter()

const metrics = ref({ monthly_income: 0, monthly_expense: 0, monthly_profit: 0, active_projects: 0, customer_conversion_rate: 0, quotation_conversion_rate: 0, sent_this_month: 0 })
// v1.8 财务指标
const financialMetrics = ref({ monthly_invoiced: 0, monthly_received: 0, accounts_receivable: 0, unbilled_amount: 0 })
const funnel = ref({})
const projectStatus = ref({})
const todos = ref({ tasks: [], expiring_contracts: [], reminders: [] })
const revenueTrend = ref([])
const lastBackupTime = ref('')
const backups = ref([])
const verifyingId = ref(null)
const cashflowData = ref({ forecast: [], summary: {} })
const taxSummary = ref({ output_tax_total: 0, input_tax_total: 0, tax_payable: 0 })
const taxLoading = ref(false)

// v1.7 WIP 看板
const wipProjects = ref([])

const stageLabels = { potential: '潜在客户', follow_up: '跟进中', deal: '成交', lost: '流失' }
const stageColors = { potential: '#94a3b8', follow_up: '#06b6d4', deal: '#10b981', lost: '#f43f5e' }
const statusLabels = { requirements: '需求', design: '设计', development: '开发', testing: '测试', delivery: '交付', paused: '暂停', completed: '已完成' }
const statusColors = { requirements: '#94a3b8', design: '#8b5cf6', development: '#06b6d4', testing: '#f59e0b', delivery: '#10b981', paused: '#ef4444', completed: '#10b981' }
const statusTypes = { requirements: 'info', design: '', development: 'primary', testing: 'warning', delivery: 'success', paused: 'info', completed: 'success' }

const metricCards = computed(() => [
  { key: 'income', label: '本月收入', value: metrics.value.monthly_income, prefix: '¥', color: '#10b981', glow: 'rgba(16, 185, 129, 0.12)', icon: TrendCharts },
  { key: 'expense', label: '本月支出', value: metrics.value.monthly_expense, prefix: '¥', color: '#f43f5e', glow: 'rgba(244, 63, 94, 0.10)', icon: Wallet },
  { key: 'profit', label: '本月利润', value: metrics.value.monthly_profit, prefix: '¥', color: metrics.value.monthly_profit >= 0 ? '#06b6d4' : '#f43f5e', glow: metrics.value.monthly_profit >= 0 ? 'rgba(6, 182, 212, 0.12)' : 'rgba(244, 63, 94, 0.10)', icon: Coin },
  { key: 'projects', label: '进行中项目', value: metrics.value.active_projects, prefix: '', color: '#8b5cf6', glow: 'rgba(139, 92, 246, 0.12)', icon: DataBoard },
  { key: 'quotation_rate', label: '报价转化率', value: metrics.value.quotation_conversion_rate || 0, prefix: '', suffix: '%', color: '#f59e0b', glow: 'rgba(245, 158, 11, 0.12)', icon: Tickets },
  { key: 'sent_this_month', label: '本月发出报价', value: metrics.value.sent_this_month || 0, prefix: '', color: '#06b6d4', glow: 'rgba(6, 182, 212, 0.12)', icon: Tickets },
  // v1.8 财务指标
  { key: 'monthly_invoiced', label: '本月开票', value: financialMetrics.value.monthly_invoiced, prefix: '¥', color: '#8b5cf6', glow: 'rgba(139, 92, 246, 0.12)', icon: Tickets },
  { key: 'monthly_received', label: '本月收款', value: financialMetrics.value.monthly_received, prefix: '¥', color: '#10b981', glow: 'rgba(16, 185, 129, 0.12)', icon: Wallet },
  { key: 'accounts_receivable', label: '应收账款', value: financialMetrics.value.accounts_receivable, prefix: '¥', color: '#f59e0b', glow: 'rgba(245, 158, 11, 0.12)', icon: Coin },
  { key: 'unbilled_amount', label: '未开票金额', value: financialMetrics.value.unbilled_amount, prefix: '¥', color: '#06b6d4', glow: 'rgba(6, 182, 212, 0.12)', icon: DataBoard },
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

// v1.8 加载财务指标
const loadFinancialMetrics = async () => {
  try {
    const { getInvoiceSummary } = await import('../api/v18')
    const now = new Date()
    const year = now.getFullYear()
    const month = String(now.getMonth() + 1).padStart(2, '0')
    const period = `${year}-${month}`

    // 获取本月发票汇总
    const summary = await getInvoiceSummary({ accounting_period: period })
    const monthlyInvoiced = (summary.verified?.total_amount || 0) + (summary.received?.total_amount || 0) + (summary.issued?.total_amount || 0)

    // 获取收款数据（从 dashboard metrics）
    const monthlyReceived = metrics.value.monthly_income || 0

    // 计算应收账款（合同总额 - 已收款）
    const accountsReceivable = Math.max(0, (metrics.value.total_contract_amount || 0) - (metrics.value.total_received || 0))

    // 计算未开票金额（合同总额 - 已开票）
    const totalInvoiced = (summary.verified?.total_amount || 0) + (summary.received?.total_amount || 0) + (summary.issued?.total_amount || 0) + (summary.draft?.total_amount || 0)
    const unbilledAmount = Math.max(0, (metrics.value.total_contract_amount || 0) - Number(totalInvoiced))

    financialMetrics.value = {
      monthly_invoiced: Number(monthlyInvoiced) || 0,
      monthly_received: monthlyReceived,
      accounts_receivable: accountsReceivable,
      unbilled_amount: unbilledAmount
    }
  } catch (err) {
    console.error('Failed to load financial metrics:', err)
    // 默认值
    financialMetrics.value = { monthly_invoiced: 0, monthly_received: 0, accounts_receivable: 0, unbilled_amount: 0 }
  }
}

// v1.7 加载 WIP 项目
const loadWipProjects = async () => {
  try {
    const { data } = await getProjects()
    // 过滤出进行中的项目（status !== 'completed' 且 status !== 'paused'）
    wipProjects.value = (data?.items || data || []).filter(p => p.status !== 'completed' && p.status !== 'paused')
  } catch {
    wipProjects.value = []
  }
}

const progressColor = (p) => {
  if (p >= 100) return '#10b981'
  if (p >= 70) return '#06b6d4'
  if (p >= 40) return '#f59e0b'
  return '#94a3b8'
}

const goToProject = (projectId) => {
  router.push({ path: '/projects', query: { id: projectId } })
}

// v1.3 现金流预测
const cashflowError = ref('')
const cashflow30dWarning = computed(() => {
  const net30d = cashflowData.value.summary?.net_30d
  if (net30d === undefined || net30d === null || net30d >= 0) return ''
  return `未来30天现金流预警：预计净流出 ¥${formatNumber(Math.abs(net30d))}，建议关注资金安排`
})
const cfMaxValue = computed(() => {
  if (!cashflowData.value.forecast.length) return 1
  return Math.max(...cashflowData.value.forecast.flatMap(w => [Math.abs(w.income || 0), Math.abs(w.expense || 0), Math.abs(w.net || 0)]), 1)
})
const cfBarHeight = (value) => {
  if (!value) return 0
  return Math.max(Math.round((Math.abs(value) / cfMaxValue.value) * 100), 2)
}
const loadCashflowForecast = async () => {
  try {
    const { data } = await getCashflowForecast()
    // API 返回 predicted_income/predicted_expense/predicted_net，前端使用 income/expense/net
    const forecast = (data.forecast || []).map(w => ({
      ...w,
      income: w.predicted_income || w.income || 0,
      expense: w.predicted_expense || w.expense || 0,
      net: w.predicted_net || w.net || 0,
    }))
    cashflowData.value = { forecast, summary: data.summary || {} }
    cashflowError.value = ''
  } catch (e) {
    cashflowError.value = '加载现金流预测失败'
    cashflowData.value = { forecast: [], summary: {} }
  }
}

// v1.3 季度增值税
const now = new Date()
const taxYear = ref(now.getFullYear())
const taxQuarter = ref(Math.ceil((now.getMonth() + 1) / 3))
const loadTaxSummary = async () => {
  taxLoading.value = true
  try {
    const { data } = await getTaxSummary(taxYear.value, taxQuarter.value)
    taxSummary.value = data
  } catch {
    taxSummary.value = { output_tax_total: 0, input_tax_total: 0, tax_payable: 0 }
  } finally {
    taxLoading.value = false
  }
}

const handleBackup = async () => {
  try {
    const { data } = await backupDatabase('./backups')
    lastBackupTime.value = data.timestamp
    ElMessage.success('备份成功: ' + data.backup_path)
    loadBackups()
  } catch {
    ElMessage.error('备份失败')
  }
}

const loadBackups = async () => {
  try {
    const { data } = await listBackups()
    backups.value = data
  } catch { /* ignore */ }
}

const goToCard = (key) => {
  if (['projects', 'quotation_rate', 'sent_this_month'].includes(key)) {
    router.push('/quotations')
  } else if (['income', 'expense', 'profit'].includes(key)) {
    router.push('/finances')
  } else {
    router.push('/projects')
  }
}

const handleVerify = async (filename) => {
  verifyingId.value = filename
  try {
    const { data } = await verifyBackup(filename)
    if (data.valid) {
      ElMessage.success('备份校验通过')
    } else {
      ElMessage.warning('备份校验发现问题: ' + (data.error || '部分表记录数不一致'))
    }
    loadBackups()
  } catch {
    ElMessage.error('校验失败')
  } finally {
    verifyingId.value = null
  }
}

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

onMounted(() => { loadData(); loadBackups(); loadCashflowForecast(); loadTaxSummary(); loadWipProjects(); loadFinancialMetrics() })
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

/* ---- Cashflow Chart ---- */
.cashflow-chart { padding: 4px 0; }

.cashflow-bars {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  height: 120px;
}

.cashflow-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
}

.cashflow-col-bars {
  flex: 1;
  display: flex;
  align-items: flex-end;
  gap: 2px;
  width: 100%;
}

.cashflow-bar {
  flex: 1;
  border-radius: 3px 3px 0 0;
  min-height: 2px;
  transition: height 0.6s var(--ease-out);
}

.cashflow-bar.income-bar { background: #10b981; }
.cashflow-bar.expense-bar { background: #f43f5e; opacity: 0.7; }
.cashflow-bar.net-bar { opacity: 0.8; }

.cashflow-week {
  font-size: 10px;
  color: var(--text-tertiary);
  margin-top: 6px;
  white-space: nowrap;
}

/* ---- Tax Summary ---- */
.tax-quarter-select {
  margin-left: auto;
}

.tax-summary-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 4px 0;
}

.tax-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--el-fill-color-lighter);
  border-radius: 8px;
}

.tax-item.highlight {
  background: var(--el-fill-color-light);
  border: 1px solid var(--border-default);
}

.tax-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.tax-value {
  font-size: 18px;
  font-weight: 700;
}

.tax-value.positive { color: var(--brand-emerald); }

.tax-disclaimer {
  margin-top: 12px;
  font-size: 11px;
  color: var(--text-tertiary);
  text-align: center;
}

/* ---- WIP Progress Cell ---- */
.wip-progress-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.wip-progress-cell :deep(.el-progress) {
  flex: 1;
}

.wip-progress-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  min-width: 32px;
  text-align: right;
}

.progress-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-cell :deep(.el-progress) {
  flex: 1;
}

.progress-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  min-width: 32px;
  text-align: right;
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
