<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-title-group">
        <span class="header-count mono">总计：{{ total }} 条记录</span>
        <PageHelpDrawer pageKey="quote_list" />
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新建报价单
      </el-button>
    </div>

    <el-card>
      <div class="filter-bar">
        <el-input
          v-model="searchQuery"
          placeholder="搜索报价标题..."
          style="width: 250px"
          clearable
          :prefix-icon="Search"
          @clear="loadData"
          @keyup.enter="loadData"
        />
        <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 130px" @change="loadData">
          <el-option v-for="(label, val) in statusLabels" :key="val" :label="label" :value="val" />
        </el-select>
        <el-select v-model="customerFilter" placeholder="客户" clearable filterable style="width: 180px" @change="loadData">
          <el-option v-for="c in customerOptions" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-button type="primary" @click="loadData">查询</el-button>
      </div>

      <el-table :data="records" style="width: 100%" v-loading="loading">
        <el-table-column prop="quote_no" label="报价编号" width="160">
          <template #default="{ row }">
            <span class="mono contract-no" style="cursor: pointer" @click="openDetail(row)">{{ row.quote_no }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="报价标题" min-width="160" show-overflow-tooltip>
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
        <el-table-column prop="customer_id" label="客户" width="120">
          <template #default="{ row }">
            {{ getCustomerName(row.customer_id) }}
          </template>
        </el-table-column>
        <el-table-column prop="total_amount" label="总价" width="120" align="right">
          <template #default="{ row }">
            <span class="mono" :class="{ 'expired-text': isExpired(row) }">
              ¥{{ formatAmount(row.total_amount) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag
              v-if="row.status === 'expired'"
              type="danger"
              size="small"
              round
              effect="dark"
            >已过期</el-tag>
            <el-tag v-else :type="statusTypes[row.status] || 'info'" size="small" round>
              {{ statusLabels[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="valid_until" label="有效期至" width="110">
          <template #default="{ row }">
            <span class="mono" :class="{ 'expired-text': isExpired(row) }">{{ row.valid_until }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-btns">
              <el-button link type="primary" size="small" @click="openDetail(row)">查看</el-button>
              <el-button v-if="canEdit(row.status)" link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
              <el-button
                v-if="row.status === 'accepted' && !row.converted_contract_id"
                link type="success" size="small"
                @click="handleConvert(row)"
              >转合同</el-button>
              <span v-if="row.converted_contract_id" class="mono converted-tag">已转合同</span>
              <el-dropdown v-if="hasStatusActions(row)" trigger="click" placement="bottom-end">
                <el-button link type="info" size="small" style="padding: 0 4px">
                  <el-icon><MoreFilled /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item v-if="row.status === 'draft'" @click="changeStatus(row, 'sent')" style="color: var(--el-color-success)">发送给客户</el-dropdown-item>
                    <el-dropdown-item v-if="row.status === 'sent'" @click="changeStatus(row, 'accepted')" style="color: var(--el-color-success)">客户已接受</el-dropdown-item>
                    <el-dropdown-item v-if="row.status === 'sent'" @click="changeStatus(row, 'rejected')" style="color: var(--el-color-warning)">客户已拒绝</el-dropdown-item>
                    <el-dropdown-item v-if="['draft', 'sent'].includes(row.status)" @click="changeStatus(row, 'cancelled')" style="color: var(--el-color-info)">取消报价</el-dropdown-item>
                    <el-dropdown-item v-if="row.status === 'draft'" @click="handleDelete(row)" style="color: var(--el-color-danger)" divided>删除记录</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-bar" v-if="total > pageSize">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="loadData"
        />
      </div>
    </el-card>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑报价单' : '新建报价单'"
      width="900px"
      destroy-on-close
      :close-on-click-modal="false"
    >
      <div class="edit-layout">
        <div class="edit-form">
          <el-form :model="form" :rules="formRules" ref="formRef" label-position="top" size="default">
            <el-form-item label="报价标题" prop="title">
              <el-input
                v-model="form.title"
                maxlength="200"
                placeholder="请输入报价标题"
                :disabled="isAcceptedReadOnly"
              />
            </el-form-item>
            <div class="form-grid">
              <el-form-item label="客户" prop="customer_id">
                <el-select
                  v-model="form.customer_id"
                  filterable
                  placeholder="选择客户"
                  style="width: 100%"
                  :disabled="isAcceptedReadOnly"
                >
                  <el-option v-for="c in customerOptions" :key="c.id" :label="c.name" :value="c.id" />
                </el-select>
              </el-form-item>
              <el-form-item prop="valid_until">
                <template #label>有效期至 <FieldTip module="quote" field="valid_until" /></template>
                <el-date-picker
                  v-model="form.valid_until"
                  type="date"
                  value-format="YYYY-MM-DD"
                  placeholder="选择有效期"
                  style="width: 100%"
                  :disabled="isAcceptedReadOnly"
                />
              </el-form-item>
            </div>
            <el-form-item label="需求摘要" prop="requirement_summary">
              <el-input
                v-model="form.requirement_summary"
                type="textarea"
                :rows="3"
                maxlength="5000"
                show-word-limit
                placeholder="需求描述"
                :disabled="isAcceptedReadOnly"
              />
            </el-form-item>
            <div class="form-grid">
              <el-form-item prop="estimate_days">
                <template #label>预计工期（天） <FieldTip module="quote" field="estimate_days" /></template>
                <el-input-number
                  v-model="form.estimate_days"
                  :min="1"
                  :max="365"
                  :controls="false"
                  style="width: 100%"
                  :disabled="isAcceptedReadOnly"
                />
              </el-form-item>
              <el-form-item>
                <template #label>日费率 <FieldTip module="quote" field="daily_rate" /></template>
                <el-input-number
                  v-model="form.daily_rate"
                  :min="0"
                  :precision="2"
                  :controls="false"
                  placeholder="可选"
                  style="width: 100%"
                  :disabled="isAcceptedReadOnly"
                />
              </el-form-item>
            </div>
            <div class="form-grid">
              <el-form-item label="直接成本">
                <el-input-number
                  v-model="form.direct_cost"
                  :min="0"
                  :precision="2"
                  :controls="false"
                  placeholder="可选"
                  style="width: 100%"
                  :disabled="isAcceptedReadOnly"
                />
              </el-form-item>
              <el-form-item>
                <template #label>风险缓冲率 <FieldTip module="quote" field="risk_buffer_rate" /></template>
                <el-input-number
                  v-model="form.risk_buffer_rate"
                  :min="0"
                  :max="1"
                  :precision="2"
                  :step="0.05"
                  :controls="false"
                  style="width: 100%"
                  :disabled="isAcceptedReadOnly"
                />
              </el-form-item>
            </div>
            <div class="form-grid">
              <el-form-item>
                <template #label>折扣金额 <FieldTip module="quote" field="discount_amount" /></template>
                <el-input-number
                  v-model="form.discount_amount"
                  :min="0"
                  :precision="2"
                  :controls="false"
                  style="width: 100%"
                  :disabled="isAcceptedReadOnly"
                />
              </el-form-item>
              <el-form-item>
                <template #label>税率 <FieldTip module="quote" field="tax_rate" /></template>
                <el-input-number
                  v-model="form.tax_rate"
                  :min="0"
                  :max="1"
                  :precision="4"
                  :step="0.01"
                  :controls="false"
                  style="width: 100%"
                  :disabled="isAcceptedReadOnly"
                />
              </el-form-item>
            </div>
            <el-form-item label="备注">
              <el-input
                v-model="form.notes"
                type="textarea"
                :rows="2"
                placeholder="备注信息（可选）"
              />
            </el-form-item>
          </el-form>
        </div>

        <!-- Preview Panel -->
        <div class="preview-panel" v-if="previewData">
          <div class="preview-title">报价预览</div>
          <div class="preview-rows">
            <div class="preview-row">
              <span class="preview-label">人工成本</span>
              <span class="preview-value mono">¥{{ formatAmount(previewData.labor_amount) }}</span>
            </div>
            <div class="preview-row">
              <span class="preview-label">基础金额</span>
              <span class="preview-value mono">¥{{ formatAmount(previewData.base_amount) }}</span>
            </div>
            <div class="preview-row">
              <span class="preview-label">缓冲金额</span>
              <span class="preview-value mono">¥{{ formatAmount(previewData.buffer_amount) }}</span>
            </div>
            <el-divider style="margin: 8px 0" />
            <div class="preview-row">
              <span class="preview-label">小计</span>
              <span class="preview-value mono">¥{{ formatAmount(previewData.subtotal_amount) }}</span>
            </div>
            <div class="preview-row">
              <span class="preview-label">税额</span>
              <span class="preview-value mono">¥{{ formatAmount(previewData.tax_amount) }}</span>
            </div>
            <el-divider style="margin: 8px 0" />
            <div class="preview-row total-row">
              <span class="preview-label">总价</span>
              <span class="preview-value mono">¥{{ formatAmount(previewData.total_amount) }}</span>
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
    <el-dialog v-model="detailVisible" :title="detailData ? detailData.quote_no : ''" width="700px" destroy-on-close>
      <template #header>
        <div style="display: flex; align-items: center; gap: 12px;">
          <span style="font-size: 16px; font-weight: 600;">{{ detailData?.quote_no }}</span>
          <el-tag :type="statusTypes[detailData?.status] || 'info'" size="small" round>
            {{ statusLabels[detailData?.status] || detailData?.status }}
          </el-tag>
          <el-tag v-if="detailData?.status === 'expired'" type="danger" size="small" effect="dark" round>已过期</el-tag>
        </div>
      </template>
      <div v-if="detailData" class="detail-content">
        <div class="detail-section">
          <div class="detail-section-title">基本信息</div>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">报价标题</span>
              <span class="detail-value">{{ detailData.title }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">客户</span>
              <span class="detail-value">{{ getCustomerName(detailData.customer_id) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">有效期至</span>
              <span class="detail-value mono">{{ detailData.valid_until }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">状态</span>
              <span class="detail-value">{{ statusLabels[detailData.status] || detailData.status }}</span>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <div class="detail-section-title">需求与工期</div>
          <div class="detail-block">{{ detailData.requirement_summary || '—' }}</div>
          <div class="detail-grid" style="margin-top: 12px;">
            <div class="detail-item">
              <span class="detail-label">预计工期</span>
              <span class="detail-value mono">{{ detailData.estimate_days }} 天</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">日费率</span>
              <span class="detail-value mono">{{ detailData.daily_rate != null ? '¥' + detailData.daily_rate : '—' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">直接成本</span>
              <span class="detail-value mono">{{ detailData.direct_cost != null ? '¥' + detailData.direct_cost : '—' }}</span>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <div class="detail-section-title">费用明细</div>
          <div class="detail-grid detail-grid-3">
            <div class="detail-item">
              <span class="detail-label">风险缓冲率</span>
              <span class="detail-value mono">{{ detailData.risk_buffer_rate != null ? (Number(detailData.risk_buffer_rate) * 100).toFixed(0) + '%' : '—' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">折扣金额</span>
              <span class="detail-value mono">¥{{ formatAmount(detailData.discount_amount) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">税率</span>
              <span class="detail-value mono">{{ detailData.tax_rate != null ? (Number(detailData.tax_rate) * 100).toFixed(2) + '%' : '—' }}</span>
            </div>
          </div>
          <div class="detail-grid detail-grid-3" style="margin-top: 12px;">
            <div class="detail-item">
              <span class="detail-label">小计</span>
              <span class="detail-value mono">¥{{ formatAmount(detailData.subtotal_amount) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">税额</span>
              <span class="detail-value mono">¥{{ formatAmount(detailData.tax_amount) }}</span>
            </div>
            <div class="detail-item highlight">
              <span class="detail-label">总价</span>
              <span class="detail-value mono">¥{{ formatAmount(detailData.total_amount) }}</span>
            </div>
          </div>
        </div>

        <div class="detail-section" v-if="detailData.notes">
          <div class="detail-section-title">备注</div>
          <div class="detail-block">{{ detailData.notes }}</div>
        </div>

        <div class="detail-section" v-if="detailData.status === 'accepted' && !detailData.converted_contract_id">
          <el-alert type="success" :closable="false" style="margin-bottom: 12px;">
            <template #title>该报价已被客户接受</template>
          </el-alert>
          <el-button type="primary" @click="handleConvertFromDetail(detailData)">
            一键转合同
          </el-button>
        </div>

        <div class="detail-section" v-if="detailData.converted_contract_id">
          <el-alert type="info" :closable="false">
            <template #title>已关联合同编号: {{ detailData.converted_contract_id }}</template>
          </el-alert>
        </div>

        <div class="detail-section" v-if="detailData.status === 'expired'">
          <el-alert type="warning" :closable="false">
            <template #title>此报价已过期</template>
          </el-alert>
        </div>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, MoreFilled } from '@element-plus/icons-vue'
import FieldTip from '../components/FieldTip.vue'
import PageHelpDrawer from '../components/PageHelpDrawer.vue'
import {
  getQuotations, getQuotation, createQuotation, updateQuotation, deleteQuotation,
  convertToContract, sendQuotation, acceptQuotation, rejectQuotation,
  cancelQuotation, previewQuotation,
} from '../api/quotations'
import { getCustomers } from '../api/customers'

const records = ref([])
const total = ref(0)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const statusFilter = ref('')
const customerFilter = ref('')
const searchQuery = ref('')
const customerOptions = ref([])

const dialogVisible = ref(false)
const editingId = ref(null)
const submitting = ref(false)
const formRef = ref(null)
const editingStatus = ref('')

const detailVisible = ref(false)
const detailData = ref(null)

const previewData = ref(null)
let previewTimer = null

const statusLabels = {
  draft: '草稿', sent: '已发送', accepted: '已接受',
  rejected: '已拒绝', expired: '已过期', cancelled: '已取消',
}
const statusTypes = {
  draft: 'info', sent: 'primary', accepted: 'success',
  rejected: 'danger', expired: 'warning', cancelled: 'info',
}

const form = ref({
  title: '',
  customer_id: null,
  requirement_summary: '',
  estimate_days: 5,
  daily_rate: null,
  direct_cost: null,
  risk_buffer_rate: 0,
  discount_amount: 0,
  tax_rate: 0,
  valid_until: '',
  notes: '',
})

const formRules = {
  title: [{ required: true, message: '请输入报价标题', trigger: 'blur' }],
  customer_id: [{ required: true, message: '请选择客户', trigger: 'change' }],
  requirement_summary: [{ required: true, message: '请输入需求摘要', trigger: 'blur' }],
  estimate_days: [{ required: true, message: '请输入预计工期', trigger: 'blur' }],
  valid_until: [{ required: true, message: '请选择有效期', trigger: 'change' }],
}

const isAcceptedReadOnly = computed(() => editingStatus.value === 'accepted')

const canEdit = (status) => ['draft', 'sent'].includes(status)

const isExpired = (row) => row.status === 'expired'

const hasStatusActions = (row) => {
  if (row.status === 'draft') return true
  if (row.status === 'sent') return true
  return false
}

const getCustomerName = (id) => {
  const c = customerOptions.value.find(c => c.id === id)
  return c ? c.name : '—'
}

const formatAmount = (val) => {
  if (val == null) return '0.00'
  return Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const loadData = async () => {
  loading.value = true
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
    }
    if (statusFilter.value) params.status = statusFilter.value
    if (customerFilter.value) params.customer_id = customerFilter.value
    if (searchQuery.value) params.search = searchQuery.value
    const { data } = await getQuotations(params)
    records.value = data.items
    total.value = data.total
  } catch {
    ElMessage.error('加载报价单失败')
  } finally {
    loading.value = false
  }
}

const loadCustomers = async () => {
  try {
    const { data } = await getCustomers({ limit: 100 })
    customerOptions.value = data.items || data
  } catch { /* ignore */ }
}

const openCreate = () => {
  editingId.value = null
  editingStatus.value = ''
  const today = new Date()
  const defaultValidUntil = new Date(today.getTime() + 30 * 86400000)
  form.value = {
    title: '', customer_id: null, requirement_summary: '',
    estimate_days: 5, daily_rate: null, direct_cost: null,
    risk_buffer_rate: 0, discount_amount: 0, tax_rate: 0,
    valid_until: defaultValidUntil.toISOString().slice(0, 10),
    notes: '',
  }
  previewData.value = null
  dialogVisible.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  editingStatus.value = row.status
  form.value = {
    title: row.title,
    customer_id: row.customer_id,
    requirement_summary: row.requirement_summary || '',
    estimate_days: row.estimate_days,
    daily_rate: row.daily_rate != null ? Number(row.daily_rate) : null,
    direct_cost: row.direct_cost != null ? Number(row.direct_cost) : null,
    risk_buffer_rate: row.risk_buffer_rate != null ? Number(row.risk_buffer_rate) : 0,
    discount_amount: row.discount_amount != null ? Number(row.discount_amount) : 0,
    tax_rate: row.tax_rate != null ? Number(row.tax_rate) : 0,
    valid_until: row.valid_until,
    notes: row.notes || '',
  }
  previewData.value = null
  dialogVisible.value = true
}

const openDetail = async (row) => {
  try {
    const { data } = await getQuotation(row.id)
    detailData.value = data
    detailVisible.value = true
  } catch {
    ElMessage.error('加载报价详情失败')
  }
}

const buildPreviewPayload = () => {
  const f = form.value
  if (!f.estimate_days || f.estimate_days <= 0) return null
  return {
    estimate_days: f.estimate_days,
    daily_rate: f.daily_rate != null ? String(f.daily_rate) : null,
    direct_cost: f.direct_cost != null ? String(f.direct_cost) : null,
    risk_buffer_rate: f.risk_buffer_rate != null ? String(f.risk_buffer_rate) : '0',
    discount_amount: f.discount_amount != null ? String(f.discount_amount) : '0',
    tax_rate: f.tax_rate != null ? String(f.tax_rate) : '0',
  }
}

const fetchPreview = async () => {
  const payload = buildPreviewPayload()
  if (!payload) { previewData.value = null; return }
  try {
    const { data } = await previewQuotation(payload)
    previewData.value = data
  } catch {
    previewData.value = null
  }
}

const schedulePreview = () => {
  clearTimeout(previewTimer)
  previewTimer = setTimeout(fetchPreview, 300)
}

watch(() => [
  form.value.estimate_days, form.value.daily_rate, form.value.direct_cost,
  form.value.risk_buffer_rate, form.value.discount_amount, form.value.tax_rate,
], () => {
  if (dialogVisible.value && !isAcceptedReadOnly.value) {
    schedulePreview()
  }
}, { deep: true })

watch(dialogVisible, (val) => {
  if (!val) {
    clearTimeout(previewTimer)
    previewData.value = null
  } else if (!editingId.value) {
    fetchPreview()
  }
})

const submitForm = async () => {
  try {
    await formRef.value.validate()
  } catch { return }
  submitting.value = true
  try {
    const payload = { ...form.value }
    // Clean null optional fields — remove old values when fields are hidden
    if (payload.daily_rate == null) payload.daily_rate = null
    if (payload.direct_cost == null) payload.direct_cost = null

    if (editingId.value) {
      // For accepted quotes, only send notes
      if (editingStatus.value === 'accepted') {
        await updateQuotation(editingId.value, { notes: payload.notes })
      } else {
        await updateQuotation(editingId.value, payload)
      }
      ElMessage.success('报价单已更新')
    } else {
      await createQuotation(payload)
      ElMessage.success('报价单已创建')
    }
    dialogVisible.value = false
    loadData()
  } catch {
    // Error handled by interceptor
  } finally {
    submitting.value = false
  }
}

const changeStatus = async (row, newStatus) => {
  const labels = { sent: '发送', accepted: '接受', rejected: '拒绝', cancelled: '取消' }
  try {
    await ElMessageBox.confirm(
      `确认将此报价单标记为"${labels[newStatus]}"？`,
      '状态变更',
    )
    if (newStatus === 'sent') await sendQuotation(row.id)
    else if (newStatus === 'accepted') await acceptQuotation(row.id)
    else if (newStatus === 'rejected') await rejectQuotation(row.id)
    else if (newStatus === 'cancelled') await cancelQuotation(row.id)
    ElMessage.success('状态已更新')
    loadData()
  } catch { /* cancelled */ }
}

const handleConvert = async (row) => {
  try {
    await ElMessageBox.confirm('确认将此报价单转为合同草稿？此操作不可撤销。', '一键转合同', { type: 'warning' })
    await convertToContract(row.id)
    ElMessage.success('已成功转为合同草稿')
    loadData()
  } catch { /* cancelled */ }
}

const handleConvertFromDetail = async (row) => {
  try {
    await ElMessageBox.confirm('确认将此报价单转为合同草稿？此操作不可撤销。', '一键转合同', { type: 'warning' })
    await convertToContract(row.id)
    ElMessage.success('已成功转为合同草稿')
    detailVisible.value = false
    loadData()
  } catch { /* cancelled */ }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确认删除此报价单？', '删除确认', { type: 'warning' })
    await deleteQuotation(row.id)
    ElMessage.success('报价单已删除')
    loadData()
  } catch { /* cancelled */ }
}

onMounted(() => {
  loadData()
  loadCustomers()
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

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.pagination-bar {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

.mono {
  font-family: 'SF Mono', 'Monaco', 'Cascadia Code', monospace;
}

.contract-no {
  font-weight: 600;
  color: var(--brand-cyan, #0891b2);
}

.expired-text {
  color: var(--el-color-danger, #f56c6c);
}

.converted-tag {
  font-size: 12px;
  color: var(--el-color-success, #67c23a);
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

/* Edit Layout */
.edit-layout {
  display: flex;
  gap: 24px;
}

.edit-form {
  flex: 1;
  min-width: 0;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

/* Preview Panel */
.preview-panel {
  width: 240px;
  flex-shrink: 0;
  background: var(--bg-soft, #f8fafc);
  border: 1px solid var(--border-light, #e2e8f0);
  border-radius: 8px;
  padding: 16px;
  height: fit-content;
  position: sticky;
  top: 0;
}

.preview-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.preview-rows {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.preview-value {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.total-row .preview-label,
.total-row .preview-value {
  font-size: 15px;
  font-weight: 700;
  color: var(--brand-cyan, #0891b2);
}

/* Detail Content */
.detail-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.detail-section {
  /* no special style needed */
}

.detail-section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border-subtle, #f1f5f9);
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 24px;
}

.detail-grid-3 {
  grid-template-columns: repeat(3, 1fr);
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.detail-item.highlight {
  background: var(--bg-soft, #f8fafc);
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-light, #e2e8f0);
}

.detail-label {
  font-size: 12px;
  color: var(--text-tertiary, #94a3b8);
}

.detail-value {
  font-size: 14px;
  color: var(--text-primary);
}

.detail-block {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.6;
  white-space: pre-wrap;
}

/* Status Dots */
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

@media (max-width: 768px) {
  .edit-layout {
    flex-direction: column;
  }
  .preview-panel {
    width: 100%;
  }
  .detail-grid, .detail-grid-3 {
    grid-template-columns: 1fr;
  }
}
</style>
