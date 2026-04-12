<template>
  <div>
    <div class="tab-toolbar">
      <el-button type="primary" size="small" @click="openCreate"><el-icon><Plus /></el-icon> 新建交付包</el-button>
    </div>

    <el-table :data="packages" style="width:100%" size="small" v-if="packages.length" row-key="id">
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="expand-content">
            <h4>可追溯链</h4>
            <div v-if="row._traceability" class="trace-block">
              <div v-if="row._traceability.model_versions && row._traceability.model_versions.length">
                <strong>模型版本：</strong>
                <el-tag v-for="mv in row._traceability.model_versions" :key="mv.id" size="small" class="trace-tag">{{ mv.version_no }}</el-tag>
              </div>
              <div v-if="row._traceability.dataset_versions && row._traceability.dataset_versions.length">
                <strong>数据集版本：</strong>
                <el-tag v-for="dv in row._traceability.dataset_versions" :key="dv.id" size="small" type="success" class="trace-tag">{{ dv.dataset_name }} / {{ dv.version_no }}</el-tag>
              </div>
              <div v-if="row._traceability.experiments && row._traceability.experiments.length">
                <strong>实验：</strong>
                <el-tag v-for="exp in row._traceability.experiments" :key="exp.id" size="small" type="warning" class="trace-tag">{{ exp.name }}</el-tag>
              </div>
              <div v-if="!hasTraceData(row)" class="text-muted">暂无可追溯信息</div>
            </div>
            <div v-else class="text-muted">暂无可追溯信息</div>

            <el-divider />
            <h4>关联管理</h4>
            <div class="link-section">
              <div class="link-row">
                <span class="link-label">模型版本：</span>
                <el-tag v-for="mv in (row._modelVersions || [])" :key="mv.id" size="small" closable @close="handleUnlinkModel(row, mv)" class="trace-tag">{{ mv.version_no }}</el-tag>
                <el-button link size="small" type="primary" @click="openLinkModel(row)">+ 关联模型版本</el-button>
              </div>
              <div class="link-row">
                <span class="link-label">数据集版本：</span>
                <el-tag v-for="dv in (row._datasetVersions || [])" :key="dv.id" size="small" type="success" closable @close="handleUnlinkDataset(row, dv)" class="trace-tag">{{ dv.version_no }}</el-tag>
                <el-button link size="small" type="primary" @click="openLinkDataset(row)">+ 关联数据集版本</el-button>
              </div>
            </div>

            <el-divider />
            <h4>验收记录</h4>
            <div v-if="row._acceptance" class="acceptance-info">
              <el-tag :type="row._acceptance.result === 'passed' ? 'success' : 'danger'" size="small">
                {{ row._acceptance.result === 'passed' ? '已通过' : '未通过' }}
              </el-tag>
              <span class="acceptance-notes">{{ row._acceptance.notes || '无备注' }}</span>
            </div>
            <div v-else class="text-muted">暂无验收记录</div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="交付包名称" min-width="150" />
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="pkgStatusType[row.status] || 'info'" size="small">{{ pkgStatusLabel[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="delivered_at" label="交付日期" width="160">
        <template #default="{ row }">
          <span class="mono">{{ row.delivered_at || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button link size="small" type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="row.status === 'ready'" link size="small" type="success" @click="handleDeliver(row)">交付</el-button>
          <el-button v-if="row.status === 'delivered'" link size="small" type="warning" @click="openAcceptance(row)">验收</el-button>
          <el-button v-if="row.status !== 'accepted'" link size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div v-else class="empty-hint">暂无交付包</div>

    <!-- 新建/编辑交付包 -->
    <el-dialog v-model="showForm" :title="editingPkg ? '编辑交付包' : '新建交付包'" width="520px" destroy-on-close append-to-body>
      <el-form :model="form" label-position="top">
        <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.notes" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showForm = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 验收 -->
    <el-dialog v-model="showAcceptance" title="验收" width="460px" destroy-on-close append-to-body>
      <el-form :model="acceptanceForm" label-position="top">
        <el-form-item label="验收结果" required>
          <el-select v-model="acceptanceForm.result" style="width:100%">
            <el-option label="通过" value="passed" /><el-option label="不通过" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item label="验收备注">
          <el-input v-model="acceptanceForm.notes" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAcceptance = false">取消</el-button>
        <el-button type="primary" @click="handleAcceptanceSubmit">提交验收</el-button>
      </template>
    </el-dialog>

    <!-- 关联模型版本 -->
    <el-dialog v-model="showLinkModel" title="关联模型版本" width="480px" destroy-on-close append-to-body>
      <el-table :data="availableModelVersions" style="width:100%" size="small" v-if="availableModelVersions.length"
        @selection-change="onModelSelect" ref="modelTableRef">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="version_no" label="版本号" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="mvStatusType[row.status] || 'info'" size="small">{{ mvStatusLabel[row.status] || row.status }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <div v-else class="empty-hint">无可用模型版本</div>
      <template #footer>
        <el-button @click="showLinkModel = false">取消</el-button>
        <el-button type="primary" @click="handleLinkModelSubmit" :disabled="!selectedModels.length">确认关联</el-button>
      </template>
    </el-dialog>

    <!-- 关联数据集版本 -->
    <el-dialog v-model="showLinkDataset" title="关联数据集版本" width="520px" destroy-on-close append-to-body>
      <el-table :data="availableDatasetVersions" style="width:100%" size="small" v-if="availableDatasetVersions.length"
        @selection-change="onDatasetSelect" ref="datasetTableRef">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="version_no" label="版本号" width="100" />
        <el-table-column prop="dataset_name" label="数据集" min-width="140" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="dvStatusType[row.status] || 'info'" size="small">{{ dvStatusLabel[row.status] || row.status }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <div v-else class="empty-hint">无可用数据集版本</div>
      <template #footer>
        <el-button @click="showLinkDataset = false">取消</el-button>
        <el-button type="primary" @click="handleLinkDatasetSubmit" :disabled="!selectedDatasets.length">确认关联</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  getDeliveryPackages, createDeliveryPackage, updateDeliveryPackage,
  deleteDeliveryPackage, deliverPackage, createPackageAcceptance,
  getPackageAcceptance, getPackageTraceability,
  linkPackageModelVersion, unlinkPackageModelVersion,
  linkPackageDatasetVersion, unlinkPackageDatasetVersion,
  getModelVersions, getDatasets, getDatasetVersions
} from '../../api/v111'

const props = defineProps({ projectId: { type: Number, required: true } })
const packages = ref([])
const editingPkg = ref(null)

const pkgStatusLabel = { draft: '草稿', ready: '就绪', delivered: '已交付', accepted: '已验收', rejected: '已拒绝' }
const pkgStatusType = { draft: 'info', ready: '', delivered: 'warning', accepted: 'success', rejected: 'danger' }
const mvStatusLabel = { training: '训练中', ready: '就绪', delivered: '已交付', deprecated: '已废弃' }
const mvStatusType = { training: 'warning', ready: 'success', delivered: '', deprecated: 'info' }
const dvStatusLabel = { draft: '草稿', ready: '就绪', in_use: '使用中', archived: '已归档' }
const dvStatusType = { draft: 'info', ready: 'success', in_use: 'warning', archived: 'info' }

// 表单
const showForm = ref(false)
const defaultForm = { name: '', description: '', notes: '' }
const form = ref({ ...defaultForm })

// 验收
const showAcceptance = ref(false)
const acceptanceTarget = ref(null)
const acceptanceForm = ref({ result: 'passed', notes: '' })

// 关联
const showLinkModel = ref(false)
const linkModelTarget = ref(null)
const availableModelVersions = ref([])
const selectedModels = ref([])
const modelTableRef = ref(null)

const showLinkDataset = ref(false)
const linkDatasetTarget = ref(null)
const availableDatasetVersions = ref([])
const selectedDatasets = ref([])
const datasetTableRef = ref(null)

const hasTraceData = (row) => {
  const t = row._traceability
  if (!t) return false
  return (t.model_versions && t.model_versions.length) ||
    (t.dataset_versions && t.dataset_versions.length) ||
    (t.experiments && t.experiments.length)
}

const loadData = async () => {
  try {
    const res = await getDeliveryPackages({ project_id: props.projectId })
    packages.value = Array.isArray(res.data.data) ? res.data.data : []
    // 加载每个包的关联信息和追溯
    for (const pkg of packages.value) {
      // 追溯链
      try {
        const tRes = await getPackageTraceability(pkg.id)
        const raw = tRes.data || tRes || {}
        // 展平嵌套结构：API 返回 model_versions 每项为 {model_version: {id,version_no,...}, experiment_id, dataset_versions}
        const flatMvs = (raw.model_versions || []).map(mv => ({
          id: mv.model_version?.id || mv.id,
          version_no: mv.model_version?.version_no || mv.version_no,
          name: mv.model_version?.name || mv.name,
          status: mv.model_version?.status || mv.status,
          experiment_id: mv.experiment_id,
          dataset_versions: mv.dataset_versions || [],
        }))
        const flatDvs = (raw.dataset_versions || []).map(dv => ({
          id: dv.id,
          version_no: dv.version_no,
          status: dv.status,
          dataset_name: dv.dataset_name || '',
        }))
        pkg._traceability = { ...raw, model_versions: flatMvs, dataset_versions: flatDvs }
      } catch { pkg._traceability = {} }
      // 验收记录
      try {
        const aRes = await getPackageAcceptance(pkg.id)
        pkg._acceptance = aRes.data || aRes || null
      } catch { pkg._acceptance = null }
      // 关联的模型版本（从追溯链中提取，已展平）
      pkg._modelVersions = pkg._traceability?.model_versions || []
      // 关联的数据集版本（从追溯链中提取，已展平）
      pkg._datasetVersions = pkg._traceability?.dataset_versions || []
    }
  } catch { /* handled */ }
}

// CRUD
const openCreate = () => {
  editingPkg.value = null
  form.value = { ...defaultForm }
  showForm.value = true
}
const openEdit = (row) => {
  editingPkg.value = { ...row }
  form.value = { name: row.name || '', description: row.description || '', notes: row.notes || '' }
  showForm.value = true
}
const handleSave = async () => {
  if (!form.value.name) { ElMessage.warning('请填写名称'); return }
  try {
    if (editingPkg.value) {
      await updateDeliveryPackage(editingPkg.value.id, { ...form.value })
      ElMessage.success('交付包已更新')
    } else {
      await createDeliveryPackage({ ...form.value, project_id: props.projectId })
      ElMessage.success('交付包已创建')
    }
    showForm.value = false
    await loadData()
  } catch { /* handled */ }
}
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除交付包「${row.name}」？`, '确认')
    await deleteDeliveryPackage(row.id)
    ElMessage.success('已删除')
    await loadData()
  } catch { /* cancelled */ }
}

// 交付
const handleDeliver = async (row) => {
  try {
    await ElMessageBox.confirm('确认交付此交付包？', '确认交付')
    await deliverPackage(row.id)
    ElMessage.success('已交付')
    await loadData()
  } catch { /* cancelled */ }
}

// 验收
const openAcceptance = (row) => {
  acceptanceTarget.value = row
  acceptanceForm.value = { result: 'passed', notes: '' }
  showAcceptance.value = true
}
const handleAcceptanceSubmit = async () => {
  if (!acceptanceForm.value.result) { ElMessage.warning('请选择验收结果'); return }
  try {
    await createPackageAcceptance(acceptanceTarget.value.id, { ...acceptanceForm.value })
    ElMessage.success('验收结果已提交')
    showAcceptance.value = false
    await loadData()
  } catch { /* handled */ }
}

// 关联模型版本
const openLinkModel = async (row) => {
  linkModelTarget.value = row
  selectedModels.value = []
  try {
    const res = await getModelVersions({ project_id: props.projectId })
    const all = res.data?.data || res.data || res || []
    availableModelVersions.value = Array.isArray(all) ? all : []
  } catch { availableModelVersions.value = [] }
  showLinkModel.value = true
}
const onModelSelect = (selection) => { selectedModels.value = selection }
const handleLinkModelSubmit = async () => {
  if (!selectedModels.value.length) return
  try {
    for (const mv of selectedModels.value) {
      await linkPackageModelVersion(linkModelTarget.value.id, { model_version_id: mv.id })
    }
    ElMessage.success('已关联')
    showLinkModel.value = false
    await loadData()
  } catch { /* handled */ }
}
const handleUnlinkModel = async (pkg, mv) => {
  try {
    await unlinkPackageModelVersion(pkg.id, mv.id)
    ElMessage.success('已取消关联')
    await loadData()
  } catch { /* handled */ }
}

// 关联数据集版本
const openLinkDataset = async (row) => {
  linkDatasetTarget.value = row
  selectedDatasets.value = []
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
    availableDatasetVersions.value = allVersions
  } catch { availableDatasetVersions.value = [] }
  showLinkDataset.value = true
}
const onDatasetSelect = (selection) => { selectedDatasets.value = selection }
const handleLinkDatasetSubmit = async () => {
  if (!selectedDatasets.value.length) return
  try {
    for (const dv of selectedDatasets.value) {
      await linkPackageDatasetVersion(linkDatasetTarget.value.id, { dataset_version_id: dv.id })
    }
    ElMessage.success('已关联')
    showLinkDataset.value = false
    await loadData()
  } catch { /* handled */ }
}
const handleUnlinkDataset = async (pkg, dv) => {
  try {
    await unlinkPackageDatasetVersion(pkg.id, dv.id)
    ElMessage.success('已取消关联')
    await loadData()
  } catch { /* handled */ }
}

watch(() => props.projectId, () => loadData(), { immediate: true })
</script>

<style scoped>
.tab-toolbar { margin-bottom: 12px; }
.empty-hint { color: #999; text-align: center; padding: 24px; }
.expand-content { padding: 12px 20px; }
.expand-content h4 { margin: 0 0 8px; font-size: 13px; color: #333; }
.trace-block { font-size: 12px; line-height: 2; }
.trace-tag { margin-right: 4px; }
.text-muted { color: #999; font-size: 12px; }
.link-section { font-size: 12px; }
.link-row { margin-bottom: 8px; display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.link-label { min-width: 80px; color: #666; }
.acceptance-info { display: flex; align-items: center; gap: 8px; }
.acceptance-notes { color: #666; font-size: 12px; }
</style>
