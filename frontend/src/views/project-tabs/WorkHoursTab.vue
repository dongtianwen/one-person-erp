<!-- v1.7 工时偏差记录 Tab -->
<template>
  <div class="work-hours-tab">
    <!-- 工时汇总卡片 -->
    <el-card class="summary-card" shadow="never">
      <template #header>
        <span>工时汇总</span>
        <el-button type="primary" size="small" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          记录工时
        </el-button>
      </template>
      <el-row :gutter="16" v-loading="summaryLoading">
        <el-col :span="6">
          <div class="summary-item">
            <div class="summary-label">预计工时</div>
            <div class="summary-value mono">{{ summary.estimated_hours || '-' }} 小时</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item">
            <div class="summary-label">实际工时</div>
            <div class="summary-value mono">{{ summary.actual_hours_total?.toFixed(1) || '0.0' }} 小时</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item" :class="{ warning: summary.deviation_exceeds_threshold }">
            <div class="summary-label">偏差率</div>
            <div class="summary-value mono">
              {{ summary.deviation_rate != null ? (summary.deviation_rate * 100).toFixed(1) + '%' : '-' }}
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item">
            <div class="summary-label">偏差状态</div>
            <el-tag :type="summary.deviation_exceeds_threshold ? 'danger' : 'success'" size="small">
              {{ summary.deviation_exceeds_threshold ? '超过阈值' : '正常' }}
            </el-tag>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 工时记录列表 -->
    <el-card shadow="never" style="margin-top: 16px;">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>工时记录</span>
          <el-button size="small" @click="openEditEstimatedDialog">
            修改预计工时
          </el-button>
        </div>
      </template>
      <el-table :data="summary.logs" v-loading="loading" stripe>
        <el-table-column prop="log_date" label="日期" width="110" />
        <el-table-column prop="hours_spent" label="工时(小时)" width="100" align="right">
          <template #default="{ row }">
            <span class="mono">{{ row.hours_spent }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="task_description" label="任务描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="deviation_note" label="偏差备注" min-width="150">
          <template #default="{ row }">
            <span class="text-muted">{{ row.deviation_note || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="记录时间" width="160">
          <template #default="{ row }">
            <span class="mono">{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 记录工时对话框 -->
    <el-dialog
      v-model="createDialogVisible"
      title="记录工时"
      width="450px"
    >
      <el-form :model="formData" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="日期" prop="log_date">
          <el-date-picker
            v-model="formData.log_date"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="工时(小时)" prop="hours_spent">
          <el-input-number
            v-model="formData.hours_spent"
            :min="0.1"
            :max="24"
            :step="0.5"
            :precision="1"
            controls-position="right"
            style="width: 100%"
          />
          <span class="form-tip">0.1 - 24 小时</span>
        </el-form-item>
        <el-form-item label="任务描述" prop="task_description">
          <el-input
            v-model="formData.task_description"
            type="textarea"
            :rows="2"
            placeholder="简要描述当日工作内容"
          />
        </el-form-item>
        <el-form-item label="偏差备注" prop="deviation_note">
          <el-input
            v-model="formData.deviation_note"
            type="textarea"
            :rows="2"
            placeholder="偏差超过阈值时必填"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 修改预计工时对话框 -->
    <el-dialog
      v-model="editEstimatedDialogVisible"
      title="修改预计工时"
      width="350px"
    >
      <el-form :model="estimatedForm" label-width="100px">
        <el-form-item label="预计工时">
          <el-input-number
            v-model="estimatedForm.estimated_hours"
            :min="0"
            controls-position="right"
            style="width: 100%"
          />
          <span class="form-tip">小时</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editEstimatedDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUpdateEstimated" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import * as v17Api from '../../api/v17'

const props = defineProps({
  projectId: { type: Number, required: true }
})

const loading = ref(false)
const summaryLoading = ref(false)
const summary = ref({
  estimated_hours: null,
  actual_hours_total: 0,
  deviation_rate: null,
  deviation_exceeds_threshold: false,
  logs: []
})

// 创建对话框
const createDialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref(null)
const formData = ref({
  log_date: new Date().toISOString().split('T')[0],
  hours_spent: 8,
  task_description: '',
  deviation_note: ''
})

const rules = {
  log_date: [{ required: true, message: '请选择日期', trigger: 'change' }],
  hours_spent: [
    { required: true, message: '请输入工时', trigger: 'change' },
    { type: 'number', min: 0.1, max: 24, message: '工时范围为 0.1-24 小时', trigger: 'change' }
  ],
  task_description: [{ required: true, message: '请输入任务描述', trigger: 'blur' }]
}

// 修改预计工时对话框
const editEstimatedDialogVisible = ref(false)
const estimatedForm = ref({
  estimated_hours: 0
})

const formatDateTime = (dt) => {
  if (!dt) return '-'
  return new Date(dt).toLocaleString('zh-CN')
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await v17Api.getWorkHours(props.projectId)
    summary.value = res.data || summary.value
    estimatedForm.value.estimated_hours = summary.value.estimated_hours || 0
  } catch (err) {
    ElMessage.error('加载工时数据失败: ' + (err.response?.data?.detail || err.message))
  } finally {
    loading.value = false
  }
}

const loadSummary = async () => {
  summaryLoading.value = true
  try {
    const res = await v17Api.getWorkHoursSummary(props.projectId)
    summary.value = { ...summary.value, ...res.data }
  } catch (err) {
    ElMessage.error('加载汇总失败: ' + (err.response?.data?.detail || err.message))
  } finally {
    summaryLoading.value = false
  }
}

const openCreateDialog = () => {
  formData.value = {
    log_date: new Date().toISOString().split('T')[0],
    hours_spent: 8,
    task_description: '',
    deviation_note: ''
  }
  createDialogVisible.value = true
}

const handleCreate = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  submitting.value = true
  try {
    await v17Api.createWorkHourLog(props.projectId, formData.value)
    ElMessage.success('工时记录已添加')
    createDialogVisible.value = false
    await Promise.all([loadData(), loadSummary()])
  } catch (err) {
    ElMessage.error('记录失败: ' + (err.response?.data?.detail || err.message))
  } finally {
    submitting.value = false
  }
}

const openEditEstimatedDialog = () => {
  estimatedForm.value.estimated_hours = summary.value.estimated_hours || 0
  editEstimatedDialogVisible.value = true
}

const handleUpdateEstimated = async () => {
  submitting.value = true
  try {
    await v17Api.updateEstimatedHours(props.projectId, estimatedForm.value.estimated_hours)
    ElMessage.success('预计工时已更新')
    editEstimatedDialogVisible.value = false
    await Promise.all([loadData(), loadSummary()])
  } catch (err) {
    ElMessage.error('更新失败: ' + (err.response?.data?.detail || err.message))
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadData()
  loadSummary()
})
</script>

<style scoped>
.work-hours-tab {
  padding: 16px 0;
}

.summary-card {
  margin-bottom: 16px;
}

.summary-item {
  text-align: center;
  padding: 12px;
  border-radius: 4px;
  background: var(--el-bg-color-page);
}

.summary-item.warning {
  background: #fef0f0;
}

.summary-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.summary-value {
  font-size: 18px;
  font-weight: bold;
}

.form-tip {
  margin-left: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.text-muted {
  color: var(--el-text-color-secondary);
}

.mono {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
}
</style>
