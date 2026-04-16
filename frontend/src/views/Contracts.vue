<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-title-group">
        <span class="header-count mono">总计：{{ total }} 份合同</span>
        <PageHelpDrawer pageKey="contract_detail" />
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新建合同
      </el-button>
    </div>

    <el-card>
      <div class="filter-bar" style="margin-bottom: 16px; display: flex; gap: 10px;">
        <el-input
          v-model="searchQuery"
          placeholder="搜索合同标题或编号..."
          style="width: 250px"
          clearable
          :prefix-icon="Search"
          @clear="loadData"
          @keyup.enter="loadData"
        />
        <el-button type="primary" @click="loadData">查询</el-button>
      </div>
      <el-table :data="contracts" style="width: 100%" v-loading="loading">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="contract_no" label="合同编号" width="160">
          <template #default="{ row }">
            <span class="mono contract-no-link" @click="openContractDetail(row)">{{ row.contract_no }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="合同标题" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px;">
              <div class="status-dot-wrapper">
                <div class="status-dot" :class="statusTypes[row.status] || 'info'"></div>
                <span class="status-dot-text">{{ statusLabels[row.status] || row.status }}</span>
              </div>
              <span style="font-weight: 500;">{{ row.title }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="金额" width="120" align="right">
          <template #default="{ row }">
            <span class="mono amount-cell">¥{{ (row.amount || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="有效期" width="200">
          <template #default="{ row }">
            <div class="date-range mono">
              <span>{{ row.start_date || '-' }}</span>
              <span class="date-sep">&rarr;</span>
              <span>{{ row.end_date || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <div class="action-btns">
              <el-button link type="primary" size="small" @click="openContractDetail(row)">管理</el-button>
              <el-button link type="primary" size="small" @click="editContract(row)">编辑</el-button>
            </div>
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

    <el-dialog v-model="showDialog" :title="editingId ? '编辑合同' : '新建合同'" width="600px" destroy-on-close>
      <el-form :model="form" label-position="top">
        <el-form-item label="合同标题" required>
          <el-input v-model="form.title" placeholder="请输入合同标题" />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="关联客户" required>
            <el-select v-model="form.customer_id" placeholder="选择客户" filterable style="width: 100%">
              <el-option v-for="c in customers" :key="c.id" :label="`${c.name} (${c.company || '无公司'})`" :value="c.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="关联项目">
            <el-select v-model="form.project_id" placeholder="选择项目" filterable clearable style="width: 100%">
              <el-option v-for="p in projects" :key="p.id" :label="`#${p.id} ${p.name}`" :value="p.id" />
            </el-select>
          </el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item label="合同金额" required>
            <el-input-number v-model="form.amount" :min="0" :precision="2" style="width: 100%" />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="form.status" style="width: 100%">
              <el-option v-for="(label, val) in statusLabels" :key="val" :label="label" :value="val" />
            </el-select>
          </el-form-item>
        </div>
        <div class="form-grid-3">
          <el-form-item label="签署日期">
            <el-date-picker v-model="form.signed_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="生效日期">
            <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="到期日期">
            <el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </div>
        <el-form-item v-if="form.status === 'terminated'" label="终止原因" required>
          <el-input v-model="form.termination_reason" type="textarea" :rows="2" placeholder="请填写终止原因" />
        </el-form-item>
        <!-- v1.3 现金流预测字段 -->
        <div class="form-grid">
          <el-form-item label="预计回款日期">
            <el-date-picker v-model="form.expected_payment_date" type="date" value-format="YYYY-MM-DD" placeholder="预计回款日期" style="width: 100%" />
          </el-form-item>
          <el-form-item label="回款阶段说明">
            <el-input v-model="form.payment_stage_note" placeholder="如：首付款、尾款等" maxlength="200" />
          </el-form-item>
        </div>
        <el-form-item label="合同条款">
          <el-input v-model="form.terms" type="textarea" :rows="3" placeholder="合同主要条款（选填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">{{ editingId ? '保存修改' : '创建合同' }}</el-button>
      </template>
    </el-dialog>

    <!-- Contract Detail Dialog -->
    <el-dialog v-model="showContractDetail" :title="detailContract?.title || '合同详情'" width="780px" destroy-on-close top="5vh">
      <div v-if="detailContract" class="detail-header">
        <div class="detail-meta">
          <span class="mono">{{ detailContract.contract_no }}</span>
          <el-tag :type="statusTypes[detailContract.status] || 'info'" size="small" round>
            {{ statusLabels[detailContract.status] || detailContract.status }}
          </el-tag>
          <span class="mono amount-cell">¥{{ (detailContract.amount || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}</span>
        </div>
      </div>
      <!-- 内容生成区域（独立 Tab 之前） -->
      <div v-if="shouldShowGenerateButton(detailContract?.status)" class="content-section" style="margin: 0 16px 16px;">
        <!-- 冻结状态提示 -->
        <el-alert v-if="detailContract?.generated_content && isContentFrozen(detailContract?.status)" type="warning" :closable="false" style="margin-bottom: 12px;">
          <template #title>内容已冻结，不可重新生成或编辑</template>
        </el-alert>

        <!-- 已有内容 -->
        <div v-if="detailContract?.generated_content" class="content-display">
          <div class="content-header">
            <span class="content-label">生成内容：</span>
            <span class="content-time">{{ detailContract.content_generated_at }}</span>
          </div>
          <pre class="content-body">{{ detailContract.generated_content }}</pre>
          <div class="content-actions">
            <el-button size="small" @click="openEditContent(detailContract)">
              <el-icon><Edit /></el-icon>
              手工编辑
            </el-button>
            <el-button size="small" @click="openPreview(detailContract)">
              <el-icon><View /></el-icon>
              预览
            </el-button>
          </div>
        </div>

        <!-- 无内容或新生成 -->
        <div v-else class="content-empty">
          <p class="empty-text">暂无生成内容</p>
          <el-button type="primary" size="small" @click="handleGenerate(detailContract)">
            <el-icon><MagicStick /></el-icon>
            生成内容
          </el-button>
        </div>
      </div>

      <el-tabs v-model="contractDetailTab">
        <!-- v1.8 发票 Tab -->
        <el-tab-pane label="发票" name="invoices">
          <InvoicesTab v-if="showContractDetail" :contract-id="detailContract?.id" :contract-amount="detailContract?.amount || 0" />
        </el-tab-pane>
        <el-tab-pane label="变更单" name="change-orders">
          <!-- 金额合计 -->
          <div v-if="changeOrderSummary" class="co-summary">
            <div class="co-summary-item"><span class="co-label">原合同金额</span><span class="mono co-value">¥{{ (detailContract?.amount || 0).toLocaleString(undefined, {minimumFractionDigits: 2}) }}</span></div>
            <div class="co-summary-item"><span class="co-label">变更单确认合计</span><span class="mono co-value">¥{{ (changeOrderSummary.confirmed_total || 0).toLocaleString(undefined, {minimumFractionDigits: 2}) }}</span></div>
            <div class="co-summary-item"><span class="co-label">实际应收合计</span><span class="mono co-value co-highlight">¥{{ (changeOrderSummary.actual_receivable || 0).toLocaleString(undefined, {minimumFractionDigits: 2}) }}</span></div>
          </div>
          <div class="tab-toolbar">
            <el-button type="primary" size="small" @click="openChangeOrderCreate"><el-icon><Plus /></el-icon> 新建变更单</el-button>
          </div>
          <el-table :data="changeOrders" style="width:100%" size="small" v-if="changeOrders.length">
            <el-table-column prop="order_no" label="变更单号" width="150" />
            <el-table-column prop="title" label="标题" min-width="120" show-overflow-tooltip />
            <el-table-column prop="amount" label="金额" width="100" align="right">
              <template #default="{ row }"><span class="mono">¥{{ (row.amount || 0).toLocaleString(undefined, {minimumFractionDigits: 2}) }}</span></template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="coStatusColor[row.status] || 'info'">{{ coStatusLabels[row.status] || row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200">
              <template #default="{ row }">
                <el-button v-if="row.status === 'draft'" link size="small" type="primary" @click="handleCOStatusChange(row, 'sent')">发送</el-button>
                <el-button v-if="row.status === 'draft'" link size="small" type="success" @click="handleCOStatusChange(row, 'confirmed')">直接确认</el-button>
                <el-button v-if="row.status === 'sent'" link size="small" type="success" @click="handleCOStatusChange(row, 'confirmed')">确认</el-button>
                <el-button v-if="row.status === 'confirmed'" link size="small" type="primary" @click="handleCOStatusChange(row, 'in_progress')">开始执行</el-button>
                <el-button v-if="row.status === 'confirmed'" link size="small" type="success" @click="handleCOStatusChange(row, 'completed')">完成</el-button>
                <el-button v-if="row.status === 'in_progress'" link size="small" type="success" @click="handleCOStatusChange(row, 'completed')">完成</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-else class="empty-hint">暂无变更单</div>
        </el-tab-pane>
      </el-tabs>

      <!-- 新建变更单 -->
      <el-dialog v-model="showCOForm" title="新建变更单" width="480px" destroy-on-close append-to-body>
        <el-form :model="coForm" label-position="top">
          <el-form-item label="标题" required><el-input v-model="coForm.title" /></el-form-item>
          <el-form-item label="描述"><el-input v-model="coForm.description" type="textarea" :rows="3" /></el-form-item>
          <el-form-item label="金额" required><el-input-number v-model="coForm.amount" :min="0" :precision="2" style="width:100%" /></el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showCOForm = false">取消</el-button>
          <el-button type="primary" @click="handleCOCreate">创建</el-button>
        </template>
      </el-dialog>
    </el-dialog>

    <!-- 预览对话框 -->
    <el-dialog v-model="previewVisible" title="预览内容" width="80%" destroy-on-close>
      <pre v-if="previewContent" class="preview-body">{{ previewContent }}</pre>
      <el-button @click="previewVisible = false">关闭</el-button>
    </el-dialog>

    <!-- 编辑内容对话框 -->
    <el-dialog v-model="editContentVisible" title="手工编辑内容" width="70%" destroy-on-close>
      <el-input
        v-model="editContent"
        type="textarea"
        :rows="20"
        placeholder="请输入内容..."
        style="width: 100%"
        resize="vertical"
      />
      <template #footer>
        <el-button @click="editContentVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEditContent" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Edit, View, MagicStick } from '@element-plus/icons-vue'
import api from '../api'
import { getCustomers } from '../api/customers'
import { getProjects } from '../api/projects'
import { getChangeOrders, createChangeOrder, patchChangeOrder, getChangeOrderDetail } from '../api/changeOrders'
import { generateContractContent, previewContractContent } from '../api/contracts'
import InvoicesTab from './contract-tabs/InvoicesTab.vue'
import PageHelpDrawer from '../components/PageHelpDrawer.vue'

const contracts = ref([])
const customers = ref([])
const projects = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchQuery = ref('')
const showDialog = ref(false)
const editingId = ref(null)
const defaultForm = { title: '', customer_id: null, project_id: null, amount: 0, signed_date: '', start_date: '', end_date: '', status: 'draft', terms: '', termination_reason: '', expected_payment_date: '', payment_stage_note: '' }
const form = ref({ ...defaultForm })

const statusLabels = { draft: '草稿', active: '生效', executing: '执行中', completed: '已完成', terminated: '终止' }
const statusTypes = { draft: 'info', active: 'success', executing: 'primary', completed: '', terminated: 'danger' }

// Contract Detail Dialog state
const showContractDetail = ref(false)
const contractDetailTab = ref('change-orders')
const detailContract = ref(null)
const changeOrders = ref([])
const changeOrderSummary = ref(null)
const showCOForm = ref(false)
const coForm = ref({ title: '', description: '', amount: 0 })

const coStatusLabels = { draft: '草稿', sent: '已发送', confirmed: '已确认', in_progress: '执行中', completed: '已完成' }
const coStatusColor = { draft: 'info', sent: '', confirmed: 'success', in_progress: 'primary', completed: '' }

// 内容生成相关状态
const previewVisible = ref(false)
const previewContent = ref('')
const editContentVisible = ref(false)
const editContent = ref('')
const saving = ref(false)

const FROZEN_STATUSES = ['active', 'terminated']

const route = useRoute()

const loadData = async () => {
  loading.value = true
  try {
    const params = { skip: (page.value - 1) * pageSize.value, limit: pageSize.value }
    if (searchQuery.value) params.search = searchQuery.value
    const { data } = await api.get('/contracts', { params })
    contracts.value = data.items
    total.value = data.total
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

const loadProjects = async () => {
  try {
    const { data } = await getProjects({})
    projects.value = data
  } catch {
    projects.value = []
  }
}

const openCreate = () => {
  editingId.value = null
  form.value = { ...defaultForm }
  showDialog.value = true
}

const editContract = (row) => {
  editingId.value = row.id
  form.value = { ...row }
  showDialog.value = true
}

const handleSubmit = async () => {
  if (!form.value.title) { ElMessage.warning('请输入合同标题'); return }
  try {
    if (editingId.value) {
      await api.put(`/contracts/${editingId.value}`, form.value)
      ElMessage.success('更新成功')
    } else {
      await api.post('/contracts', form.value)
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    loadData()
  } catch { /* handled */ }
}

onMounted(async () => {
  await loadData()
  loadCustomers()
  loadProjects()
  // Handle navigation from quotation conversion or ChangeOrderSummary
  if (route.query.contract_id) {
    const contractId = Number(route.query.contract_id)
    const contract = contracts.value.find(c => c.id === contractId)
    if (contract) {
      await openContractDetail(contract)
    } else {
      // If not found in current list, fetch directly
      try {
        const { data } = await api.get(`/contracts/${contractId}`)
        detailContract.value = data
        contractDetailTab.value = 'change-orders'
        showContractDetail.value = true
        await loadChangeOrders(data.id)
      } catch { /* ignore */ }
    }
  }
})

// --- Contract Detail Dialog ---
const openContractDetail = async (row) => {
  detailContract.value = row
  contractDetailTab.value = 'change-orders'
  showContractDetail.value = true
  await loadChangeOrders(row.id)
}

const loadChangeOrders = async (contractId) => {
  try {
    const res = await getChangeOrders(contractId)
    changeOrders.value = res.items || res
    changeOrderSummary.value = { confirmed_total: res.confirmed_total, actual_receivable: res.actual_receivable }
  } catch { /* handled */ }
}

const openChangeOrderCreate = () => {
  coForm.value = { title: '', description: '', amount: 0 }
  showCOForm.value = true
}

const handleCOCreate = async () => {
  if (!coForm.value.title) { ElMessage.warning('请填写标题'); return }
  try {
    await createChangeOrder(detailContract.value.id, coForm.value)
    ElMessage.success('变更单已创建')
    showCOForm.value = false
    await loadChangeOrders(detailContract.value.id)
  } catch { /* handled */ }
}

const handleCOStatusChange = async (row, targetStatus) => {
  try {
    await patchChangeOrder(detailContract.value.id, row.id, { status: targetStatus })
    ElMessage.success('状态已更新')
    await loadChangeOrders(detailContract.value.id)
  } catch { /* handled */ }
}

// 内容生成相关方法
const shouldShowGenerateButton = (status) => {
  return status === 'draft' || status === 'executing'
}

const isContentFrozen = (status) => {
  return FROZEN_STATUSES.includes(status)
}

const fetchContractDetail = async (id) => {
  try {
    const { data } = await api.get(`/contracts/${id}`)
    detailContract.value = data
  } catch (error) {
    ElMessage.error(error.message || '加载详情失败')
  }
}

const handleGenerate = async (row) => {
  try {
    if (row.generated_content) {
      await ElMessageBox.confirm(
        '已有生成内容（含手工修改），确认覆盖？',
        '覆盖确认',
        { type: 'warning' }
      )
    }
    await generateContractContent(row.id, true)
    ElMessage.success('内容已生成')
    await fetchContractDetail(row.id)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '生成内容失败')
    }
  }
}

const openPreview = async (row) => {
  try {
    const { data } = await previewContractContent(row.id)
    previewContent.value = data.content
    previewVisible.value = true
  } catch (error) {
    ElMessage.error(error.message || '预览失败')
  }
}

const openEditContent = (row) => {
  if (row.generated_content) {
    editContent.value = row.generated_content
  }
  editContentVisible.value = true
}

const saveEditContent = async () => {
  try {
    saving.value = true
    await generateContractContent(detailContract.value.id, false, editContent.value)
    ElMessage.success('内容已保存')
    editContentVisible.value = false
    await fetchContractDetail(detailContract.value.id)
  } catch (error) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}
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

.contract-no-link {
  font-size: 12px;
  color: var(--brand-cyan);
  cursor: pointer;
}

.amount-cell {
  font-weight: 600;
  color: var(--text-primary);
}

.date-range {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.date-sep { color: var(--text-tertiary); }

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

.form-grid-3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 0 16px;
}

:deep(.el-form-item__label) {
  padding-bottom: 4px;
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

:deep(.action-btns .el-button + .el-button) {
  margin-left: 0 !important;
}

/* Contract Detail */
.detail-header { margin-bottom: 16px; }
.detail-meta { display: flex; align-items: center; gap: 12px; }
.co-summary { display: flex; gap: 24px; margin-bottom: 16px; padding: 12px; background: var(--bg-soft, #f8fafc); border-radius: 6px; }
.co-summary-item { display: flex; flex-direction: column; gap: 4px; }
.co-label { font-size: 12px; color: var(--text-tertiary, #94a3b8); }
.co-value { font-size: 16px; font-weight: 600; }
.co-highlight { color: var(--el-color-primary); }
.tab-toolbar { margin-bottom: 12px; }
.empty-hint { color: #999; text-align: center; padding: 24px; }

/* Content Section */
.content-section {
  background: var(--bg-soft, #f8fafc);
  padding: 16px;
  border-radius: 8px;
  border: 1px solid var(--border-light, #e2e8f0);
}

.content-display {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--text-tertiary, #94a3b8);
}

.content-label {
  font-weight: 600;
}

.content-time {
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
  font-size: 11px;
}

.content-body {
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.6;
  white-space: pre-wrap;
  background: #fff;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid var(--border-light, #e2e8f0);
  max-height: 400px;
  overflow-y: auto;
}

.content-empty {
  text-align: center;
  padding: 24px 0;
}

.empty-text {
  font-size: 13px;
  color: var(--text-tertiary, #94a3b8);
  margin-bottom: 12px;
}

.content-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

/* Preview Dialog */
.preview-body {
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.6;
  white-space: pre-wrap;
  max-height: 70vh;
  overflow-y: auto;
  background: #fff;
  padding: 16px;
  border-radius: 6px;
  border: 1px solid var(--border-light, #e2e8f0);
}
</style>
