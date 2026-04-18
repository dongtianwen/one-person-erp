<template>
  <div>
    <div class="tab-toolbar">
      <PageHelpDrawer pageKey="project_annotation_tasks_tab" />
      <el-button type="primary" size="small" @click="openCreateTask"><el-icon><Plus /></el-icon> 新建标注任务</el-button>
    </div>

    <el-table :data="tasks" style="width:100%" size="small" v-if="tasks.length">
      <el-table-column prop="name" label="任务名称" min-width="140" />
      <el-table-column prop="status" label="状态" width="110">
        <template #label>状态 <FieldTip module="annotation_task" field="quality_score" /></template>
        <template #default="{ row }">
          <el-tag :type="statusType[row.status] || 'info'" size="small">{{ statusLabel[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="负责人" width="100">
        <template #default="{ row }">
          <span>{{ row.assignee || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="截止日期" width="110">
        <template #default="{ row }">
          <span>{{ formatDateTime(row.deadline) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="进度" width="80">
        <template #default="{ row }">
          <span>{{ row.progress != null ? row.progress + '%' : '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button link size="small" type="primary" @click="openEditTask(row)">编辑</el-button>
          <el-button link size="small" @click="openSpecs(row)">规范</el-button>
          <template v-if="!terminalStatuses.includes(row.status)">
            <el-button v-if="row.status === 'pending'" link size="small" type="success" @click="handleTransition(row, 'in_progress')">开始</el-button>
            <el-button v-if="row.status === 'in_progress'" link size="small" type="warning" @click="handleTransition(row, 'quality_check')">提交质检</el-button>
            <el-button v-if="row.status === 'quality_check'" link size="small" type="success" @click="handleTransition(row, 'completed')">通过</el-button>
            <el-button v-if="row.status === 'quality_check'" link size="small" type="danger" @click="openRework(row)">返工</el-button>
          </template>
          <el-button v-if="!terminalStatuses.includes(row.status)" link size="small" type="danger" @click="handleDeleteTask(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div v-else class="empty-hint">暂无标注任务</div>

    <!-- 新建/编辑任务 -->
    <el-dialog v-model="showTaskForm" :title="editingTask ? '编辑标注任务' : '新建标注任务'" width="560px" destroy-on-close append-to-body>
      <el-form :model="taskForm" label-position="top">
        <el-form-item label="任务名称" required><el-input v-model="taskForm.name" /></el-form-item>
        <el-form-item label="数据集版本" required>
          <el-select v-model="taskForm.dataset_version_id" placeholder="请选择数据集版本" style="width:100%">
            <el-option v-for="dv in datasetVersions" :key="dv.id" :label="dv.version_no + (dv.dataset_name ? ' (' + dv.dataset_name + ')' : '')" :value="dv.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人"><el-input v-model="taskForm.assignee" /></el-form-item>
        <el-form-item label="截止日期">
          <el-date-picker v-model="taskForm.deadline" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="taskForm.notes" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTaskForm = false">取消</el-button>
        <el-button type="primary" @click="handleSaveTask">保存</el-button>
      </template>
    </el-dialog>

    <!-- 返工原因 -->
    <el-dialog v-model="showRework" title="返工原因" width="440px" destroy-on-close append-to-body>
      <el-form :model="reworkForm" label-position="top">
        <el-form-item label="返工原因" required>
          <el-input v-model="reworkForm.rework_reason" type="textarea" :rows="4" placeholder="请说明返工原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRework = false">取消</el-button>
        <el-button type="primary" @click="handleReworkSubmit">确认返工</el-button>
      </template>
    </el-dialog>

    <!-- 规范列表 -->
    <el-dialog v-model="showSpecsDialog" title="标注规范" width="640px" destroy-on-close append-to-body>
      <div style="margin-bottom:12px">
        <el-button type="primary" size="small" @click="openCreateSpec">新建规范</el-button>
      </div>
      <el-table :data="specs" style="width:100%" size="small" v-if="specs.length">
        <el-table-column prop="title" label="标题" min-width="120" />
        <el-table-column prop="content" label="内容" min-width="200" show-overflow-tooltip />
      </el-table>
      <div v-else class="empty-hint">暂无规范</div>

      <!-- 新建规范 -->
      <el-dialog v-model="showSpecForm" title="新建标注规范" width="480px" destroy-on-close append-to-body>
        <el-form :model="specForm" label-position="top">
          <el-form-item label="标题" required><el-input v-model="specForm.title" /></el-form-item>
          <el-form-item label="内容" required>
            <el-input v-model="specForm.content" type="textarea" :rows="5" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showSpecForm = false">取消</el-button>
          <el-button type="primary" @click="handleCreateSpec">创建</el-button>
        </template>
      </el-dialog>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import PageHelpDrawer from '../../components/PageHelpDrawer.vue'
import {
  getAnnotationTasks, createAnnotationTask, updateAnnotationTask,
  deleteAnnotationTask, transitionAnnotationStatus,
  getAnnotationSpecs, createAnnotationSpec,
  getDatasets, getDatasetVersions
} from '../../api/v111'

const props = defineProps({ projectId: { type: Number, required: true } })
const tasks = ref([])
const editingTask = ref(null)
const datasetVersions = ref([])

const statusLabel = { pending: '待开始', in_progress: '进行中', quality_check: '质检中', completed: '已完成', rework: '返工中', cancelled: '已取消' }
const statusType = { pending: 'info', in_progress: '', quality_check: 'warning', completed: 'success', rework: 'danger', cancelled: 'info' }
const terminalStatuses = ['completed', 'cancelled']

const formatDateTime = (dt) => {
  if (!dt) return '-'
  return new Date(dt).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

// 任务表单
const showTaskForm = ref(false)
const defaultTaskForm = { name: '', dataset_version_id: null, assignee: '', deadline: '', notes: '' }
const taskForm = ref({ ...defaultTaskForm })

// 返工
const showRework = ref(false)
const reworkTarget = ref(null)
const reworkForm = ref({ rework_reason: '' })

// 规范
const showSpecsDialog = ref(false)
const specsTaskId = ref(null)
const specs = ref([])
const showSpecForm = ref(false)
const defaultSpecForm = { title: '', content: '' }
const specForm = ref({ ...defaultSpecForm })

const loadData = async () => {
  try {
    const res = await getAnnotationTasks({ project_id: props.projectId })
    tasks.value = Array.isArray(res.data.data) ? res.data.data : []
  } catch { /* handled */ }
}

// 加载项目下可用数据集版本
const loadDatasetVersions = async () => {
  try {
    const dsRes = await getDatasets({ project_id: props.projectId })
    const dsList = dsRes.data?.data || dsRes.data || dsRes || []
    const allVersions = []
    for (const ds of (Array.isArray(dsList) ? dsList : [])) {
      try {
        const vRes = await getDatasetVersions(ds.id)
        const versions = vRes.data?.data || vRes.data || vRes || []
        for (const v of (Array.isArray(versions) ? versions : [])) {
          allVersions.push({ ...v, dataset_name: ds.name })
        }
      } catch { /* skip */ }
    }
    datasetVersions.value = allVersions
  } catch { datasetVersions.value = [] }
}

// 任务 CRUD
const openCreateTask = async () => {
  editingTask.value = null
  taskForm.value = { ...defaultTaskForm }
  // 加载可用数据集版本
  await loadDatasetVersions()
  showTaskForm.value = true
}
const openEditTask = (row) => {
  editingTask.value = { ...row }
  taskForm.value = { name: row.name || '', dataset_version_id: row.dataset_version_id, assignee: row.assignee || '', deadline: row.deadline || '', notes: row.notes || '' }
  showTaskForm.value = true
}
const handleSaveTask = async () => {
  if (!taskForm.value.name) { ElMessage.warning('请填写任务名称'); return }
  if (!editingTask.value && !taskForm.value.dataset_version_id) { ElMessage.warning('请选择数据集版本'); return }
  try {
    if (editingTask.value) {
      await updateAnnotationTask(editingTask.value.id, { ...taskForm.value })
      ElMessage.success('任务已更新')
    } else {
      await createAnnotationTask({ ...taskForm.value, project_id: props.projectId })
      ElMessage.success('任务已创建')
    }
    showTaskForm.value = false
    await loadData()
  } catch { /* handled */ }
}
const handleDeleteTask = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除任务「${row.name}」？`, '确认')
    await deleteAnnotationTask(row.id)
    ElMessage.success('已删除')
    await loadData()
  } catch { /* cancelled */ }
}

// 状态流转
const handleTransition = async (row, targetStatus) => {
  try {
    await transitionAnnotationStatus(row.id, { status: targetStatus })
    ElMessage.success('状态已更新')
    await loadData()
  } catch { /* handled */ }
}

// 返工
const openRework = (row) => {
  reworkTarget.value = row
  reworkForm.value = { rework_reason: '' }
  showRework.value = true
}
const handleReworkSubmit = async () => {
  if (!reworkForm.value.rework_reason) { ElMessage.warning('请填写返工原因'); return }
  try {
    await transitionAnnotationStatus(reworkTarget.value.id, { status: 'rework', rework_reason: reworkForm.value.rework_reason })
    ElMessage.success('已标记返工')
    showRework.value = false
    await loadData()
  } catch { /* handled */ }
}

// 规范
const openSpecs = async (row) => {
  specsTaskId.value = row.id
  showSpecsDialog.value = true
  await loadSpecs(row.id)
}
const loadSpecs = async (taskId) => {
  try {
    const res = await getAnnotationSpecs(taskId)
    specs.value = res.data?.items || res.data || res || []
    if (!Array.isArray(specs.value)) specs.value = []
  } catch { specs.value = [] }
}
const openCreateSpec = () => {
  specForm.value = { ...defaultSpecForm }
  showSpecForm.value = true
}
const handleCreateSpec = async () => {
  if (!specForm.value.title || !specForm.value.content) { ElMessage.warning('请填写完整'); return }
  try {
    await createAnnotationSpec(specsTaskId.value, { ...specForm.value })
    ElMessage.success('规范已创建')
    showSpecForm.value = false
    await loadSpecs(specsTaskId.value)
  } catch { /* handled */ }
}

watch(() => props.projectId, () => loadData(), { immediate: true })
</script>

<style scoped>
.tab-toolbar { margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
.empty-hint { color: #999; text-align: center; padding: 24px; }
</style>
