<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-title-group">
        <h2>财务管理</h2>
        <span class="header-count mono">{{ total }} 条记录</span>
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新建记录
      </el-button>
    </div>

    <el-card>
      <div class="filter-bar">
        <el-select v-model="typeFilter" placeholder="类型" clearable style="width: 110px" @change="loadData">
          <el-option label="收入" value="income" />
          <el-option label="支出" value="expense" />
        </el-select>
        <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 130px" @change="loadData">
          <el-option v-for="(label, val) in statusLabels" :key="val" :label="label" :value="val" />
        </el-select>
        <el-button type="primary" @click="loadData">筛选</el-button>
      </div>

      <!-- Funding Source Stats -->
      <div v-if="Object.keys(fundingStats.funding_sources || {}).length" class="stats-bar">
        <div v-for="(amount, source) in fundingStats.funding_sources" :key="source" class="stat-chip">
          <span class="stat-label">{{ fundingSourceLabels[source] || source }}</span>
          <span class="stat-value mono">¥{{ (amount || 0).toLocaleString() }}</span>
        </div>
        <div v-if="fundingStats.unclosed_advances > 0" class="stat-chip warning">
          <span class="stat-label">未报销垫付</span>
          <span class="stat-value mono">{{ fundingStats.unclosed_advances }} 笔</span>
        </div>
        <div v-if="fundingStats.unclosed_loans > 0" class="stat-chip warning">
          <span class="stat-label">未归还借款</span>
          <span class="stat-value mono">{{ fundingStats.unclosed_loans }} 笔</span>
        </div>
      </div>

      <el-table :data="records" style="width: 100%" v-loading="loading">
        <el-table-column prop="type" label="类型" width="80">
          <template #default="{ row }">
            <div class="type-indicator" :class="row.type">
              {{ row.type === 'income' ? '收' : '支' }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="金额" width="130">
          <template #default="{ row }">
            <span class="mono amount-cell" :class="row.type">
              {{ row.type === 'income' ? '+' : '-' }}¥{{ (row.amount || 0).toLocaleString() }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="100">
          <template #default="{ row }">
            {{ categoryLabels[row.category] || row.category }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="180" show-overflow-tooltip />
        <el-table-column prop="date" label="日期" width="110">
          <template #default="{ row }">
            <span class="mono">{{ row.date }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="invoice_no" label="发票号" width="130">
          <template #default="{ row }">
            <span class="mono">{{ row.invoice_no || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTypes[row.status] || 'info'" size="small" round>
              {{ statusLabels[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="funding_source" label="资金来源" width="100">
          <template #default="{ row }">
            <span v-if="row.funding_source">{{ fundingSourceLabels[row.funding_source] || row.funding_source }}</span>
            <span v-else class="text-tertiary">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="settlement_status" label="结算状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="needsSettlement(row)" :type="settlementType(row.settlement_status)" size="small" round>
              {{ settlementLabels[row.settlement_status] || row.settlement_status }}
            </el-tag>
            <span v-else class="text-tertiary">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="editRecord(row)">编辑</el-button>
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

    <el-dialog v-model="showDialog" :title="editingId ? '编辑记录' : '新建记录'" width="560px" destroy-on-close>
      <el-form :model="form" label-position="top">
        <div class="form-grid">
          <el-form-item label="类型" required>
            <el-select v-model="form.type" style="width: 100%">
              <el-option label="收入" value="income" />
              <el-option label="支出" value="expense" />
            </el-select>
          </el-form-item>
          <el-form-item label="金额" required>
            <el-input-number v-model="form.amount" :min="0" :precision="2" style="width: 100%" />
          </el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item label="分类">
            <el-select v-model="form.category" style="width: 100%">
              <el-option v-for="(label, val) in categoryLabels" :key="val" :label="label" :value="val" />
            </el-select>
          </el-form-item>
          <el-form-item label="日期" required>
            <el-date-picker v-model="form.date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </div>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="简要描述（选填）" />
        </el-form-item>
        <el-form-item label="关联合同">
          <el-select v-model="form.contract_id" placeholder="选择合同" filterable clearable style="width: 100%">
            <el-option v-for="c in contracts" :key="c.id" :label="`${c.title} (${c.contract_no})`" :value="c.id" />
          </el-select>
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="发票号">
            <el-input v-model="form.invoice_no" placeholder="发票编号" />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="form.status" style="width: 100%">
              <el-option v-for="(label, val) in statusLabels" :key="val" :label="label" :value="val" />
            </el-select>
          </el-form-item>
        </div>
        <!-- v1.1 资金来源 -->
        <el-form-item label="资金来源" :required="form.type === 'expense'">
          <el-select v-model="form.funding_source" placeholder="选择资金来源" clearable style="width: 100%">
            <el-option v-for="(label, val) in fundingSourceLabels" :key="val" :label="label" :value="val" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.funding_source === 'personal_advance' || form.funding_source === 'loan'" label="业务说明" required>
          <el-input v-model="form.business_note" type="textarea" :rows="2" placeholder="说明垫付或借款原因" />
        </el-form-item>
        <el-form-item v-if="form.funding_source === 'personal_advance' || form.funding_source === 'loan'" label="结算状态" required>
          <el-select v-model="form.settlement_status" placeholder="选择结算状态" style="width: 100%">
            <el-option v-for="(label, val) in settlementLabels" :key="val" :label="label" :value="val" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联记录">
          <el-select v-model="form.related_record_id" placeholder="选择关联记录" filterable clearable style="width: 100%">
            <el-option v-for="r in records" :key="r.id" :label="`${r.type === 'income' ? '收' : '支'} ¥${(r.amount || 0).toLocaleString()} - ${r.description || r.date}`" :value="r.id" :disabled="r.id === editingId" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.related_record_id" label="关联说明" required>
          <el-input v-model="form.related_note" placeholder="说明关联关系，如'报销张三2026-03-01垫付'" />
        </el-form-item>
      </el-form>

      <!-- Change History -->
      <div v-if="editingId && changelogs.length" class="changelog-section">
        <div class="changelog-header">变更历史</div>
        <div class="changelog-list">
          <div v-for="log in changelogs" :key="log.id" class="changelog-item">
            <div class="changelog-field">{{ fieldLabels[log.field] || log.field }}</div>
            <div class="changelog-values">
              <span class="old-val">{{ log.old_value || '空' }}</span>
              <span class="arrow">→</span>
              <span class="new-val">{{ log.new_value || '空' }}</span>
            </div>
            <div class="changelog-time">{{ formatTime(log.created_at) }}</div>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">{{ editingId ? '保存修改' : '创建记录' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '../api'

const records = ref([])
const fundingStats = ref({ funding_sources: {}, unclosed_advances: 0, unclosed_loans: 0 })
const contracts = ref([])
const changelogs = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const typeFilter = ref('')
const statusFilter = ref('')
const showDialog = ref(false)
const editingId = ref(null)
const defaultForm = { type: 'income', amount: 0, category: 'other', description: '', date: '', contract_id: null, invoice_no: '', status: 'pending', funding_source: 'company_account', business_note: '', related_record_id: null, related_note: '', settlement_status: null }
const form = ref({ ...defaultForm })

const statusLabels = { pending: '待确认', confirmed: '已确认', invoiced: '已开票', paid: '已付款', cancelled: '已取消' }
const fundingSourceLabels = {
  company_account: '对公账户',
  personal_advance: '个人垫付',
  reimbursement: '报销',
  loan: '借款',
  loan_repayment: '借款归还',
  other: '其他',
}
const statusTypes = { pending: 'warning', confirmed: 'success', invoiced: 'info', paid: 'success', cancelled: 'danger' }
const categoryLabels = { development: '开发费', design: '设计费', maintenance: '维护费', server: '服务器', office: '办公', other: '其他', '项目收入': '项目收入', 人力: '人力', 外包: '外包' }
const fieldLabels = { type: '类型', amount: '金额', category: '分类', description: '描述', date: '日期', contract_id: '关联合同', invoice_no: '发票号', status: '状态' }

const settlementLabels = { open: '未结清', partial: '部分归还', closed: '已结清' }
const settlementTypes = { open: 'danger', partial: 'warning', closed: 'success' }
const needsSettlement = (row) => ['personal_advance', 'loan'].includes(row.funding_source) && row.settlement_status

const loadData = async () => {
  loading.value = true
  try {
    const params = { skip: (page.value - 1) * pageSize.value, limit: pageSize.value }
    if (typeFilter.value) params.type = typeFilter.value
    if (statusFilter.value) params.status = statusFilter.value
    const { data } = await api.get('/finances', { params })
    records.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

const loadFundingStats = async () => {
  try {
    const now = new Date()
    const { data } = await api.get('/finances/stats/funding-source', {
      params: { year: now.getFullYear(), month: now.getMonth() + 1 }
    })
    fundingStats.value = data
  } catch { /* silently degrade */ }
}

const loadContracts = async () => {
  try {
    const { data } = await api.get('/contracts', { params: { skip: 0, limit: 100 } })
    contracts.value = data.items
  } catch {
    contracts.value = []
  }
}

const openCreate = () => {
  editingId.value = null
  form.value = { ...defaultForm }
  showDialog.value = true
}

const editRecord = (row) => {
  editingId.value = row.id
  form.value = { ...row }
  changelogs.value = []
  showDialog.value = true
  loadChangelogs(row.id)
}

const loadChangelogs = async (recordId) => {
  try {
    const { data } = await api.get('/changelogs', { params: { entity_type: 'finance_record', entity_id: recordId } })
    changelogs.value = data
  } catch {
    changelogs.value = []
  }
}

const formatTime = (ts) => {
  if (!ts) return ''
  const d = new Date(ts)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}

const handleSubmit = async () => {
  if (!form.value.amount || !form.value.date) { ElMessage.warning('请填写金额和日期'); return }
  if (form.value.type === 'expense' && !form.value.funding_source) { ElMessage.warning('支出记录必须填写资金来源'); return }
  if (['personal_advance', 'loan'].includes(form.value.funding_source) && !form.value.business_note) { ElMessage.warning('个人垫付/借款必须填写业务说明'); return }
  if (['personal_advance', 'loan'].includes(form.value.funding_source) && !form.value.settlement_status) { ElMessage.warning('个人垫付/借款必须填写结算状态'); return }
  if (form.value.related_record_id && !form.value.related_note) { ElMessage.warning('关联记录时必须填写关联说明'); return }
  try {
    if (editingId.value) {
      await api.put(`/finances/${editingId.value}`, form.value)
      ElMessage.success('更新成功')
    } else {
      await api.post('/finances', form.value)
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    loadData()
  } catch { /* handled */ }
}

onMounted(() => { loadData(); loadContracts(); loadFundingStats() })
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

.filter-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.type-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
}

.type-indicator.income {
  background: var(--brand-emerald-glow);
  color: var(--brand-emerald);
}

.type-indicator.expense {
  background: var(--brand-rose-glow);
  color: var(--brand-rose);
}

.amount-cell {
  font-weight: 600;
}

.amount-cell.income { color: var(--brand-emerald); }
.amount-cell.expense { color: var(--brand-rose); }

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

:deep(.el-form-item__label) {
  padding-bottom: 4px;
}

/* ---- Changelog ---- */
.changelog-section {
  margin-top: 12px;
  padding-top: 16px;
  border-top: 1px dashed var(--border-default);
}

.changelog-header {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.changelog-list {
  max-height: 200px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.changelog-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: var(--el-fill-color-lighter);
  border-radius: var(--el-border-radius-base);
  font-size: 12px;
}

.changelog-field {
  font-weight: 600;
  color: var(--text-primary);
  min-width: 56px;
}

.changelog-values {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
}

.old-val {
  text-decoration: line-through;
  color: var(--text-tertiary);
}

.arrow {
  color: var(--text-tertiary);
}

.new-val {
  color: var(--brand-emerald);
  font-weight: 500;
}

.changelog-time {
  color: var(--text-tertiary);
  font-size: 11px;
  white-space: nowrap;
}
.stats-bar {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.stat-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: var(--el-fill-color-lighter);
  border-radius: 16px;
  font-size: 13px;
}

.stat-chip.warning {
  background: rgba(245, 158, 11, 0.1);
}

.stat-label {
  color: var(--text-secondary);
}

.stat-value {
  color: var(--text-primary);
  font-weight: 600;
}
</style>
