<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-title-group">
        <span class="header-count mono">总计：{{ total }} 条记录</span>
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
        <el-table-column type="selection" width="40" />
        <el-table-column prop="quotation_number" label="报价编号" width="160">
          <template #default="{ row }">
            <span class="mono contract-no">{{ row.quotation_number }}</span>
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
        <el-table-column prop="amount" label="报价金额" width="120" align="right">
          <template #default="{ row }">
            <span class="mono">¥{{ (row.amount || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="validity_date" label="有效期至" width="110">
          <template #default="{ row }">
            <span class="mono">{{ row.validity_date }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <div class="action-btns">
              <el-button link type="primary" size="small" @click="openEdit(row)">
                {{ canEdit(row.status) ? '编辑' : '查看' }}
              </el-button>
              <el-button link type="success" size="small" @click="handleConvert(row)" v-if="row.status === 'accepted' && !row.contract_id">转合同</el-button>
              <el-dropdown trigger="click" v-if="['draft', 'sent'].includes(row.status)" placement="bottom-end">
                <el-button link type="info" size="small" style="padding: 0 4px">
                  <el-icon><MoreFilled /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item v-if="row.status === 'draft'" @click="changeStatus(row, 'sent')" style="color: var(--el-color-success)">发送给客户</el-dropdown-item>
                    <el-dropdown-item v-if="row.status === 'sent'" @click="changeStatus(row, 'accepted')" style="color: var(--el-color-success)">客户已接受</el-dropdown-item>
                    <el-dropdown-item v-if="row.status === 'sent'" @click="changeStatus(row, 'rejected')" style="color: var(--el-color-warning)">客户已拒绝</el-dropdown-item>
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
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑报价单' : '新建报价单'" width="600px" destroy-on-close>
      <el-form :model="form" :rules="formRules" ref="formRef" label-position="top">
        <el-form-item label="报价标题" prop="title">
          <el-input v-model="form.title" maxlength="200" placeholder="请输入报价标题" />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="客户" prop="customer_id">
            <el-select v-model="form.customer_id" filterable placeholder="选择客户" style="width: 100%">
              <el-option v-for="c in customerOptions" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="报价金额" prop="amount">
            <el-input-number v-model="form.amount" :min="0" :precision="2" :controls="false" style="width: 100%" />
          </el-form-item>
        </div>
        <el-form-item label="有效期至" prop="validity_date">
          <el-date-picker v-model="form.validity_date" type="date" value-format="YYYY-MM-DD" placeholder="选择有效期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="报价内容">
          <el-input v-model="form.content" type="textarea" :rows="4" maxlength="5000" show-word-limit placeholder="报价内容详情" />
        </el-form-item>
        <el-form-item label="折扣说明">
          <el-input v-model="form.discount_note" maxlength="500" show-word-limit placeholder="折扣说明（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, MoreFilled } from '@element-plus/icons-vue'
import { getQuotations, createQuotation, updateQuotation, deleteQuotation, convertToContract } from '../api/quotations'
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

const form = ref({
  title: '',
  customer_id: null,
  amount: 0,
  validity_date: '',
  content: '',
  discount_note: '',
})

const formRules = {
  title: [{ required: true, message: '请输入报价标题', trigger: 'blur' }],
  customer_id: [{ required: true, message: '请选择客户', trigger: 'change' }],
  amount: [{ required: true, message: '请输入报价金额', trigger: 'blur' }],
  validity_date: [{ required: true, message: '请选择有效期', trigger: 'change' }],
}

const statusLabels = { draft: '草稿', sent: '已发送', accepted: '已接受', rejected: '已拒绝', expired: '已过期' }
const statusTypes = { draft: 'info', sent: 'primary', accepted: 'success', rejected: 'danger', expired: 'warning' }

const canEdit = (status) => ['draft', 'sent'].includes(status)

const getCustomerName = (id) => {
  const c = customerOptions.value.find(c => c.id === id)
  return c ? c.name : '-'
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
  form.value = { title: '', customer_id: null, amount: 0, validity_date: '', content: '', discount_note: '' }
  dialogVisible.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  form.value = {
    title: row.title,
    customer_id: row.customer_id,
    amount: row.amount,
    validity_date: row.validity_date,
    content: row.content || '',
    discount_note: row.discount_note || '',
  }
  dialogVisible.value = true
}

const submitForm = async () => {
  try {
    await formRef.value.validate()
  } catch { return }
  submitting.value = true
  try {
    if (editingId.value) {
      await updateQuotation(editingId.value, form.value)
      ElMessage.success('报价单已更新')
    } else {
      await createQuotation(form.value)
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
  const labels = { sent: '发送', accepted: '接受', rejected: '拒绝' }
  try {
    await ElMessageBox.confirm(`确认将此报价单标记为"${labels[newStatus]}"？`, '状态变更')
    await updateQuotation(row.id, { status: newStatus })
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

.header-title-group h2 {
  margin: 0;
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

.contract-no {
  font-weight: 600;
  color: var(--brand-cyan, #0891b2);
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
</style>
