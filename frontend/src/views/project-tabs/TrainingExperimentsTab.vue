<template>
  <div>
    <div class="tab-toolbar">
      <el-button type="primary" size="small" @click="openCreate"><el-icon><Plus /></el-icon> 新建实验</el-button>
    </div>

    <el-table :data="experiments" style="width:100%" size="small" v-if="experiments.length">
      <el-table-column prop="name" label="实验名称" min-width="140" />
      <el-table-column prop="framework" label="框架" width="110">
        <template #default="{ row }">
          <span>{{ row.framework || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="expStatusType[row.status] || 'info'" size="small">{{ expStatusLabel[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="metrics_summary" label="指标摘要" min-width="150" show-overflow-tooltip />
      <el-table-column label="关联数据集版本" min-width="180">
        <template #default="{ row }">
          <div class="linked-tags" v-if="row._linkedVersions && row._linkedVersions.length">
            <el-tag v-for="dv in row._linkedVersions" :key="dv.id" size="small" closable @close="handleUnlink(row, dv)" class="link-tag">
              {{ dv.version_no || dv.id }}
            </el-tag>
          </div>
          <span v-else class="text-muted">未关联</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button link size="small" type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link size="small" type="success" @click="openLinkVersion(row)">关联数据集</el-button>
          <el-button link size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div v-else class="empty-hint">暂无训练实验</div>

    <!-- 新建/编辑实验 -->
    <el-dialog v-model="showForm" :title="editingExp ? '编辑实验' : '新建实验'" width="580px" destroy-on-close append-to-body>
      <el-form :model="form" label-position="top">
        <el-form-item label="实验名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="框架" :required="!isFrozen">
          <el-input v-model="form.framework" :disabled="isFrozen" />
        </el-form-item>
        <el-form-item label="超参数">
          <el-input v-model="form.hyperparameters" type="textarea" :rows="3" :disabled="isFrozen" placeholder="JSON 格式或自由文本" />
        </el-form-item>
        <el-form-item label="指标">
          <el-input v-model="form.metrics" type="textarea" :rows="2" :disabled="isFrozen" placeholder="JSON 格式或自由文本" />
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

    <!-- 关联数据集版本 -->
    <el-dialog v-model="showLink" title="关联数据集版本" width="520px" destroy-on-close append-to-body>
      <p class="link-hint">选择要关联的数据集版本（仅显示未归档版本）</p>
      <el-table :data="availableVersions" style="width:100%" size="small" v-if="availableVersions.length"
        @selection-change="onVersionSelect" ref="versionTableRef">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="version_no" label="版本号" width="100" />
        <el-table-column prop="dataset_name" label="数据集" min-width="140" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="versionStatusType[row.status] || 'info'" size="small">{{ versionStatusLabel[row.status] || row.status }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <div v-else class="empty-hint">无可用版本</div>
      <template #footer>
        <el-button @click="showLink = false">取消</el-button>
        <el-button type="primary" @click="handleLinkSubmit" :disabled="!selectedVersions.length">确认关联</el-button>
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
  getTrainingExperiments, createTrainingExperiment, updateTrainingExperiment,
  deleteTrainingExperiment, linkDatasetVersion, unlinkDatasetVersion,
  getLinkedDatasetVersions, getDatasetVersions, getDatasets
} from '../../api/v111'

const props = defineProps({ projectId: { type: Number, required: true } })
const experiments = ref([])
const editingExp = ref(null)
const versionTableRef = ref(null)

const expStatusLabel = { draft: '草稿', running: '运行中', completed: '已完成', failed: '失败' }
const expStatusType = { draft: 'info', running: '', completed: 'success', failed: 'danger' }
const versionStatusLabel = { draft: '草稿', ready: '就绪', in_use: '使用中', archived: '已归档' }
const versionStatusType = { draft: 'info', ready: 'success', in_use: 'warning', archived: 'info' }

const isFrozen = computed(() => {
  if (!editingExp.value) return false
  return !!(editingExp.value._linkedVersions && editingExp.value._linkedVersions.length)
})

// 实验表单
const showForm = ref(false)
const defaultForm = { name: '', framework: '', hyperparameters: '', metrics: '', notes: '' }
const form = ref({ ...defaultForm })

// 关联数据集
const showLink = ref(false)
const linkTarget = ref(null)
const availableVersions = ref([])
const selectedVersions = ref([])

const loadData = async () => {
  try {
    const res = await getTrainingExperiments({ project_id: props.projectId })
    experiments.value = Array.isArray(res.data.data) ? res.data.data : []
    // 加载每个实验的关联版本
    for (const exp of experiments.value) {
      try {
        const vRes = await getLinkedDatasetVersions(exp.id)
        // 检查 API 返回的数据结构
        const linked = Array.isArray(vRes.data.data) ? vRes.data.data : (Array.isArray(vRes.data) ? vRes.data : [])
        exp._linkedVersions = linked
      } catch (err) {
        console.warn('Failed to load linked versions for exp', exp.id, err)
        exp._linkedVersions = []
      }
    }
  } catch (err) {
    console.warn('Failed to load experiments', err)
    experiments.value = []
  }
}

// CRUD
const openCreate = () => {
  editingExp.value = null
  form.value = { ...defaultForm }
  showForm.value = true
}
const openEdit = (row) => {
  editingExp.value = { ...row }
  form.value = {
    name: row.name || '',
    framework: row.framework || '',
    hyperparameters: row.hyperparameters || '',
    metrics: row.metrics || '',
    notes: row.notes || ''
  }
  showForm.value = true
}
const handleSave = async () => {
  if (!form.value.name) { ElMessage.warning('请填写实验名称'); return }
  try {
    if (editingExp.value) {
      await updateTrainingExperiment(editingExp.value.id, { ...form.value })
      ElMessage.success('实验已更新')
    } else {
      await createTrainingExperiment({ ...form.value, project_id: props.projectId })
      ElMessage.success('实验已创建')
    }
    showForm.value = false
    await loadData()
  } catch { /* handled */ }
}
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除实验「${row.name}」？`, '确认')
    await deleteTrainingExperiment(row.id)
    ElMessage.success('已删除')
    await loadData()
  } catch { /* cancelled */ }
}

// 关联数据集版本
const openLinkVersion = async (row) => {
  linkTarget.value = row
  selectedVersions.value = []
  // 加载项目所有数据集的未归档版本
  try {
    const dsRes = await getDatasets({ project_id: props.projectId })
    const dsList = dsRes.data?.data || dsRes.data || dsRes || []
    const allVersions = []
    for (const ds of (Array.isArray(dsList) ? dsList : [])) {
      try {
        const vRes = await getDatasetVersions(ds.id)
        const versions = vRes.data?.data || vRes.data || vRes || []
        for (const v of (Array.isArray(versions) ? versions : [])) {
          if (v.status !== 'archived') {
            allVersions.push({ ...v, dataset_name: ds.name })
          }
        }
      } catch { /* skip */ }
    }
    availableVersions.value = allVersions
  } catch {
    availableVersions.value = []
  }
  showLink.value = true
}
const onVersionSelect = (selection) => {
  selectedVersions.value = selection
}
const handleLinkSubmit = async () => {
  if (!selectedVersions.value.length) return
  try {
    for (const dv of selectedVersions.value) {
      await linkDatasetVersion(linkTarget.value.id, { dataset_version_id: dv.id })
    }
    ElMessage.success('已关联')
    showLink.value = false
    await loadData()
  } catch { /* handled */ }
}
const handleUnlink = async (exp, dv) => {
  try {
    await unlinkDatasetVersion(exp.id, dv.id)
    ElMessage.success('已取消关联')
    await loadData()
  } catch { /* handled */ }
}

watch(() => props.projectId, () => loadData(), { immediate: true })
</script>

<style scoped>
.tab-toolbar { margin-bottom: 12px; }
.empty-hint { color: #999; text-align: center; padding: 24px; }
.linked-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.link-tag { margin: 0; }
.text-muted { color: #999; }
.link-hint { color: #666; font-size: 12px; margin-bottom: 8px; }
</style>
