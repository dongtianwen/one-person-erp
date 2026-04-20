<template>
  <div class="tool-entries-view">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <div style="display: flex; align-items: center; gap: 12px">
        <h2 style="margin: 0; font-size: 18px">工具入口台账</h2>
        <PageHelpDrawer pageKey="tool_entries_page" />
      </div>
      <el-button type="primary" @click="formVisible = true">创建工具入口</el-button>
    </div>

    <el-tabs v-model="activeTab" @tab-change="loadList">
      <el-tab-pane label="全部" name="all" />
      <el-tab-pane
        v-for="s in TOOL_ENTRY_STATUSES"
        :key="s.value"
        :label="s.label"
        :name="s.value"
      />
    </el-tabs>

    <el-table :data="list" v-loading="loading" stripe size="small">
      <el-table-column prop="action_name" label="动作名称" min-width="140" />
      <el-table-column prop="tool_name" label="工具名称" min-width="120" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="TOOL_STATUS_TAG_TYPE[row.status]" size="small">
            {{ getStatusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="已回填" width="80" align="center">
        <template #default="{ row }">
          <el-icon v-if="row.is_backfilled" color="#10b981"><Check /></el-icon>
          <span v-else style="color: #94a3b8">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="notes" label="备注" min-width="120" show-overflow-tooltip />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'pending' || row.status === 'in_progress'"
            link type="success" size="small"
            @click="handleMarkDone(row)"
          >标记已完成</el-button>
          <el-button
            v-if="row.status === 'done'"
            link type="warning" size="small"
            @click="handleMarkBackfilled(row)"
          >标记已回填</el-button>
          <el-button link type="primary" size="small" @click="editRow = row; formVisible = true">编辑</el-button>
          <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && !list.length" :description="emptyDesc" />

    <ToolEntryFormDialog
      v-model="formVisible"
      :edit-data="editRow"
      @success="onFormSuccess"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check } from '@element-plus/icons-vue'
import ToolEntryFormDialog from './ToolEntryFormDialog.vue'
import { getToolEntries, updateToolEntryStatus, deleteToolEntry } from '../../api/ledger'
import { TOOL_ENTRY_STATUSES, TOOL_STATUS_TAG_TYPE } from '../../constants/status'
import { useApiWarning } from '../../composables/useApiWarning'
import PageHelpDrawer from '../../components/PageHelpDrawer.vue'

const { handleResponse } = useApiWarning()

const loading = ref(false)
const list = ref([])
const activeTab = ref('all')
const formVisible = ref(false)
const editRow = ref(null)

const emptyDesc = computed(() => {
  if (activeTab.value === 'all') return '暂无工具记录'
  const status = TOOL_ENTRY_STATUSES.find((s) => s.value === activeTab.value)
  return status ? `暂无${status.label}工具记录` : '暂无工具记录'
})

function getStatusLabel(status) {
  return TOOL_ENTRY_STATUSES.find((s) => s.value === status)?.label || status
}

async function loadList() {
  loading.value = true
  try {
    const params = {}
    if (activeTab.value !== 'all') params.status = activeTab.value
    const { data } = await getToolEntries(params)
    list.value = data.items || []
  } catch {
    list.value = []
  } finally {
    loading.value = false
  }
}

async function handleMarkDone(row) {
  try {
    const { data } = await updateToolEntryStatus(row.id, { status: 'done' })
    handleResponse(data)
    ElMessage.success('已标记为完成')
    loadList()
  } catch { /* error handled */ }
}

async function handleMarkBackfilled(row) {
  try {
    const { data } = await updateToolEntryStatus(row.id, { status: 'backfilled', is_backfilled: true })
    handleResponse(data)
    ElMessage.success('已标记为回填')
    loadList()
  } catch { /* error handled */ }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定删除此工具入口？', '确认', { type: 'warning' })
    const { data } = await deleteToolEntry(row.id)
    handleResponse(data)
    ElMessage.success('删除成功')
    loadList()
  } catch { /* cancelled or error */ }
}

function onFormSuccess() {
  editRow.value = null
  loadList()
}

onMounted(() => { loadList() })
</script>
