<template>
  <div>
    <div class="tab-toolbar">
      <el-button type="primary" size="small" @click="openCreateDataset"><el-icon><Plus /></el-icon> 新建数据集</el-button>
    </div>

    <!-- 数据集列表 -->
    <div v-for="ds in datasets" :key="ds.id" class="dataset-block">
      <div class="dataset-header">
        <span class="dataset-name">{{ ds.name }}</span>
        <el-tag size="small" type="info">{{ ds.data_type || '未指定' }}</el-tag>
        <el-button link size="small" type="primary" @click="openCreateVersion(ds)">+ 新建版本</el-button>
        <el-button link size="small" type="danger" @click="handleDeleteDataset(ds)">删除数据集</el-button>
      </div>
      <div class="dataset-desc" v-if="ds.description">{{ ds.description }}</div>

      <!-- 版本列表 -->
      <el-table :data="ds._versions || []" style="width:100%" size="small" v-if="ds._versions && ds._versions.length">
        <el-table-column prop="version_no" label="版本号" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="versionStatusType[row.status] || 'info'" size="small">{{ versionStatusLabel[row.status] || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sample_count" label="样本数" width="90" />
        <el-table-column prop="file_path" label="文件路径" min-width="150" show-overflow-tooltip />
        <el-table-column prop="data_source" label="数据来源" width="120" />
        <el-table-column prop="label_schema_version" label="标注Schema版本" width="130" />
        <el-table-column prop="change_summary" label="变更摘要" min-width="140" show-overflow-tooltip />
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button link size="small" type="primary" @click="openEditVersion(row)">编辑</el-button>
            <el-button v-if="row.status === 'draft'" link size="small" type="success" @click="handleMarkReady(row)">标记就绪</el-button>
            <el-button v-if="row.status === 'ready'" link size="small" type="warning" @click="handleMarkArchive(row)">归档</el-button>
            <el-button v-if="row.status !== 'in_use'" link size="small" type="danger" @click="handleDeleteVersion(row)">删除</el-button>
            <el-tooltip v-else content="使用中的版本不可删除" placement="top">
              <el-button link size="small" type="info" disabled>删除</el-button>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>
      <div v-else class="empty-hint">暂无版本</div>
    </div>
    <div v-if="!datasets.length" class="empty-hint">暂无数据集</div>

    <!-- 新建数据集 -->
    <el-dialog v-model="showDatasetForm" title="新建数据集" width="480px" destroy-on-close append-to-body>
      <el-form :model="datasetForm" label-position="top">
        <el-form-item label="数据集名称" required><el-input v-model="datasetForm.name" /></el-form-item>
        <el-form-item label="数据类型">
          <el-select v-model="datasetForm.data_type" style="width:100%">
            <el-option label="图片" value="image" /><el-option label="文本" value="text" /><el-option label="音频" value="audio" /><el-option label="视频" value="video" /><el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述"><el-input v-model="datasetForm.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDatasetForm = false">取消</el-button>
        <el-button type="primary" @click="handleCreateDataset">创建</el-button>
      </template>
    </el-dialog>

    <!-- 新建/编辑版本 -->
    <el-dialog v-model="showVersionForm" :title="versionFormTarget ? '编辑版本' : '新建版本'" width="560px" destroy-on-close append-to-body>
      <el-form :model="versionForm" label-position="top">
        <el-form-item label="版本号" required>
          <el-input v-model="versionForm.version_no" :disabled="isVersionFrozen" />
        </el-form-item>
        <el-form-item label="样本数">
          <el-input-number v-model="versionForm.sample_count" :min="0" :disabled="isVersionFrozen" style="width:100%" />
        </el-form-item>
        <el-form-item label="文件路径">
          <el-input v-model="versionForm.file_path" :disabled="isVersionFrozen" />
        </el-form-item>
        <el-form-item label="数据来源">
          <el-input v-model="versionForm.data_source" :disabled="isVersionFrozen" />
        </el-form-item>
        <el-form-item label="标注Schema版本">
          <el-input v-model="versionForm.label_schema_version" :disabled="isVersionFrozen" />
        </el-form-item>
        <el-form-item label="变更摘要">
          <el-input v-model="versionForm.change_summary" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="versionForm.notes" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showVersionForm = false">取消</el-button>
        <el-button type="primary" @click="handleSaveVersion">保存</el-button>
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
  getDatasets, createDataset, updateDataset, deleteDataset,
  getDatasetVersions, createDatasetVersion, updateDatasetVersion,
  deleteDatasetVersion, markVersionReady, markVersionArchive
} from '../../api/v111'

const props = defineProps({ projectId: { type: Number, required: true } })
const datasets = ref([])

const versionStatusLabel = { draft: '草稿', ready: '就绪', in_use: '使用中', archived: '已归档' }
const versionStatusType = { draft: 'info', ready: 'success', in_use: 'warning', archived: 'info' }
const frozenStatuses = ['ready', 'in_use', 'archived']

// 数据集表单
const showDatasetForm = ref(false)
const defaultDatasetForm = { name: '', data_type: '', description: '' }
const datasetForm = ref({ ...defaultDatasetForm })

// 版本表单
const showVersionForm = ref(false)
const versionFormTarget = ref(null) // null=新建, object=编辑
const versionFormDatasetId = ref(null)
const defaultVersionForm = { version_no: '', sample_count: 0, file_path: '', data_source: '', label_schema_version: '', change_summary: '', notes: '' }
const versionForm = ref({ ...defaultVersionForm })

const isVersionFrozen = computed(() => {
  return versionFormTarget.value && frozenStatuses.includes(versionFormTarget.value.status)
})

const loadData = async () => {
  try {
    const res = await getDatasets({ project_id: props.projectId })
    datasets.value = Array.isArray(res.data.data) ? res.data.data : []
    // 加载每个数据集的版本
    for (const ds of datasets.value) {
      try {
        const vRes = await getDatasetVersions(ds.id)
        ds._versions = Array.isArray(vRes.data.data) ? vRes.data.data : []
      } catch {
        ds._versions = []
      }
    }
  } catch { /* handled */ }
}

// 数据集操作
const openCreateDataset = () => {
  datasetForm.value = { ...defaultDatasetForm }
  showDatasetForm.value = true
}
const handleCreateDataset = async () => {
  if (!datasetForm.value.name) { ElMessage.warning('请填写数据集名称'); return }
  try {
    await createDataset({ ...datasetForm.value, project_id: props.projectId })
    ElMessage.success('数据集已创建')
    showDatasetForm.value = false
    await loadData()
  } catch { /* handled */ }
}
const handleDeleteDataset = async (ds) => {
  try {
    await ElMessageBox.confirm(`确认删除数据集「${ds.name}」？`, '确认')
    await deleteDataset(ds.id)
    ElMessage.success('已删除')
    await loadData()
  } catch { /* cancelled */ }
}

// 版本操作
const openCreateVersion = (ds) => {
  versionFormTarget.value = null
  versionFormDatasetId.value = ds.id
  versionForm.value = { ...defaultVersionForm }
  showVersionForm.value = true
}
const openEditVersion = (row) => {
  versionFormTarget.value = { ...row }
  versionFormDatasetId.value = null
  versionForm.value = {
    version_no: row.version_no || '',
    sample_count: row.sample_count || 0,
    file_path: row.file_path || '',
    data_source: row.data_source || '',
    label_schema_version: row.label_schema_version || '',
    change_summary: row.change_summary || '',
    notes: row.notes || ''
  }
  showVersionForm.value = true
}
const handleSaveVersion = async () => {
  if (!versionForm.value.version_no) { ElMessage.warning('请填写版本号'); return }
  try {
    if (versionFormTarget.value) {
      // 编辑
      await updateDatasetVersion(versionFormTarget.value.id, { ...versionForm.value })
      ElMessage.success('版本已更新')
    } else {
      // 新建
      await createDatasetVersion(versionFormDatasetId.value, { ...versionForm.value })
      ElMessage.success('版本已创建')
    }
    showVersionForm.value = false
    await loadData()
  } catch { /* handled */ }
}
const handleDeleteVersion = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除版本「${row.version_no}」？`, '确认')
    await deleteDatasetVersion(row.id)
    ElMessage.success('已删除')
    await loadData()
  } catch { /* cancelled */ }
}
const handleMarkReady = async (row) => {
  try {
    await markVersionReady(row.id)
    ElMessage.success('已标记为就绪')
    await loadData()
  } catch { /* handled */ }
}
const handleMarkArchive = async (row) => {
  try {
    await markVersionArchive(row.id)
    ElMessage.success('已归档')
    await loadData()
  } catch { /* handled */ }
}

watch(() => props.projectId, () => loadData(), { immediate: true })
</script>

<style scoped>
.tab-toolbar { margin-bottom: 12px; }
.empty-hint { color: #999; text-align: center; padding: 24px; }
.dataset-block { margin-bottom: 20px; border: 1px solid #ebeef5; border-radius: 4px; padding: 12px; }
.dataset-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.dataset-name { font-weight: 600; font-size: 14px; }
.dataset-desc { color: #666; font-size: 12px; margin-bottom: 8px; }
</style>
