<template>
  <div class="leads-view">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <div style="display: flex; align-items: center; gap: 12px">
        <h2 style="margin: 0; font-size: 18px">客户线索台账</h2>
        <PageHelpDrawer pageKey="leads_page" />
      </div>
      <el-button type="primary" @click="formVisible = true">创建线索</el-button>
    </div>

    <el-tabs v-model="activeTab" @tab-change="loadList">
      <el-tab-pane label="全部" name="all" />
      <el-tab-pane
        v-for="s in LEAD_STATUSES"
        :key="s.value"
        :label="s.label"
        :name="s.value"
      />
    </el-tabs>

    <el-table :data="list" v-loading="loading" stripe size="small">
      <el-table-column label="来源" width="120">
        <template #default="{ row }">
          {{ getSourceLabel(row.source) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="LEAD_STATUS_TAG_TYPE[row.status]" size="small">
            {{ getStatusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="next_action" label="下次动作" min-width="160" show-overflow-tooltip />
      <el-table-column label="关联客户" width="120">
        <template #default="{ row }">
          {{ getClientName(row.client_id) }}
        </template>
      </el-table-column>
      <el-table-column label="关联项目" width="120">
        <template #default="{ row }">
          {{ getProjectName(row.project_id) }}
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">
          {{ row.created_at?.replace('T', ' ').slice(0, 16) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="canAdvance(row.status)"
            link type="success" size="small"
            @click="handleAdvance(row)"
          >推进到下一阶段</el-button>
          <el-button link type="primary" size="small" @click="editRow = row; formVisible = true">编辑</el-button>
          <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && !list.length" :description="emptyDesc" />

    <LeadFormDialog
      v-model="formVisible"
      :edit-data="editRow"
      @success="onFormSuccess"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import LeadFormDialog from './LeadFormDialog.vue'
import { getLeads, updateLead, deleteLead } from '../../api/ledger'
import { getCustomers } from '../../api/customers'
import { getProjects } from '../../api/projects'
import { LEAD_STATUSES, LEAD_SOURCES, LEAD_STATUS_TAG_TYPE, LEAD_TRANSITIONS } from '../../constants/status'
import { useApiWarning } from '../../composables/useApiWarning'
import PageHelpDrawer from '../../components/PageHelpDrawer.vue'

const { handleResponse } = useApiWarning()

const loading = ref(false)
const list = ref([])
const activeTab = ref('all')
const formVisible = ref(false)
const editRow = ref(null)
const clients = ref([])
const projects = ref([])

const emptyDesc = computed(() => {
  if (activeTab.value === 'all') return '暂无线索'
  const status = LEAD_STATUSES.find((s) => s.value === activeTab.value)
  return status ? `暂无${status.label}线索` : '暂无线索'
})

function getStatusLabel(status) {
  return LEAD_STATUSES.find((s) => s.value === status)?.label || status
}

function getSourceLabel(source) {
  return LEAD_SOURCES.find((s) => s.value === source)?.label || source
}

function getClientName(id) {
  if (!id) return '-'
  return clients.value.find((c) => c.id === id)?.name || id
}

function getProjectName(id) {
  if (!id) return '-'
  return projects.value.find((p) => p.id === id)?.name || id
}

function canAdvance(status) {
  const transitions = LEAD_TRANSITIONS[status] || []
  return transitions.some((t) => t !== 'invalid')
}

function getNextStatus(status) {
  const transitions = LEAD_TRANSITIONS[status] || []
  return transitions.find((t) => t !== 'invalid') || null
}

async function loadList() {
  loading.value = true
  try {
    const params = {}
    if (activeTab.value !== 'all') params.status = activeTab.value
    const { data } = await getLeads(params)
    list.value = data.items || []
  } catch {
    list.value = []
  } finally {
    loading.value = false
  }
}

async function handleAdvance(row) {
  const nextStatus = getNextStatus(row.status)
  if (!nextStatus) return
  const nextLabel = getStatusLabel(nextStatus)
  try {
    await ElMessageBox.confirm(`确定将此线索推进到「${nextLabel}」？`, '确认', { type: 'info' })
    const { data } = await updateLead(row.id, { status: nextStatus })
    handleResponse(data)
    ElMessage.success(`已推进到${nextLabel}`)
    loadList()
  } catch { /* cancelled or error */ }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定删除此线索？', '确认', { type: 'warning' })
    const { data } = await deleteLead(row.id)
    handleResponse(data)
    ElMessage.success('删除成功')
    loadList()
  } catch { /* cancelled or error */ }
}

function onFormSuccess() {
  editRow.value = null
  loadList()
}

onMounted(async () => {
  loadList()
  try {
    const [custRes, projRes] = await Promise.all([getCustomers(), getProjects()])
    clients.value = custRes.data?.items || custRes.data || []
    projects.value = projRes.data?.items || projRes.data || []
  } catch { /* ignore */ }
})
</script>
