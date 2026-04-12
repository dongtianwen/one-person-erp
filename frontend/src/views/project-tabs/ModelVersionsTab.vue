<template>
  <div>
    <div class="tab-toolbar">
      <el-button type="primary" size="small" @click="openCreate"><el-icon><Plus /></el-icon> 新建模型版本</el-button>
    </div>

    <el-table :data="modelVersions" style="width:100%" size="small" v-if="modelVersions.length">
      <el-table-column prop="version_no" label="版本号" width="110" />
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="mvStatusType[row.status] || 'info'" size="small">{{ mvStatusLabel[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="experiment_name" label="来源实验" min-width="130" show-overflow-tooltip />
      <el-table-column prop="model_path" label="模型路径" min-width="150" show-overflow-tooltip />
      <el-table-column label="指标" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="mono">{{ formatMetrics(row.metrics) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="notes" label="备注" min-width="120" show-overflow-tooltip />
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button link size="small" type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="row.status === 'training'" link size="small" type="success" @click="handleMarkReady(row)">标记就绪</el-button>
          <el-button v-if="row.status === 'ready'" link size="small" type="warning" @click="handleMarkDeprecate(row)">废弃</el-button>
          <el-button v-if="row.status !== 'delivered'" link size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div v-else class="empty-hint">暂无模型版本</div>

    <!-- 新建/编辑模型版本 -->
    <el-dialog v-model="showForm" :title="editingMV ? '编辑模型版本' : '新建模型版本'" width="560px" destroy-on-close append-to-body>
      <el-form :model="form" label-position="top">
        <el-form-item label="版本号" required>
          <el-input v-model="form.version_no" :disabled="isFrozen" />
        </el-form-item>
        <el-form-item v-if="!editingMV" label="来源实验" required>
          <el-select v-model="form.experiment_id" style="width:100%" placeholder="选择实验">
            <el-option v-for="exp in experiments" :key="exp.id" :label="exp.name" :value="exp.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型路径">
          <el-input v-model="form.model_path" :disabled="isFrozen" />
        </el-form-item>
        <el-form-item label="指标">
          <el-input v-model="form.metrics" type="textarea" :rows="2" :disabled="isFrozen" />
        </el-form-item>
        <el-form-item label="超参数">
          <el-input v-model="form.hyperparameters" type="textarea" :rows="2" :disabled="isFrozen" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showForm = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  getModelVersions, createModelVersion, updateModelVersion,
  deleteModelVersion, markModelReady, markModelDeprecate,
  getTrainingExperiments
} from '../../api/v111'

const props = defineProps({ projectId: { type: Number, required: true } })
const modelVersions = ref([])
const experiments = ref([])
const editingMV = ref(null)

const mvStatusLabel = { training: '训练中', ready: '就绪', delivered: '已交付', deprecated: '已废弃' }
const mvStatusType = { training: 'warning', ready: 'success', delivered: '', deprecated: 'info' }
const frozenStatuses = ['ready', 'delivered', 'deprecated']

const isFrozen = computed(() => {
  return editingMV.value && frozenStatuses.includes(editingMV.value.status)
})

// 表单
const showForm = ref(false)
const defaultForm = { version_no: '', experiment_id: null, model_path: '', metrics: '', hyperparameters: '', notes: '' }
const form = ref({ ...defaultForm })

const formatMetrics = (metrics) => {
  if (!metrics) return '-'
  try {
    // 尝试解析 JSON，如果不是标准格式则尝试修复
    let parsed
    try {
      parsed = JSON.parse(metrics)
    } catch {
      // 尝试修复非标准 JSON 格式（如 {key: value} -> {"key": value}）
      const fixed = metrics.replace(/([{,]\s*)(\w+)\s*:/g, '$1"$2":')
      parsed = JSON.parse(fixed)
    }
    // 格式化为易读的字符串
    return Object.entries(parsed).map(([key, value]) => `${key}: ${value}`).join(', ')
  } catch {
    // 如果解析失败，直接返回原始字符串
    return metrics
  }
}

const loadData = async () => {
  try {
    const res = await getModelVersions({ project_id: props.projectId })
    modelVersions.value = Array.isArray(res.data.data) ? res.data.data : []
    // 为每个模型版本添加实验名称（后端已返回 experiment_name）
    for (const mv of modelVersions.value) {
      if (!mv.experiment_name) {
        const exp = experiments.value.find(e => e.id === mv.experiment_id)
        mv.experiment_name = exp?.name || '-'
      }
    }
  } catch (err) {
    console.warn('Failed to load model versions', err)
  }
  try {
    const eRes = await getTrainingExperiments({ project_id: props.projectId })
    experiments.value = Array.isArray(eRes.data) ? eRes.data : []
    if (!Array.isArray(experiments.value)) experiments.value = []
  } catch (err) {
    console.warn('Failed to load experiments', err)
    experiments.value = []
  }
}

// CRUD
const openCreate = () => {
  editingMV.value = null
  form.value = { ...defaultForm }
  showForm.value = true
}
const openEdit = (row) => {
  editingMV.value = { ...row }
  form.value = {
    version_no: row.version_no || '',
    experiment_id: row.experiment_id || null,
    model_path: row.model_path || '',
    metrics: row.metrics || '',
    hyperparameters: row.hyperparameters || '',
    notes: row.notes || ''
  }
  showForm.value = true
}
const handleSave = async () => {
  if (!form.value.version_no) { ElMessage.warning('请填写版本号'); return }
  if (!editingMV.value && !form.value.experiment_id) { ElMessage.warning('请选择来源实验'); return }
  try {
    if (editingMV.value) {
      await updateModelVersion(editingMV.value.id, { ...form.value })
      ElMessage.success('模型版本已更新')
    } else {
      await createModelVersion({ ...form.value, project_id: props.projectId })
      ElMessage.success('模型版本已创建')
    }
    showForm.value = false
    await loadData()
  } catch { /* handled */ }
}
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除模型版本「${row.version_no}」？`, '确认')
    await deleteModelVersion(row.id)
    ElMessage.success('已删除')
    await loadData()
  } catch { /* cancelled */ }
}

// 状态流转
const handleMarkReady = async (row) => {
  try {
    await markModelReady(row.id)
    ElMessage.success('已标记为就绪')
    await loadData()
  } catch { /* handled */ }
}
const handleMarkDeprecate = async (row) => {
  try {
    await markModelDeprecate(row.id)
    ElMessage.success('已废弃')
    await loadData()
  } catch { /* handled */ }
}

watch(() => props.projectId, () => loadData(), { immediate: true })
</script>

<style scoped>
.tab-toolbar { margin-bottom: 12px; }
.empty-hint { color: #999; text-align: center; padding: 24px; }
</style>
