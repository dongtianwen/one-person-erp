<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-title-group">
        <span class="header-count mono">总计：{{ total }} 条记录</span>
        <PageHelpDrawer pageKey="file_indexes" />
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新建文件
      </el-button>
    </div>

    <el-card>
      <div class="filter-bar">
        <el-select v-model="typeFilter" placeholder="文件类型" clearable style="width: 140px" @change="loadData">
          <el-option v-for="(label, val) in typeLabels" :key="val" :label="label" :value="val" />
        </el-select>
        <el-input
          v-model="keyword"
          placeholder="搜索文件名称..."
          clearable
          style="width: 250px"
          @clear="loadData"
          @keyup.enter="loadData"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="loadData">查询</el-button>
      </div>

      <el-table :data="records" style="width: 100%" v-loading="loading" row-key="id" @expand-change="handleExpand">
        <el-table-column type="selection" width="50" />
        <el-table-column type="expand" width="40">
          <template #default="{ row }">
            <div class="expand-content" v-loading="expandLoading[row.id]">
              <div class="expand-title">版本历史（{{ expandVersions[row.id]?.length || 0 }} 个版本）</div>
              <el-table :data="expandVersions[row.id] || []" size="small" border>
                <el-table-column prop="version" label="版本" width="80">
                  <template #default="{ row: v }">
                    <span v-if="v.version" class="mono version-badge">{{ v.version }}</span>
                    <span v-else class="text-tertiary">-</span>
                  </template>
                </el-table-column>
                <el-table-column prop="is_current" label="状态" width="70">
                  <template #default="{ row: v }">
                    <div class="status-dot-wrapper" style="background: transparent; border: none; padding: 0;">
                      <div class="status-dot" :class="v.is_current ? 'success' : 'info'"></div>
                      <span class="status-dot-text">{{ v.is_current ? '当前' : '历史' }}</span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column prop="issue_date" label="签发日期" width="100">
                  <template #default="{ row: v }">
                    <span class="mono">{{ v.issue_date || '-' }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="expiry_date" label="到期日期" width="100">
                  <template #default="{ row: v }">
                    <el-tag v-if="v.expiry_date" :type="expiryTagType(v.expiry_date)" size="small" round>
                      {{ v.expiry_date }}
                    </el-tag>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
                <el-table-column prop="storage_location" label="存放位置" min-width="120" show-overflow-tooltip>
                  <template #default="{ row: v }">
                    {{ v.storage_location || '-' }}
                  </template>
                </el-table-column>
                <el-table-column prop="note" label="备注" min-width="120" show-overflow-tooltip>
                  <template #default="{ row: v }">
                    {{ v.note || '-' }}
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="file_name" label="文件名称" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px;">
              <div class="status-dot-wrapper">
                <div class="status-dot" :class="row.is_current ? 'success' : 'info'"></div>
                <span class="status-dot-text">{{ row.is_current ? '当前' : '历史' }}</span>
              </div>
              <span style="font-weight: 500;">{{ row.file_name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="file_type" label="文件类型" width="110">
          <template #default="{ row }">
            {{ typeLabels[row.file_type] || row.file_type }}
          </template>
        </el-table-column>
        <el-table-column prop="version" label="版本" width="80">
          <template #default="{ row }">
            <span v-if="row.version" class="mono version-badge">{{ row.version }}</span>
            <span v-else class="text-tertiary">-</span>
          </template>
        </el-table-column>

        <el-table-column prop="issue_date" label="签发日期" width="110">
          <template #default="{ row }">
            <span class="mono">{{ row.issue_date || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="expiry_date" label="到期日期" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.expiry_date" :type="expiryTagType(row.expiry_date)" size="small" round>
              {{ row.expiry_date }}
            </el-tag>
            <span v-else class="text-tertiary">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="storage_location" label="存放位置" width="130" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.storage_location">{{ row.storage_location }}</span>
            <span v-else class="text-tertiary">-</span>
          </template>
        </el-table-column>
        <el-table-column label="关联对象" width="100">
          <template #default="{ row }">
            <router-link
              v-if="row.entity_type && row.entity_id"
              :to="entityLink(row)"
              class="entity-link"
            >
              {{ entityLabel(row) }}
            </router-link>
            <span v-else class="text-tertiary">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <div class="action-btns">
              <el-button link type="primary" size="small" @click="openVersion(row)">升版</el-button>
              <el-button link type="primary" size="small" @click="editRecord(row)">编辑</el-button>
              <el-dropdown trigger="click" placement="bottom-end">
                <el-button link type="info" size="small" style="padding: 0 4px">
                  <el-icon><MoreFilled /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item @click="handleDelete(row)" style="color: var(--el-color-danger)">删除此版本</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
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

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="showDialog" :title="editingId ? '编辑文件' : '新建文件'" width="600px" destroy-on-close>
      <el-form :model="form" label-position="top">
        <div class="form-grid">
          <el-form-item label="文件名称" required>
            <el-input v-model="form.file_name" placeholder="文件名称" />
          </el-form-item>
          <el-form-item label="文件类型" required>
            <el-select v-model="form.file_type" style="width: 100%">
              <el-option v-for="(label, val) in typeLabels" :key="val" :label="label" :value="val" />
            </el-select>
          </el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item label="版本号">
            <el-input v-model="form.version" placeholder="如 v1、v2.0" />
          </el-form-item>
          <el-form-item label="签发机关">
            <el-input v-model="form.issuing_authority" placeholder="签发机关（选填）" />
          </el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item label="签发日期">
            <el-date-picker v-model="form.issue_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="到期日期">
            <el-date-picker v-model="form.expiry_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </div>
        <el-form-item label="存放位置">
          <el-input v-model="form.storage_location" placeholder="文件存放位置（选填）" />
        </el-form-item>
        <el-form-item label="关联对象类型">
          <el-select v-model="form.entity_type" placeholder="选择关联类型" clearable style="width: 100%">
            <el-option label="合同" value="contract" />
            <el-option label="项目" value="project" />
            <el-option label="财务记录" value="finance_record" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" type="textarea" :rows="2" placeholder="备注信息（选填）" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">{{ editingId ? '保存修改' : '创建文件' }}</el-button>
      </template>
    </el-dialog>

    <!-- Version Dialog -->
    <el-dialog v-model="showVersionDialog" title="新建版本" width="480px" destroy-on-close>
      <el-form :model="versionForm" label-position="top">
        <el-form-item label="版本号">
          <el-input v-model="versionForm.version" placeholder="如 v2、v3.0" />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="签发日期">
            <el-date-picker v-model="versionForm.issue_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="到期日期">
            <el-date-picker v-model="versionForm.expiry_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </div>
        <el-form-item label="存放位置">
          <el-input v-model="versionForm.storage_location" placeholder="新版本存放位置" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="versionForm.note" type="textarea" :rows="2" placeholder="版本变更说明（选填）" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showVersionDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreateVersion">创建版本</el-button>
      </template>
    </el-dialog>

    <!-- Versions List Dialog -->
    <el-dialog v-model="showVersionsList" title="版本历史" width="640px" destroy-on-close>
      <el-table :data="versions" style="width: 100%" v-loading="versionsLoading">
        <el-table-column prop="version" label="版本" width="80">
          <template #default="{ row }">
            <span v-if="row.version" class="mono version-badge">{{ row.version }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_current" label="状态" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.is_current" type="success" size="small" round>当前</el-tag>
            <el-tag v-else type="info" size="small" round>历史</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="issue_date" label="签发日期" width="110">
          <template #default="{ row }">
            <span class="mono">{{ row.issue_date || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="expiry_date" label="到期日期" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.expiry_date" :type="expiryTagType(row.expiry_date)" size="small" round>
              {{ row.expiry_date }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="storage_location" label="存放位置" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.storage_location || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="note" label="备注" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.note || '-' }}
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, MoreFilled } from '@element-plus/icons-vue'
import {
  getFileIndexes,
  createFileIndex,
  updateFileIndex,
  deleteFileIndex,
  createFileVersion,
  getFileVersions,
} from '../api/fileIndexes'
import PageHelpDrawer from '../components/PageHelpDrawer.vue'

const typeLabels = {
  business_license: '营业执照',
  company_charter: '公司章程',
  lease_agreement: '租赁协议',
  audit_report: '审计报告',
  tax_registration: '税务备案',
  invoice: '发票',
  annual_report: '年度报告',
  contract: '合同文件',
  other: '其他',
}

const entityLink = (row) => {
  if (row.entity_type === 'contract') return '/contracts'
  if (row.entity_type === 'project') return '/projects'
  if (row.entity_type === 'finance_record') return '/finances'
  return '#'
}

const entityLabel = (row) => {
  const labels = { contract: '关联合同', project: '关联项目', finance_record: '关联财务' }
  return labels[row.entity_type] || row.entity_type
}

const records = ref([])
const versions = ref([])
const loading = ref(false)
const versionsLoading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const keyword = ref('')
const typeFilter = ref('')

const expandLoading = ref({})
const expandVersions = ref({})

const showDialog = ref(false)
const editingId = ref(null)
const showVersionDialog = ref(false)
const versionFileId = ref(null)
const showVersionsList = ref(false)

const defaultForm = {
  file_name: '',
  file_type: 'other',
  version: '',
  issue_date: '',
  expiry_date: '',
  storage_location: '',
  issuing_authority: '',
  note: '',
  entity_type: '',
  entity_id: null,
}
const form = ref({ ...defaultForm })

const defaultVersionForm = {
  version: '',
  issue_date: '',
  expiry_date: '',
  storage_location: '',
  note: '',
}
const versionForm = ref({ ...defaultVersionForm })

const expiryTagType = (d) => {
  if (!d) return 'info'
  const diff = (new Date(d) - new Date()) / 86400000
  if (diff < 0) return 'danger'
  if (diff <= 30) return 'warning'
  return 'info'
}

const loadData = async () => {
  loading.value = true
  try {
    const params = { skip: (page.value - 1) * pageSize.value, limit: pageSize.value }
    if (keyword.value) params.keyword = keyword.value
    if (typeFilter.value) params.file_type = typeFilter.value
    const { data } = await getFileIndexes(params)
    records.value = data.items
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

const editRecord = (row) => {
  editingId.value = row.id
  form.value = { ...row }
  showDialog.value = true
}

const handleSubmit = async () => {
  if (!form.value.file_name || !form.value.file_type) {
    ElMessage.warning('请填写文件名称和类型')
    return
  }
  try {
    if (editingId.value) {
      await updateFileIndex(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await createFileIndex(form.value)
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    loadData()
  } catch {
    /* handled by interceptor */
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除文件「${row.file_name}」？`, '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteFileIndex(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch {
    /* cancelled or handled */
  }
}

const openVersion = (row) => {
  versionFileId.value = row.id
  versionForm.value = { ...defaultVersionForm }
  showVersionDialog.value = true
}

const handleCreateVersion = async () => {
  try {
    await createFileVersion(versionFileId.value, versionForm.value)
    ElMessage.success('新版本已创建')
    showVersionDialog.value = false
    loadData()
  } catch {
    /* handled by interceptor */
  }
}

const loadVersions = async (row) => {
  if (!row.file_group_id) return
  expandLoading.value[row.id] = true
  try {
    const { data } = await getFileVersions(row.file_group_id)
    expandVersions.value[row.id] = data
  } finally {
    expandLoading.value[row.id] = false
  }
}

const handleExpand = (row) => {
  if (!expandVersions.value[row.id]) {
    loadVersions(row)
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
  gap: 10px;
}

.header-title-group h2 {
  margin: 0;
}

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

.version-badge {
  display: inline-block;
  padding: 2px 8px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
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

.text-tertiary {
  color: var(--text-tertiary);
}
.entity-link {
  color: var(--el-color-primary);
  text-decoration: none;
  font-size: 13px;
}
.entity-link:hover {
  text-decoration: underline;
}
</style>
