<template>
  <div class="invoices-tab">
    <!-- 已开票进度 -->
    <div v-if="invoiceSummary" class="invoice-progress">
      <div class="progress-item">
        <span class="progress-label">合同金额</span>
        <span class="mono progress-value">¥{{ contractAmount.toLocaleString(undefined, {minimumFractionDigits: 2}) }}</span>
      </div>
      <div class="progress-item">
        <span class="progress-label">已开票</span>
        <span class="mono progress-value">¥{{ Number(invoiceSummary.total_invoiced).toLocaleString(undefined, {minimumFractionDigits: 2}) }}</span>
      </div>
      <div class="progress-item">
        <span class="progress-label">进度</span>
        <span class="mono progress-value" :class="{'progress-warning': invoiceProgress >= 100, 'progress-full': invoiceProgress === 100}">
          {{ invoiceProgress.toFixed(1) }}%
        </span>
      </div>
    </div>

    <div class="tab-toolbar">
      <el-button type="primary" size="small" @click="openCreateInvoice">
        <el-icon><Plus /></el-icon> 新建发票
      </el-button>
    </div>

    <el-table :data="invoices" style="width:100%" size="small" v-loading="loading">
      <el-table-column prop="invoice_no" label="发票编号" width="150">
        <template #default="{ row }">
          <span class="mono">{{ row.invoice_no || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="invoice_type" label="类型" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="row.invoice_type === 'special' ? 'info' : undefined">
            {{ invoiceTypeLabels[row.invoice_type] || row.invoice_type }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="invoice_date" label="开票日期" width="110" />
      <el-table-column prop="amount_excluding_tax" label="金额(不含税)" width="120" align="right">
        <template #default="{ row }">
          <span class="mono">¥{{ (row.amount_excluding_tax || 0).toLocaleString(undefined, {minimumFractionDigits: 2}) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="tax_amount" label="税额" width="100" align="right">
        <template #default="{ row }">
          <span class="mono">¥{{ (row.tax_amount || 0).toLocaleString(undefined, {minimumFractionDigits: 2}) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="statusColor[row.status] ?? 'info'">
            {{ statusLabels[row.status] || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status === 'draft'" link size="small" type="primary" @click="handleIssue(row)">开具</el-button>
          <el-button v-if="row.status === 'issued'" link size="small" type="success" @click="handleReceive(row)">收票</el-button>
          <el-button v-if="row.status === 'received'" link size="small" type="primary" @click="handleVerify(row)">核销</el-button>
          <el-button v-if="['draft', 'issued', 'received'].includes(row.status)" link size="small" @click="editInvoice(row)">编辑</el-button>
          <el-button v-if="['draft', 'issued'].includes(row.status)" link size="small" type="danger" @click="handleCancel(row)">作废</el-button>
          <el-button v-if="['draft', 'issued', 'received'].includes(row.status)" link size="small" type="danger" @click="deleteInvoice(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="!invoices.length && !loading" class="empty-hint">暂无发票记录</div>

    <!-- 新建/编辑发票对话框 -->
    <el-dialog v-model="showInvoiceForm" :title="editingInvoice?.id ? '编辑发票' : '新建发票'" width="520px" destroy-on-close append-to-body>
      <el-form :model="invoiceForm" label-position="top" :rules="invoiceRules" ref="invoiceFormRef">
        <div class="form-grid">
          <el-form-item label="发票类型" prop="invoice_type">
            <el-select v-model="invoiceForm.invoice_type" style="width: 100%">
              <el-option label="普通发票" value="standard" />
              <el-option label="专用发票" value="special" />
            </el-select>
          </el-form-item>
          <el-form-item label="开票日期" prop="invoice_date">
            <el-date-picker v-model="invoiceForm.invoice_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item label="金额(不含税)" prop="amount_excluding_tax">
            <el-input-number v-model="invoiceForm.amount_excluding_tax" :min="0" :precision="2" style="width:100%" @change="calculateTax" />
          </el-form-item>
          <el-form-item label="税率" prop="tax_rate">
            <el-input-number v-model="invoiceForm.tax_rate" :min="0" :max="1" :step="0.01" :precision="2" style="width:100%" @change="calculateTax" />
          </el-form-item>
        </div>
        <el-form-item label="税额">
          <el-input-number v-model="invoiceForm.tax_amount" :min="0" :precision="2" disabled style="width:100%" />
        </el-form-item>
        <el-form-item label="价税合计">
          <el-input :value="`¥${totalAmount.toFixed(2)}`" disabled />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="invoiceForm.notes" type="textarea" :rows="2" placeholder="备注信息（选填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showInvoiceForm = false">取消</el-button>
        <el-button type="primary" @click="handleSaveInvoice">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  getContractInvoices,
  createInvoice,
  updateInvoice,
  deleteInvoice as deleteInvoiceApi,
  issueInvoice,
  receiveInvoice,
  verifyInvoice,
  cancelInvoice
} from '../../api/v18'

const props = defineProps({
  contractId: { type: Number, required: true },
  contractAmount: { type: Number, default: 0 }
})

const invoices = ref([])
const invoiceSummary = ref(null)
const loading = ref(false)
const showInvoiceForm = ref(false)
const editingInvoice = ref(null)
const invoiceFormRef = ref(null)

const invoiceForm = ref({
  invoice_type: 'standard',
  invoice_date: new Date().toISOString().split('T')[0],
  amount_excluding_tax: 0,
  tax_rate: 0.13,
  tax_amount: 0,
  notes: ''
})

const invoiceRules = {
  invoice_type: [{ required: true, message: '请选择发票类型' }],
  invoice_date: [{ required: true, message: '请选择开票日期' }],
  amount_excluding_tax: [{ required: true, message: '请输入金额' }]
}

const invoiceTypeLabels = { standard: '普通', special: '专用' }
const statusLabels = { draft: '草稿', issued: '已开票', received: '已收票', verified: '已核销', cancelled: '已作废' }
const statusColor = { draft: 'info', issued: 'warning', received: 'primary', verified: 'success', cancelled: 'danger' }

const invoiceProgress = computed(() => {
  if (!invoiceSummary.value || !props.contractAmount) return 0
  return (Number(invoiceSummary.value.total_invoiced) / Number(props.contractAmount)) * 100
})

const totalAmount = computed(() => {
  const amt = invoiceForm.value.amount_excluding_tax || 0
  const tax = invoiceForm.value.tax_amount || 0
  return amt + tax
})

const calculateTax = () => {
  const amt = invoiceForm.value.amount_excluding_tax || 0
  const rate = invoiceForm.value.tax_rate || 0
  invoiceForm.value.tax_amount = amt * rate
}

const loadInvoices = async () => {
  loading.value = true
  try {
    const { data } = await getContractInvoices(props.contractId)
    invoices.value = data.items || data
    // Calculate summary
    const totalInvoiced = invoices.value
      .filter(inv => inv.status !== 'cancelled')
      .reduce((sum, inv) => sum + Number(inv.amount_excluding_tax || 0) + Number(inv.tax_amount || 0), 0)
    invoiceSummary.value = { total_invoiced: totalInvoiced }
  } catch (err) {
    console.error('Failed to load invoices:', err)
  } finally {
    loading.value = false
  }
}

const openCreateInvoice = () => {
  editingInvoice.value = null
  invoiceForm.value = {
    invoice_type: 'standard',
    invoice_date: new Date().toISOString().split('T')[0],
    amount_excluding_tax: 0,
    tax_rate: 0.13,
    tax_amount: 0,
    notes: ''
  }
  showInvoiceForm.value = true
}

const editInvoice = (row) => {
  editingInvoice.value = row
  invoiceForm.value = {
    invoice_type: row.invoice_type,
    invoice_date: row.invoice_date,
    amount_excluding_tax: row.amount_excluding_tax,
    tax_rate: row.tax_rate,
    tax_amount: row.tax_amount,
    notes: row.notes || ''
  }
  showInvoiceForm.value = true
}

const handleSaveInvoice = async () => {
  if (!invoiceFormRef.value) return
  await invoiceFormRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      if (editingInvoice.value) {
        await updateInvoice(editingInvoice.value.id, invoiceForm.value)
        ElMessage.success('发票已更新')
      } else {
        await createInvoice({ ...invoiceForm.value, contract_id: props.contractId })
        ElMessage.success('发票已创建')
      }
      showInvoiceForm.value = false
      loadInvoices()
    } catch (err) {
      console.error('Failed to save invoice:', err)
    }
  })
}

const handleIssue = async (row) => {
  try {
    await issueInvoice(row.id)
    ElMessage.success('发票已开具')
    loadInvoices()
  } catch (err) {
    console.error('Failed to issue invoice:', err)
  }
}

const handleReceive = async (row) => {
  try {
    await receiveInvoice(row.id)
    ElMessage.success('已确认收票')
    loadInvoices()
  } catch (err) {
    console.error('Failed to receive invoice:', err)
  }
}

const handleVerify = async (row) => {
  try {
    await verifyInvoice(row.id)
    ElMessage.success('发票已核销')
    loadInvoices()
  } catch (err) {
    console.error('Failed to verify invoice:', err)
  }
}

const handleCancel = async (row) => {
  try {
    const { value: reason } = await ElMessageBox.prompt('请输入作废原因', '作废发票', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputPattern: /.+/,
      inputErrorMessage: '原因不能为空'
    })
    await cancelInvoice(row.id, reason)
    ElMessage.success('发票已作废')
    loadInvoices()
  } catch (err) {
    // User cancelled or error
    if (err !== 'cancel') {
      console.error('Failed to cancel invoice:', err)
    }
  }
}

const deleteInvoice = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除此发票吗？', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteInvoiceApi(row.id)
    ElMessage.success('发票已删除')
    loadInvoices()
  } catch (err) {
    if (err !== 'cancel') {
      console.error('Failed to delete invoice:', err)
    }
  }
}

watch(() => props.contractId, () => {
  if (props.contractId) {
    loadInvoices()
  }
}, { immediate: true })

defineExpose({ loadInvoices })
</script>

<style scoped>
.invoices-tab {
  padding: 0;
}

.invoice-progress {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--bg-soft, #f8fafc);
  border-radius: 6px;
}

.progress-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.progress-label {
  font-size: 12px;
  color: var(--text-tertiary, #94a3b8);
}

.progress-value {
  font-size: 16px;
  font-weight: 600;
}

.progress-warning {
  color: var(--el-color-warning);
}

.progress-full {
  color: var(--el-color-success);
}

.tab-toolbar {
  margin-bottom: 12px;
}

.empty-hint {
  color: #999;
  text-align: center;
  padding: 24px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

.mono {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
}
</style>
