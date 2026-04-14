<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-title-group">
        <span class="header-count mono">总计：{{ records.length }} 个模板</span>
        <PageHelpDrawer pageKey="template_list" />
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新建模板
      </el-button>
    </div>

    <el-card>
      <el-table :data="records" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="模板名称" min-width="180">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-weight: 500;">{{ row.name }}</span>
              <el-tag v-if="row.is_default" type="success" size="small" round>默认</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="template_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.template_type === 'quotation' ? 'primary' : 'warning'" size="small" round>
              {{ typeLabels[row.template_type] || row.template_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            <span class="mono">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <div class="action-btns">
              <el-button link type="primary" size="small" @click="openDetail(row)">查看</el-button>
              <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
              <el-button
                v-if="!row.is_default"
                link type="success" size="small"
                @click="handleSetDefault(row)"
              >设为默认</el-button>
              <span v-if="row.is_default" class="mono default-tag">默认不可删</span>
              <el-button
                v-if="!row.is_default"
                link type="danger" size="small"
                @click="handleDelete(row)"
              >删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑模板' : '新建模板'"
      width="1000px"
      destroy-on-close
      :close-on-click-modal="false"
    >
      <div class="edit-layout">
        <div class="edit-form">
          <el-form :model="form" :rules="formRules" ref="formRef" label-position="top">
            <el-form-item label="模板名称" prop="name">
              <el-input v-model="form.name" maxlength="200" placeholder="请输入模板名称" />
            </el-form-item>
            <el-form-item label="模板类型" prop="template_type">
              <el-select v-model="form.template_type" placeholder="选择模板类型" style="width: 100%">
                <el-option label="报价单" value="quotation" />
                <el-option label="合同" value="contract" />
              </el-select>
            </el-form-item>
            <el-form-item label="模板内容" prop="content">
              <el-input
                v-model="form.content"
                type="textarea"
                :rows="18"
                placeholder="请输入 Jinja2 模板内容..."
                resize="vertical"
                style="font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace; font-size: 13px;"
              />
            </el-form-item>
            <el-form-item label="描述">
              <el-input v-model="form.description" type="textarea" :rows="2" placeholder="模板描述（可选）" />
            </el-form-item>
          </el-form>
        </div>

        <!-- Variable Hints Panel -->
        <div class="var-hints" v-if="form.template_type">
          <div class="var-hints-title">可用变量</div>
          <div class="var-group" v-if="currentRequiredVars.length">
            <div class="var-group-title required">必填变量</div>
            <div class="var-list">
              <div v-for="v in currentRequiredVars" :key="v" class="var-item">
                <code>{{ v }}</code>
              </div>
            </div>
          </div>
          <div class="var-group" v-if="currentOptionalVars.length">
            <div class="var-group-title optional">可选变量</div>
            <div class="var-list">
              <div v-for="v in currentOptionalVars" :key="v" class="var-item">
                <code>{{ v }}</code>
              </div>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- Detail Dialog -->
    <el-dialog v-model="detailVisible" :title="detailData?.name || '模板详情'" width="800px" destroy-on-close>
      <div v-if="detailData" class="detail-content">
        <div class="detail-grid">
          <div class="detail-item">
            <span class="detail-label">模板名称</span>
            <span class="detail-value">{{ detailData.name }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">类型</span>
            <el-tag :type="detailData.template_type === 'quotation' ? 'primary' : 'warning'" size="small" round>
              {{ typeLabels[detailData.template_type] }}
            </el-tag>
          </div>
          <div class="detail-item">
            <span class="detail-label">默认</span>
            <span class="detail-value">{{ detailData.is_default ? '是' : '否' }}</span>
          </div>
          <div class="detail-item" v-if="detailData.description">
            <span class="detail-label">描述</span>
            <span class="detail-value">{{ detailData.description }}</span>
          </div>
        </div>
        <div class="detail-section">
          <div class="detail-section-title">模板内容</div>
          <pre class="content-body">{{ detailData.content }}</pre>
        </div>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import PageHelpDrawer from '../components/PageHelpDrawer.vue'
import {
  getTemplates, getTemplate, createTemplate, updateTemplate, deleteTemplate, setDefaultTemplate
} from '../api/templates'

const records = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const detailVisible = ref(false)
const editingId = ref(null)
const submitting = ref(false)
const formRef = ref(null)
const detailData = ref(null)

const typeLabels = {
  quotation: '报价单',
  contract: '合同',
}

const quotationRequiredVars = [
  'quotation_no', 'customer_name', 'project_name',
  'requirement_summary', 'estimate_days', 'total_amount',
  'valid_until', 'created_date',
]
const quotationOptionalVars = [
  'daily_rate', 'direct_cost', 'risk_buffer_rate',
  'tax_rate', 'tax_amount', 'discount_amount', 'subtotal_amount', 'notes',
  'company_name', 'payment_terms',
]
const contractRequiredVars = [
  'contract_no', 'customer_name', 'project_name',
  'total_amount', 'sign_date', 'company_name', 'quotation_no',
]
const contractOptionalVars = [
  'payment_terms', 'project_scope', 'deliverables_desc',
  'acceptance_criteria', 'liability_clause', 'notes',
]

const currentRequiredVars = computed(() => {
  if (form.value.template_type === 'quotation') return quotationRequiredVars
  if (form.value.template_type === 'contract') return contractRequiredVars
  return []
})

const currentOptionalVars = computed(() => {
  if (form.value.template_type === 'quotation') return quotationOptionalVars
  if (form.value.template_type === 'contract') return contractOptionalVars
  return []
})

const form = ref({
  name: '',
  template_type: '',
  content: '',
  description: '',
})

const formRules = {
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  template_type: [{ required: true, message: '请选择模板类型', trigger: 'change' }],
  content: [{ required: true, message: '请输入模板内容', trigger: 'blur' }],
}

const formatTime = (val) => {
  if (!val) return '—'
  return String(val).replace('T', ' ').slice(0, 19)
}

const loadData = async () => {
  loading.value = true
  try {
    const { data } = await getTemplates({ skip: 0, limit: 100 })
    records.value = data
  } catch {
    ElMessage.error('加载模板列表失败')
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  editingId.value = null
  form.value = { name: '', template_type: '', content: '', description: '' }
  dialogVisible.value = true
}

const openEdit = async (row) => {
  try {
    const { data } = await getTemplate(row.id)
    editingId.value = row.id
    form.value = {
      name: data.name,
      template_type: data.template_type,
      content: data.content,
      description: data.description || '',
    }
    dialogVisible.value = true
  } catch {
    ElMessage.error('加载模板详情失败')
  }
}

const openDetail = async (row) => {
  try {
    const { data } = await getTemplate(row.id)
    detailData.value = data
    detailVisible.value = true
  } catch {
    ElMessage.error('加载模板详情失败')
  }
}

const submitForm = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  submitting.value = true
  try {
    if (editingId.value) {
      await updateTemplate(editingId.value, form.value)
      ElMessage.success('模板已更新')
    } else {
      await createTemplate(form.value)
      ElMessage.success('模板已创建')
    }
    dialogVisible.value = false
    loadData()
  } catch (error) {
    const msg = error.response?.data?.detail || error.message
    if (msg && msg.includes('模板语法错误')) {
      ElMessage.error(msg)
    } else {
      ElMessage.error(editingId.value ? '更新模板失败' : '创建模板失败')
    }
  } finally {
    submitting.value = false
  }
}

const handleSetDefault = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确认将「${row.name}」设为${typeLabels[row.template_type]}的默认模板？当前默认模板将被取消。`,
      '设置默认模板',
      { type: 'warning' }
    )
    await setDefaultTemplate(row.id, row.template_type)
    ElMessage.success('默认模板已设置')
    loadData()
  } catch {
    // cancelled
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确认删除模板「${row.name}」？删除后已生成内容不受影响。`,
      '删除确认',
      { type: 'warning' }
    )
    await deleteTemplate(row.id)
    ElMessage.success('模板已删除')
    loadData()
  } catch {
    // cancelled
  }
}

onMounted(() => {
  loadData()
})
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
  gap: 12px;
}

.header-count {
  font-size: 13px;
  color: var(--text-tertiary, #94a3b8);
}

.mono {
  font-family: 'SF Mono', 'Monaco', 'Cascadia Code', monospace;
}

.action-btns {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
}

:deep(.action-btns .el-button + .el-button) {
  margin-left: 0 !important;
}

.default-tag {
  font-size: 12px;
  color: var(--el-color-success, #67c23a);
}

/* Edit Layout */
.edit-layout {
  display: flex;
  gap: 24px;
}

.edit-form {
  flex: 1;
  min-width: 0;
}

/* Variable Hints Panel */
.var-hints {
  width: 220px;
  flex-shrink: 0;
  background: var(--bg-soft, #f8fafc);
  border: 1px solid var(--border-light, #e2e8f0);
  border-radius: 8px;
  padding: 16px;
  height: fit-content;
  position: sticky;
  top: 0;
  max-height: 70vh;
  overflow-y: auto;
}

.var-hints-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle, #e2e8f0);
}

.var-group {
  margin-bottom: 12px;
}

.var-group-title {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 6px;
}

.var-group-title.required {
  color: var(--el-color-danger, #f56c6c);
}

.var-group-title.optional {
  color: var(--el-color-info, #909399);
}

.var-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.var-item code {
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
  font-size: 11px;
  background: #fff;
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid var(--border-light, #e2e8f0);
  color: var(--text-primary);
}

/* Detail Content */
.detail-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 24px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.detail-label {
  font-size: 12px;
  color: var(--text-tertiary, #94a3b8);
}

.detail-value {
  font-size: 14px;
  color: var(--text-primary);
}

.detail-section {
  margin-top: 8px;
}

.detail-section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border-subtle, #f1f5f9);
}

.content-body {
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.6;
  white-space: pre-wrap;
  background: var(--bg-soft, #f8fafc);
  padding: 12px;
  border-radius: 6px;
  border: 1px solid var(--border-light, #e2e8f0);
  max-height: 500px;
  overflow-y: auto;
}

@media (max-width: 768px) {
  .edit-layout {
    flex-direction: column;
  }
  .var-hints {
    width: 100%;
    max-height: none;
    position: static;
  }
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
