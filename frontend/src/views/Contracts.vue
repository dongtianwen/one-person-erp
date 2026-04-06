<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-title-group">
        <span class="header-count mono">总计：{{ total }} 份合同</span>
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
            <span class="mono contract-no-link">{{ row.contract_no }}</span>
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
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <div class="action-btns">
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import api from '../api'
import { getCustomers } from '../api/customers'
import { getProjects } from '../api/projects'

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

onMounted(() => { loadData(); loadCustomers(); loadProjects() })
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
</style>
