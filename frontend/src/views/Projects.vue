<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-title-group">
        <span class="header-count mono">总计：{{ projects.length }} 个项目</span>
        <PageHelpDrawer pageKey="project_detail" />
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新建项目
      </el-button>
    </div>

    <el-card>
      <div class="filter-bar">
        <el-input
          v-model="searchQuery"
          placeholder="搜索项目名称或描述..."
          style="width: 250px"
          clearable
          :prefix-icon="Search"
          @clear="loadData"
          @keyup.enter="loadData"
        />
        <el-select v-model="statusFilter" placeholder="按状态筛选" clearable style="width: 160px" @change="loadData">
          <el-option v-for="(label, val) in statusLabels" :key="val" :label="label" :value="val" />
        </el-select>
        <el-button type="primary" @click="loadData">查询</el-button>
      </div>

      <el-table :data="projects" style="width: 100%" v-loading="loading">
        <el-table-column type="selection" width="40" />
        <el-table-column prop="name" label="项目名称" min-width="160">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px;">
              <div class="status-dot-wrapper">
                <div class="status-dot" :class="statusTypes[row.status] || 'info'"></div>
                <span class="status-dot-text">{{ statusLabels[row.status] || row.status }}</span>
              </div>
              <span class="cell-name">{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="budget" label="预算" width="90" align="right">
          <template #default="{ row }">
            <span class="mono">{{ row.budget != null ? '¥' + Number(row.budget).toLocaleString() : '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="profit" label="利润" width="90" align="right" sortable>
          <template #default="{ row }">
            <span class="mono" :class="{ negative: row.profit != null && row.profit < 0 }">
              {{ row.profit != null ? '¥' + Number(row.profit).toLocaleString() : '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="profit_margin" label="利润率" width="100" align="right" sortable>
          <template #default="{ row }">
            <span class="mono" :class="{ negative: row.profit_margin != null && row.profit_margin < 0 }">
              {{ row.profit_margin != null ? row.profit_margin.toFixed(2) + '%' : '—' }}
            </span>
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
        <el-table-column label="时间" width="180">
          <template #default="{ row }">
            <div class="date-range mono">
              <span>{{ row.start_date || '-' }}</span>
              <span class="date-sep">&rarr;</span>
              <span>{{ row.end_date || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <div class="action-btns">
              <el-button link type="primary" size="small" @click="openDetail(row)">管理</el-button>
              <el-button link type="primary" size="small" @click="editProject(row)">编辑</el-button>
              <el-dropdown trigger="click" placement="bottom-end">
                <el-button link type="info" size="small">
                  <el-icon><MoreFilled /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item @click="handleDelete(row.id)" style="color: var(--el-color-danger)">删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showDialog" :title="editingId ? '编辑项目' : '新建项目'" width="600px" destroy-on-close>
      <el-form :model="form" label-position="top">
        <el-form-item label="项目名称" required>
          <el-input v-model="form.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="关联客户" required>
          <el-select v-model="form.customer_id" placeholder="选择客户" filterable style="width: 100%">
            <el-option v-for="c in customers" :key="c.id" :label="`${c.name} (${c.company || '无公司'})`" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="项目描述（选填）" />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="状态">
            <el-select v-model="form.status" style="width: 100%">
              <el-option v-for="(label, val) in statusLabels" :key="val" :label="label" :value="val" />
            </el-select>
          </el-form-item>
          <el-form-item label="预算">
            <el-input-number v-model="form.budget" :min="0" :precision="2" style="width: 100%" />
          </el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item label="开始日期">
            <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="结束日期">
            <el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">{{ editingId ? '保存修改' : '创建项目' }}</el-button>
      </template>
    </el-dialog>

    <!-- Project Detail Dialog -->
    <el-dialog v-model="showDetail" :title="detailProject?.name || '项目详情'" width="780px" destroy-on-close top="5vh">
      <div class="detail-header" v-if="detailProject">
        <div class="detail-meta">
          <el-tag :type="statusTypes[detailProject.status] || 'info'" size="small" round>
            {{ statusLabels[detailProject.status] || detailProject.status }}
          </el-tag>
          <span class="detail-budget mono" v-if="detailProject.budget">¥{{ detailProject.budget.toLocaleString() }}</span>
          <span class="detail-progress mono">{{ detailProject.progress || 0 }}%</span>
          <!-- v1.7 关闭项目按钮 -->
          <el-button
            v-if="detailProject.status !== 'completed'"
            type="danger"
            size="small"
            plain
            @click="openCloseCheck"
          >
            关闭项目
          </el-button>
          <el-tag v-else type="success" size="small" round>已完成</el-tag>
        </div>
      </div>

      <!-- Profit Analysis Card -->
      <el-card v-if="detailProject" class="profit-card" style="margin: 16px 0; padding: 16px;">
        <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
          <span class="card-title">利润分析</span>
          <el-button size="small" @click="handleRefreshProfit" :loading="profitRefreshing">刷新计算</el-button>
        </div>
        <!-- v1.9 warnings -->
        <el-alert
          v-if="profitWarnings.length"
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom: 12px;"
        >
          <template #title>
            <span v-for="(w, i) in profitWarnings" :key="i">{{ w }}；</span>
          </template>
        </el-alert>
        <div class="card-body">
          <div class="profit-grid">
            <div class="profit-item">
              <span class="profit-label">实收金额</span>
              <span class="profit-value">{{ profitData.revenue?.received_amount != null ? '¥' + Number(profitData.revenue.received_amount).toLocaleString() : '¥0.00' }}</span>
              <span class="profit-sub">合同额: {{ profitData.revenue?.contract_amount != null ? '¥' + Number(profitData.revenue.contract_amount).toLocaleString() : '—' }}</span>
            </div>
            <div class="profit-item">
              <span class="profit-label">人力成本</span>
              <span class="profit-value">{{ profitData.cost?.labor_cost != null ? '¥' + Number(profitData.cost.labor_cost).toLocaleString() : '—' }}</span>
              <span class="profit-sub">{{ profitData.cost?.labor_cost != null ? '' : '无工时数据' }}</span>
            </div>
            <div class="profit-item">
              <span class="profit-label">固定成本</span>
              <span class="profit-value">{{ profitData.cost?.fixed_cost_allocated != null ? '¥' + Number(profitData.cost.fixed_cost_allocated).toLocaleString() : '¥0.00' }}</span>
            </div>
            <div class="profit-item">
              <span class="profit-label">进项发票</span>
              <span class="profit-value">{{ profitData.cost?.input_invoice_cost != null ? '¥' + Number(profitData.cost.input_invoice_cost).toLocaleString() : '¥0.00' }}</span>
            </div>
            <div class="profit-item highlight">
              <span class="profit-label">粗利润</span>
              <span class="profit-value" :class="{ negative: profitData.profit?.gross_profit < 0 }">
                {{ profitData.profit?.gross_profit != null ? '¥' + Number(profitData.profit.gross_profit).toLocaleString() : '—' }}
              </span>
            </div>
            <div class="profit-item">
              <span class="profit-label">毛利率</span>
              <span class="profit-value" :class="{ negative: profitData.profit?.gross_margin != null && profitData.profit.gross_margin < 0 }">
                {{ profitData.profit?.gross_margin != null ? (profitData.profit.gross_margin * 100).toFixed(2) + '%' : '—' }}
              </span>
            </div>
          </div>
        </div>
      </el-card>

      <el-tabs v-model="detailTab" class="detail-tabs">
        <!-- 当前线上版本显示 -->
        <div v-if="detailProject" class="detail-version">
          当前线上版本：<span class="mono">{{ detailProject.current_version || '未发布' }}</span>
        </div>

        <!-- Tasks Tab -->
        <el-tab-pane label="任务" name="tasks">
          <div class="tab-toolbar">
            <el-button type="primary" size="small" @click="openTaskCreate">
              <el-icon><Plus /></el-icon> 新建任务
            </el-button>
          </div>
          <div v-if="tasks.length === 0" class="empty-hint">暂无任务，点击上方按钮创建</div>
          <div v-else class="task-list">
            <div v-for="t in tasks" :key="t.id" class="task-item" :class="'priority-' + t.priority">
              <div class="task-left">
                <el-tag
                  :type="taskStatusType[t.status] || 'info'"
                  size="small"
                  class="task-status"
                  @click="cycleTaskStatus(t)"
                  style="cursor: pointer"
                >
                  {{ taskStatusLabel[t.status] || t.status }}
                </el-tag>
                <span class="task-title">{{ t.title }}</span>
                <span v-if="t.assignee" class="task-assignee">{{ t.assignee }}</span>
              </div>
              <div class="task-right">
                <span v-if="t.due_date" class="task-date mono">{{ t.due_date }}</span>
                <el-button link type="primary" size="small" @click="openTaskEdit(t)">编辑</el-button>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- Milestones Tab -->
        <el-tab-pane label="里程碑" name="milestones">
          <div class="tab-toolbar">
            <el-button type="primary" size="small" @click="openMilestoneCreate">
              <el-icon><Plus /></el-icon> 新建里程碑
            </el-button>
          </div>
          <div v-if="milestones.length === 0" class="empty-hint">暂无里程碑</div>
          <div v-else class="milestone-list">
            <div v-for="m in milestones" :key="m.id" class="milestone-item" :class="{ completed: m.is_completed }">
              <el-checkbox
                :model-value="m.is_completed"
                @change="toggleMilestone(m)"
                class="milestone-check"
              />
              <div class="milestone-body">
                <span class="milestone-title">{{ m.title }}</span>
                <span class="milestone-date mono">截止 {{ m.due_date }}</span>
                <span v-if="m.is_completed && m.completed_date" class="milestone-done mono">
                  完成于 {{ m.completed_date }}
                </span>
              </div>
              <el-button link type="primary" size="small" @click="openMilestoneEdit(m)">编辑</el-button>
            </div>
          </div>
        </el-tab-pane>

        <!-- v1.5 新增 Tabs -->
        <el-tab-pane label="需求" name="requirements">
          <RequirementsTab :project-id="detailProject?.id" />
        </el-tab-pane>
        <el-tab-pane label="验收" name="acceptances">
          <AcceptancesTab :project-id="detailProject?.id" />
        </el-tab-pane>
        <el-tab-pane label="交付物" name="deliverables">
          <DeliverablesTab :project-id="detailProject?.id" />
        </el-tab-pane>
        <el-tab-pane label="版本" name="releases">
          <ReleasesTab :project-id="detailProject?.id" />
        </el-tab-pane>
        <el-tab-pane label="售后" name="maintenance">
          <MaintenanceTab :project-id="detailProject?.id" />
        </el-tab-pane>
        <el-tab-pane label="变更单摘要" name="change-orders">
          <ChangeOrderSummary :project-id="detailProject?.id" />
        </el-tab-pane>

        <!-- v1.7 新增 Tabs -->
        <el-tab-pane label="变更单管理" name="change-orders-v17">
          <ChangeOrdersTab :project-id="detailProject?.id" />
        </el-tab-pane>
        <el-tab-pane label="里程碑收款" name="milestone-payment">
          <MilestonePaymentTab :project-id="detailProject?.id" />
        </el-tab-pane>
        <el-tab-pane label="工时记录" name="work-hours">
          <WorkHoursTab :project-id="detailProject?.id" />
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <!-- Task Form Dialog -->
    <el-dialog v-model="showTaskForm" :title="editingTaskId ? '编辑任务' : '新建任务'" width="480px" destroy-on-close append-to-body>
      <el-form :model="taskForm" label-position="top">
        <el-form-item label="任务标题" required>
          <el-input v-model="taskForm.title" placeholder="请输入任务标题" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="taskForm.description" type="textarea" :rows="2" placeholder="任务描述（选填）" />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="状态">
            <el-select v-model="taskForm.status" style="width: 100%">
              <el-option v-for="(label, val) in taskStatusLabel" :key="val" :label="label" :value="val" />
            </el-select>
          </el-form-item>
          <el-form-item label="优先级">
            <el-select v-model="taskForm.priority" style="width: 100%">
              <el-option label="低" value="low" />
              <el-option label="中" value="medium" />
              <el-option label="高" value="high" />
            </el-select>
          </el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item label="负责人">
            <el-input v-model="taskForm.assignee" placeholder="选填" />
          </el-form-item>
          <el-form-item label="截止日期">
            <el-date-picker v-model="taskForm.due_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="showTaskForm = false">取消</el-button>
        <el-button type="primary" @click="handleTaskSubmit">{{ editingTaskId ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>

    <!-- Milestone Form Dialog -->
    <el-dialog v-model="showMilestoneForm" :title="editingMilestoneId ? '编辑里程碑' : '新建里程碑'" width="480px" destroy-on-close append-to-body>
      <el-form :model="milestoneForm" label-position="top">
        <el-form-item label="里程碑标题" required>
          <el-input v-model="milestoneForm.title" placeholder="请输入里程碑标题" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="milestoneForm.description" type="textarea" :rows="2" placeholder="里程碑描述（选填）" />
        </el-form-item>
        <el-form-item label="截止日期" required>
          <el-date-picker v-model="milestoneForm.due_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showMilestoneForm = false">取消</el-button>
        <el-button type="primary" @click="handleMilestoneSubmit">{{ editingMilestoneId ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>

    <!-- v1.7 关闭项目检查对话框 -->
    <el-dialog
      v-model="closeCheckDialogVisible"
      title="项目关闭条件检查"
      width="500px"
      destroy-on-close
    >
      <div v-if="closeCheckData" v-loading="closeLoading">
        <el-alert
          :type="closeCheckData.can_close ? 'success' : 'warning'"
          :closable="false"
          show-icon
          style="margin-bottom: 16px"
        >
          <template #title>
            {{ closeCheckData.can_close ? '满足关闭条件，可以关闭项目' : '不满足关闭条件，请先完成以下项目' }}
          </template>
        </el-alert>

        <div class="close-checklist">
          <div class="checklist-item" :class="{ passed: closeCheckData.all_milestones_completed }">
            <el-icon :class="closeCheckData.all_milestones_completed ? 'success-color' : 'warning-color'">
              <CircleCheck v-if="closeCheckData.all_milestones_completed" />
              <CircleClose v-else />
            </el-icon>
            <span class="checklist-label">所有里程碑已完成</span>
          </div>
          <div class="checklist-item" :class="{ passed: closeCheckData.final_acceptance_passed }">
            <el-icon :class="closeCheckData.final_acceptance_passed ? 'success-color' : 'warning-color'">
              <CircleCheck v-if="closeCheckData.final_acceptance_passed" />
              <CircleClose v-else />
            </el-icon>
            <span class="checklist-label">最终验收已通过</span>
          </div>
          <div class="checklist-item" :class="{ passed: closeCheckData.payment_cleared }">
            <el-icon :class="closeCheckData.payment_cleared ? 'success-color' : 'warning-color'">
              <CircleCheck v-if="closeCheckData.payment_cleared" />
              <CircleClose v-else />
            </el-icon>
            <span class="checklist-label">款项已结清</span>
          </div>
          <div class="checklist-item" :class="{ passed: closeCheckData.deliverables_archived }">
            <el-icon :class="closeCheckData.deliverables_archived ? 'success-color' : 'warning-color'">
              <CircleCheck v-if="closeCheckData.deliverables_archived" />
              <CircleClose v-else />
            </el-icon>
            <span class="checklist-label">交付物已归档</span>
          </div>
          <div v-if="closeCheckData.blocking_items?.length > 0" class="blocking-items">
            <div class="blocking-title">阻塞项：</div>
            <div v-for="(item, idx) in closeCheckData.blocking_items" :key="idx" class="blocking-item">
              • {{ item }}
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="closeCheckDialogVisible = false">取消</el-button>
        <el-button
          type="danger"
          @click="handleClose"
          :loading="closeLoading"
          :disabled="!closeCheckData?.can_close"
        >
          确认关闭
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, MoreFilled, CircleCheck, CircleClose } from '@element-plus/icons-vue'
import { getProjects, createProject, updateProject, deleteProject, getTasks, createTask, updateTask, getMilestones, createMilestone, updateMilestone } from '../api/projects'
import { getCustomers } from '../api/customers'
import api from '../api/index'
import * as v17Api from '../api/v17'
import { refreshProjectProfit as apiRefreshProfit } from '../api/v19'
import RequirementsTab from './project-tabs/RequirementsTab.vue'
import AcceptancesTab from './project-tabs/AcceptancesTab.vue'
import DeliverablesTab from './project-tabs/DeliverablesTab.vue'
import ReleasesTab from './project-tabs/ReleasesTab.vue'
import MaintenanceTab from './project-tabs/MaintenanceTab.vue'
import ChangeOrderSummary from './project-tabs/ChangeOrderSummary.vue'
// v1.7 新增 Tabs
import ChangeOrdersTab from './project-tabs/ChangeOrdersTab.vue'
import MilestonePaymentTab from './project-tabs/MilestonePaymentTab.vue'
import WorkHoursTab from './project-tabs/WorkHoursTab.vue'
import PageHelpDrawer from '../components/PageHelpDrawer.vue'

const projects = ref([])
const customers = ref([])
const loading = ref(false)
const statusFilter = ref('')
const searchQuery = ref('')
const showDialog = ref(false)
const editingId = ref(null)
const defaultForm = { name: '', customer_id: null, description: '', status: 'requirements', budget: null, start_date: '', end_date: '' }
const form = ref({ ...defaultForm })

const statusLabels = { requirements: '需求', design: '设计', development: '开发', testing: '测试', delivery: '交付', paused: '暂停' }
const statusTypes = { requirements: 'info', design: '', development: 'primary', testing: 'warning', delivery: 'success', paused: 'info' }

// Detail dialog state
const showDetail = ref(false)
const detailProject = ref(null)
const detailTab = ref('tasks')
const tasks = ref([])
const milestones = ref([])

// Task form
const showTaskForm = ref(false)
const editingTaskId = ref(null)
const defaultTaskForm = { title: '', description: '', status: 'todo', priority: 'medium', assignee: '', due_date: '' }
const taskForm = ref({ ...defaultTaskForm })
const taskStatusLabel = { todo: '待办', in_progress: '进行中', done: '已完成' }
const taskStatusType = { todo: 'info', in_progress: 'warning', done: 'success' }
const taskStatusCycle = ['todo', 'in_progress', 'done']

// Milestone form
const showMilestoneForm = ref(false)
const editingMilestoneId = ref(null)
const defaultMilestoneForm = { title: '', description: '', due_date: '' }
const milestoneForm = ref({ ...defaultMilestoneForm })

// v1.7 项目关闭
const closeCheckDialogVisible = ref(false)
const closeCheckData = ref(null)
const closeLoading = ref(false)

// v1.9 利润分析
const profitData = ref({ revenue: {}, cost: {}, profit: {}, warnings: [] })
const profitWarnings = ref([])
const profitRefreshing = ref(false)

const progressColor = (p) => {
  if (p >= 100) return '#10b981'
  if (p >= 70) return '#06b6d4'
  if (p >= 40) return '#f59e0b'
  return '#94a3b8'
}

const loadData = async () => {
  loading.value = true
  try {
    const params = {}
    if (statusFilter.value) params.status = statusFilter.value
    if (searchQuery.value) params.search = searchQuery.value
    const { data } = await getProjects(params)
    projects.value = data
  } finally {
    loading.value = false
  }
}

const loadCustomers = async () => {
  try {
    const { data } = await getCustomers({ limit: 100 })
    customers.value = data.items
  } catch {
    customers.value = []
  }
}

const openCreate = () => {
  editingId.value = null
  form.value = { ...defaultForm }
  showDialog.value = true
}

const editProject = (row) => {
  editingId.value = row.id
  form.value = { ...row }
  showDialog.value = true
}

const handleSubmit = async () => {
  if (!form.value.name) { ElMessage.warning('请输入项目名称'); return }
  try {
    const payload = { ...form.value }
    if (!payload.start_date) payload.start_date = null
    if (!payload.end_date) payload.end_date = null
    if (editingId.value) {
      await updateProject(editingId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await createProject(payload)
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    loadData()
  } catch { /* handled */ }
}

const handleDelete = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除该项目？关联任务和里程碑将一并删除', '确认', { type: 'warning' })
    await deleteProject(id)
    ElMessage.success('删除成功')
    loadData()
  } catch { /* cancelled */ }
}

// --- Detail Dialog ---
const openDetail = async (row) => {
  detailProject.value = row
  detailTab.value = 'tasks'
  showDetail.value = true
  await loadDetailData(row.id)
}

const loadDetailData = async (projectId) => {
  const [taskRes, msRes, profitRes, projectRes] = await Promise.all([
    getTasks(projectId),
    getMilestones(projectId),
    api.get(`/projects/${projectId}/profit`),
    api.get(`/projects/${projectId}`)
  ])
  tasks.value = taskRes.data
  milestones.value = msRes.data
  // v1.9: 存储完整利润报告
  profitData.value = profitRes.data || { revenue: {}, cost: {}, profit: {}, warnings: [] }
  profitWarnings.value = profitData.value.warnings || []
  // Attach current_version to detailProject
  Object.assign(detailProject.value, {
    current_version: projectRes.data.current_version || null
  })
}

const handleRefreshProfit = async () => {
  if (!detailProject.value) return
  profitRefreshing.value = true
  try {
    await apiRefreshProfit(detailProject.value.id)
    await loadDetailData(detailProject.value.id)
    ElMessage.success('利润已刷新')
  } catch { /* */ } finally { profitRefreshing.value = false }
}

// --- Task CRUD ---
const openTaskCreate = () => {
  editingTaskId.value = null
  taskForm.value = { ...defaultTaskForm }
  showTaskForm.value = true
}

const openTaskEdit = (t) => {
  editingTaskId.value = t.id
  taskForm.value = { title: t.title, description: t.description, status: t.status, priority: t.priority, assignee: t.assignee || '', due_date: t.due_date || '' }
  showTaskForm.value = true
}

const handleTaskSubmit = async () => {
  if (!taskForm.value.title) { ElMessage.warning('请输入任务标题'); return }
  try {
    const payload = { ...taskForm.value }
    if (!payload.due_date) payload.due_date = null
    if (!payload.assignee) payload.assignee = null
    if (editingTaskId.value) {
      await updateTask(editingTaskId.value, payload)
      ElMessage.success('任务已更新')
    } else {
      await createTask(detailProject.value.id, payload)
      ElMessage.success('任务已创建')
    }
    showTaskForm.value = false
    await loadDetailData(detailProject.value.id)
    loadData()
  } catch { /* handled */ }
}

const cycleTaskStatus = async (t) => {
  const idx = taskStatusCycle.indexOf(t.status)
  const next = taskStatusCycle[(idx + 1) % taskStatusCycle.length]
  try {
    await updateTask(t.id, { status: next })
    await loadDetailData(detailProject.value.id)
    loadData()
  } catch { /* handled */ }
}

// --- Milestone CRUD ---
const openMilestoneCreate = () => {
  editingMilestoneId.value = null
  milestoneForm.value = { ...defaultMilestoneForm }
  showMilestoneForm.value = true
}

const openMilestoneEdit = (m) => {
  editingMilestoneId.value = m.id
  milestoneForm.value = { title: m.title, description: m.description, due_date: m.due_date }
  showMilestoneForm.value = true
}

const handleMilestoneSubmit = async () => {
  if (!milestoneForm.value.title) { ElMessage.warning('请输入里程碑标题'); return }
  if (!milestoneForm.value.due_date) { ElMessage.warning('请选择截止日期'); return }
  try {
    if (editingMilestoneId.value) {
      await updateMilestone(editingMilestoneId.value, milestoneForm.value)
      ElMessage.success('里程碑已更新')
    } else {
      await createMilestone(detailProject.value.id, milestoneForm.value)
      ElMessage.success('里程碑已创建')
    }
    showMilestoneForm.value = false
    await loadDetailData(detailProject.value.id)
    loadData()
  } catch { /* handled */ }
}

const toggleMilestone = async (m) => {
  try {
    await updateMilestone(m.id, { is_completed: !m.is_completed })
    await loadDetailData(detailProject.value.id)
    loadData()
  } catch { /* handled */ }
}

// --- v1.7 项目关闭 ---
const openCloseCheck = async () => {
  closeLoading.value = true
  try {
    const res = await v17Api.checkProjectCloseConditions(detailProject.value.id)
    closeCheckData.value = res.data
    closeCheckDialogVisible.value = true
  } catch (err) {
    ElMessage.error('检查关闭条件失败: ' + (err.response?.data?.detail || err.message))
  } finally {
    closeLoading.value = false
  }
}

const handleClose = async () => {
  try {
    await ElMessageBox.confirm('确认关闭该项目？关闭后将无法修改。', '确认关闭项目', { type: 'warning' })
    closeLoading.value = true
    await v17Api.closeProject(detailProject.value.id)
    ElMessage.success('项目已关闭')
    closeCheckDialogVisible.value = false
    showDetail.value = false
    loadData()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('关闭失败: ' + (err.response?.data?.detail || err.message))
    }
  } finally {
    closeLoading.value = false
  }
}

onMounted(() => { loadData(); loadCustomers() })
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-title-group {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.header-title-group h2 { margin: 0; }

.header-count {
  font-size: 13px;
  color: var(--text-tertiary);
}

.filter-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.cell-name {
  font-weight: 500;
  color: var(--text-primary);
}

.cell-sub {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 2px;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.progress-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.progress-cell :deep(.el-progress) {
  flex: 1;
}

.progress-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  min-width: 36px;
  text-align: right;
}

.date-range {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.date-sep {
  color: var(--text-tertiary);
}

.action-btns {
  display: flex;
  gap: 4px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

:deep(.el-form-item__label) {
  padding-bottom: 4px;
}

/* Detail dialog */
.detail-header {
  margin-bottom: 16px;
}

.detail-version {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
  padding: 6px 0;
}

.detail-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.detail-budget {
  font-size: 14px;
  color: var(--text-secondary);
}

.detail-progress {
  font-size: 14px;
  font-weight: 600;
  color: var(--brand-cyan, #0891b2);
}

.detail-tabs :deep(.el-tabs__header) {
  margin-bottom: 12px;
}

.tab-toolbar {
  margin-bottom: 12px;
}

.empty-hint {
  text-align: center;
  padding: 32px 0;
  color: var(--text-tertiary, #94a3b8);
  font-size: 13px;
}

/* Task list */
.task-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.task-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-subtle, #e2e8f0);
  transition: background 0.15s;
}

.task-item:hover {
  background: var(--el-fill-color-light, #f5f7fa);
}

.task-item.priority-high {
  border-left: 3px solid #ef4444;
}

.task-item.priority-medium {
  border-left: 3px solid #f59e0b;
}

.task-item.priority-low {
  border-left: 3px solid #94a3b8;
}

.task-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.task-status {
  flex-shrink: 0;
}

.task-title {
  font-size: 13px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-assignee {
  font-size: 12px;
  color: var(--text-tertiary, #94a3b8);
  flex-shrink: 0;
}

.task-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.task-date {
  font-size: 12px;
  color: var(--text-tertiary, #94a3b8);
}

/* Milestone list */
.milestone-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.milestone-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-subtle, #e2e8f0);
  transition: background 0.15s;
}

.milestone-item:hover {
  background: var(--el-fill-color-light, #f5f7fa);
}

.milestone-item.completed {
  background: var(--el-color-success-light-9, #f0f9eb);
  border-color: var(--el-color-success-light-7, #c2e7b0);
}

.milestone-check {
  flex-shrink: 0;
}

.milestone-body {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.milestone-title {
  font-size: 13px;
  font-weight: 500;
}

.milestone-item.completed .milestone-title {
  text-decoration: line-through;
  color: var(--text-tertiary, #94a3b8);
}

.milestone-date {
  font-size: 12px;
  color: var(--text-tertiary, #94a3b8);
}

.milestone-done {
  font-size: 12px;
  color: var(--el-color-success, #67c23a);
}

/* Modern Status Dots - Scoped */
.status-dot-wrapper {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  background-color: var(--bg-soft, #f8fafc);
  border: 1px solid var(--border-light, #e2e8f0);
}
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.status-dot.primary { background-color: var(--el-color-primary); box-shadow: 0 0 4px var(--el-color-primary); }
.status-dot.success { background-color: var(--el-color-success); box-shadow: 0 0 4px var(--el-color-success); }
.status-dot.warning { background-color: var(--el-color-warning); box-shadow: 0 0 4px var(--el-color-warning); }
.status-dot.danger { background-color: var(--el-color-danger); box-shadow: 0 0 4px var(--el-color-danger); }
.status-dot.info { background-color: var(--el-color-info); box-shadow: 0 0 4px var(--el-color-info); }

.status-dot-text {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
}

/* Profit Analysis Card Styles */
.profit-card {
  background: var(--bg-card, #ffffff);
  border: 1px solid var(--border-subtle, #e2e8f0);
  border-radius: 8px;
}

.card-header {
  margin-bottom: 12px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.profit-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.profit-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  background: var(--bg-soft, #f8fafc);
  border-radius: 6px;
  border: 1px solid var(--border-light, #e2e8f0);
}

.profit-item.highlight {
  background: var(--el-color-primary-light-9, #ecf5ff);
  border-color: var(--el-color-primary-light-7, #c6e2ff);
}

.profit-label {
  font-size: 12px;
  color: var(--text-tertiary, #94a3b8);
  font-weight: 500;
}

.profit-sub {
  font-size: 11px;
  color: var(--text-tertiary, #94a3b8);
}

.profit-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--mono-font, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);
}

.profit-value.negative {
  color: #ef4444;
}

@media (max-width: 768px) {
  .profit-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* v1.7 关闭项目检查列表 */
.close-checklist {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.checklist-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  background: var(--bg-soft, #f8fafc);
  border: 1px solid var(--border-light, #e2e8f0);
}

.checklist-item.passed {
  background: var(--el-color-success-light-9, #f0f9eb);
  border-color: var(--el-color-success-light-7, #c2e7b0);
}

.checklist-item:not(.passed) {
  background: var(--el-color-warning-light-9, #fdf6ec);
  border-color: var(--el-color-warning-light-7, #f5dab1);
}

.checklist-label {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
}

.checklist-hint {
  font-size: 12px;
  color: var(--el-color-warning);
}

.blocking-items {
  margin-top: 12px;
  padding: 12px;
  background: var(--el-color-danger-light-9, #fef2f2);
  border: 1px solid var(--el-color-danger-light-7, #fca5a5);
  border-radius: 6px;
}

.blocking-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-color-danger);
  margin-bottom: 8px;
}

.blocking-item {
  font-size: 13px;
  color: var(--el-color-danger);
  padding: 4px 0;
}

.success-color {
  color: var(--el-color-success);
}

.warning-color {
  color: var(--el-color-warning);
}
</style>
