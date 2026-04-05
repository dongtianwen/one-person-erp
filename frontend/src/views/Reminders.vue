<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-title-group">
        <h2>提醒管理</h2>
        <span class="header-count mono">{{ total }} 条提醒</span>
      </div>
      <div class="header-actions">
        <el-button @click="openSettings">
          <el-icon><Setting /></el-icon>
          设置
        </el-button>
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>
          新建提醒
        </el-button>
      </div>
    </div>

    <el-card>
      <div class="filter-bar">
        <el-select v-model="typeFilter" placeholder="类型" clearable style="width: 130px" @change="loadData">
          <el-option v-for="(label, val) in typeLabels" :key="val" :label="label" :value="val" />
        </el-select>
        <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 120px" @change="loadData">
          <el-option v-for="(label, val) in statusLabels" :key="val" :label="label" :value="val" />
        </el-select>
        <el-button type="primary" @click="loadData">筛选</el-button>
      </div>

      <el-table :data="items" style="width: 100%" v-loading="loading" :row-class-name="rowClassName">
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTypes[row.status] || 'info'" size="small" round>
              {{ statusLabels[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="reminder_type" label="类型" width="110">
          <template #default="{ row }">
            {{ typeLabels[row.reminder_type] || row.reminder_type }}
          </template>
        </el-table-column>
        <el-table-column prop="reminder_date" label="提醒日期" width="120">
          <template #default="{ row }">
            <span class="mono">{{ row.reminder_date }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="90">
          <template #default="{ row }">
            <span>{{ row.source === 'manual' ? '手动' : '系统' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_critical" label="是否关键" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.is_critical" type="danger" size="small" round>关键</el-tag>
            <span v-else class="text-tertiary">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status !== 'completed'"
              link
              type="success"
              size="small"
              @click="handleComplete(row)"
            >
              <el-icon><Check /></el-icon>
              完成
            </el-button>
            <el-button
              v-if="!row.is_critical"
              link
              type="danger"
              size="small"
              @click="handleDelete(row)"
            >
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadData"
        />
      </div>
    </el-card>

    <!-- Create Dialog -->
    <el-dialog v-model="showDialog" title="新建提醒" width="500px" destroy-on-close>
      <el-form :model="form" label-position="top">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" placeholder="请输入提醒标题" />
        </el-form-item>
        <el-form-item label="提醒日期" required>
          <el-date-picker v-model="form.reminder_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" type="textarea" :rows="3" placeholder="备注说明（选填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">创建提醒</el-button>
      </template>
    </el-dialog>

    <!-- Settings Dialog -->
    <el-dialog v-model="showSettingsDialog" title="提醒设置" width="520px" destroy-on-close>
      <div v-for="setting in settings" :key="setting.id" class="setting-item">
        <div class="setting-header">
          <span class="setting-name">{{ typeLabels[setting.reminder_type] || setting.reminder_type }}</span>
          <el-switch v-model="setting.is_enabled" />
        </div>
        <div v-if="setting.is_enabled" class="setting-fields">
          <div class="form-grid">
            <el-form-item label="提醒月份">
              <el-input-number v-model="setting.reminder_month" :min="1" :max="12" style="width: 100%" />
            </el-form-item>
            <el-form-item label="提醒日期">
              <el-input-number v-model="setting.reminder_day" :min="1" :max="31" style="width: 100%" />
            </el-form-item>
          </div>
          <el-form-item label="提前天数">
            <el-input-number v-model="setting.days_before" :min="0" :max="90" style="width: 100%" />
          </el-form-item>
        </div>
      </div>
      <template #footer>
        <el-button @click="showSettingsDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveSettings">保存设置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Setting, Check, Delete } from '@element-plus/icons-vue'
import {
  getReminders,
  createReminder,
  completeReminder,
  deleteReminder,
  getReminderSettings,
  updateReminderSetting,
} from '../api/reminders'

const items = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const typeFilter = ref('')
const statusFilter = ref('')
const showDialog = ref(false)
const showSettingsDialog = ref(false)
const settings = ref([])
const defaultForm = { title: '', reminder_type: 'custom', reminder_date: '', note: '' }
const form = ref({ ...defaultForm })

const typeLabels = {
  annual_report: '年报审计',
  tax_filing: '税期申报',
  contract_expiry: '合同到期',
  task_deadline: '任务截止',
  file_expiry: '文件到期',
  custom: '自定义',
}
const statusLabels = { pending: '待处理', overdue: '已逾期', completed: '已完成' }
const statusTypes = { pending: 'warning', overdue: 'danger', completed: 'success' }

const rowClassName = ({ row }) => {
  if (row.status === 'overdue') return 'overdue-row'
  return ''
}

const loadData = async () => {
  loading.value = true
  try {
    const params = { skip: (page.value - 1) * pageSize.value, limit: pageSize.value }
    if (typeFilter.value) params.reminder_type = typeFilter.value
    if (statusFilter.value) params.status = statusFilter.value
    const { data } = await getReminders(params)
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  form.value = { ...defaultForm }
  showDialog.value = true
}

const handleCreate = async () => {
  if (!form.value.title) { ElMessage.warning('请输入提醒标题'); return }
  if (!form.value.reminder_date) { ElMessage.warning('请选择提醒日期'); return }
  try {
    await createReminder(form.value)
    ElMessage.success('创建成功')
    showDialog.value = false
    loadData()
  } catch { /* handled */ }
}

const handleComplete = async (row) => {
  try {
    await ElMessageBox.confirm('确定将该提醒标记为已完成？', '确认完成', { type: 'info' })
    await completeReminder(row.id)
    ElMessage.success('已完成')
    loadData()
  } catch { /* cancelled or handled */ }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除该提醒？此操作不可撤销。', '确认删除', { type: 'warning' })
    await deleteReminder(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch { /* cancelled or handled */ }
}

const openSettings = async () => {
  try {
    const { data } = await getReminderSettings()
    settings.value = data.map((s) => ({ ...s }))
    showSettingsDialog.value = true
  } catch { /* handled */ }
}

const handleSaveSettings = async () => {
  try {
    for (const setting of settings.value) {
      await updateReminderSetting(setting.id, {
        is_enabled: setting.is_enabled,
        reminder_month: setting.reminder_month,
        reminder_day: setting.reminder_day,
        days_before: setting.days_before,
      })
    }
    ElMessage.success('设置已保存')
    showSettingsDialog.value = false
    loadData()
  } catch { /* handled */ }
}

onMounted(() => { loadData() })
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

.header-actions {
  display: flex;
  gap: 10px;
}

.filter-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.text-tertiary {
  color: var(--text-tertiary);
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-subtle);
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

/* ---- Settings ---- */
.setting-item {
  padding: 16px 0;
  border-bottom: 1px solid var(--border-subtle);
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.setting-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.setting-fields {
  padding-left: 4px;
}

:deep(.el-form-item__label) {
  padding-bottom: 4px;
}

/* ---- Overdue row highlight ---- */
:deep(.overdue-row) {
  border-left: 3px solid var(--el-color-danger) !important;
}

:deep(.overdue-row > td:first-child) {
  padding-left: 12px;
}
</style>
