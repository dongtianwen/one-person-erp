<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-title-group">
        <h2>客户管理</h2>
        <span class="header-count mono">{{ total }} 位客户</span>
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新增客户
      </el-button>
    </div>

    <el-card>
      <!-- Filter Bar -->
      <div class="filter-bar">
        <el-input
          v-model="search"
          placeholder="搜索客户名称、电话、公司..."
          style="width: 280px"
          clearable
          :prefix-icon="Search"
          @clear="loadData"
          @keyup.enter="loadData"
        />
        <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 120px" @change="loadData">
          <el-option v-for="(label, val) in statusLabels" :key="val" :label="label" :value="val" />
        </el-select>
        <el-select v-model="sourceFilter" placeholder="来源" clearable style="width: 120px" @change="loadData">
          <el-option v-for="(label, val) in sourceLabels" :key="val" :label="label" :value="val" />
        </el-select>
        <el-button type="primary" @click="loadData">搜索</el-button>
      </div>

      <!-- Table -->
      <el-table :data="customers" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="客户名称" min-width="120">
          <template #default="{ row }">
            <div class="cell-name clickable" @click="goDetail(row.id)">{{ row.name }}</div>
            <div class="cell-sub">{{ row.company || '-' }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="contact_person" label="联系人" width="100" />
        <el-table-column prop="phone" label="电话" width="130">
          <template #default="{ row }">
            <span class="mono">{{ row.phone || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusTypes[row.status] || 'info'" size="small" round>
              {{ statusLabels[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="100">
          <template #default="{ row }">
            {{ sourceLabels[row.source] || row.source }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <div class="action-btns">
              <el-button link type="primary" size="small" @click="editCustomer(row)">编辑</el-button>
              <el-button link type="danger" size="small" @click="handleDelete(row.id)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
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

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="showDialog" :title="editingId ? '编辑客户' : '新增客户'" width="520px" destroy-on-close>
      <el-form :model="form" label-width="80px" label-position="top">
        <div class="form-grid">
          <el-form-item label="客户名称" required>
            <el-input v-model="form.name" placeholder="请输入客户名称" />
          </el-form-item>
          <el-form-item label="联系人">
            <el-input v-model="form.contact_person" placeholder="请输入联系人" />
          </el-form-item>
          <el-form-item label="电话">
            <el-input v-model="form.phone" placeholder="请输入电话" />
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input v-model="form.email" placeholder="请输入邮箱" />
          </el-form-item>
        </div>
        <el-form-item label="公司">
          <el-input v-model="form.company" placeholder="请输入公司名称" />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="来源">
            <el-select v-model="form.source" style="width: 100%">
              <el-option v-for="(label, val) in sourceLabels" :key="val" :label="label" :value="val" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="form.status" style="width: 100%">
              <el-option v-for="(label, val) in statusLabels" :key="val" :label="label" :value="val" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item v-if="form.status === 'lost'" label="流失原因" required>
          <el-input v-model="form.lost_reason" type="textarea" :rows="2" placeholder="请填写流失原因" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" placeholder="备注信息（选填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">{{ editingId ? '保存修改' : '创建客户' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { getCustomers, createCustomer, updateCustomer, deleteCustomer } from '../api/customers'

const router = useRouter()

const customers = ref([])
const loading = ref(false)
const search = ref('')
const statusFilter = ref('')
const sourceFilter = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showDialog = ref(false)
const editingId = ref(null)
const defaultForm = { name: '', contact_person: '', phone: '', email: '', company: '', source: 'other', status: 'potential', notes: '', lost_reason: '' }
const form = ref({ ...defaultForm })

const statusLabels = { potential: '潜在', follow_up: '跟进', deal: '成交', lost: '流失' }
const statusTypes = { potential: 'info', follow_up: 'warning', deal: 'success', lost: 'danger' }
const sourceLabels = { referral: '推荐', network: '网络', exhibition: '展会', social: '社交媒体', other: '其他' }

const loadData = async () => {
  loading.value = true
  try {
    const params = { skip: (page.value - 1) * pageSize.value, limit: pageSize.value }
    if (statusFilter.value) params.status = statusFilter.value
    if (sourceFilter.value) params.source = sourceFilter.value
    if (search.value) params.search = search.value
    const { data } = await getCustomers(params)
    customers.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  editingId.value = null
  form.value = { ...defaultForm }
  showDialog.value = true
}

const editCustomer = (row) => {
  editingId.value = row.id
  form.value = { ...row }
  showDialog.value = true
}

const handleSubmit = async () => {
  if (!form.value.name) { ElMessage.warning('请输入客户名称'); return }
  if (form.value.status === 'lost' && !form.value.lost_reason) { ElMessage.warning('流失原因必填'); return }
  try {
    if (editingId.value) {
      await updateCustomer(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await createCustomer(form.value)
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    loadData()
  } catch { /* handled */ }
}

const handleDelete = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除该客户？', '确认', { type: 'warning' })
    await deleteCustomer(id)
    ElMessage.success('删除成功')
    loadData()
  } catch { /* cancelled */ }
}

onMounted(loadData)

const goDetail = (id) => {
  router.push(`/customers/${id}`)
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

.filter-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.cell-name {
  font-weight: 500;
  color: var(--text-primary);
}

.cell-name.clickable {
  cursor: pointer;
  color: var(--brand-cyan, #0891b2);
}

.cell-name.clickable:hover {
  text-decoration: underline;
}

.cell-sub {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

.action-btns {
  display: flex;
  gap: 4px;
}

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
</style>
