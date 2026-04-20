<template>
  <div class="minutes-list-view">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <div style="display: flex; align-items: center; gap: 12px">
        <h2 style="margin: 0; font-size: 18px">会议纪要</h2>
        <PageHelpDrawer pageKey="minutes_page" />
      </div>
      <el-button type="primary" @click="formVisible = true">创建纪要</el-button>
    </div>

    <div style="display: flex; gap: 12px; margin-bottom: 16px">
      <el-select v-model="filterProject" clearable placeholder="按项目筛选" filterable style="width: 200px" @change="loadList">
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-select v-model="filterClient" clearable placeholder="按客户筛选" filterable style="width: 200px" @change="loadList">
        <el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.id" />
      </el-select>
    </div>

    <el-table :data="list" v-loading="loading" stripe size="small">
      <el-table-column prop="title" label="标题" min-width="160" />
      <el-table-column label="关联项目" width="140">
        <template #default="{ row }">
          {{ getProjectName(row.project_id) }}
        </template>
      </el-table-column>
      <el-table-column label="关联客户" width="140">
        <template #default="{ row }">
          {{ getCustomerName(row.client_id) }}
        </template>
      </el-table-column>
      <el-table-column prop="meeting_date" label="会议日期" width="120" />
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">
          {{ row.created_at?.replace('T', ' ').slice(0, 16) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="$router.push(`/minutes/${row.id}`)">详情</el-button>
          <el-button link type="primary" size="small" @click="editRow = row; formVisible = true">编辑</el-button>
          <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && !list.length" description="暂无会议纪要" />

    <div v-if="total > pageSize" style="margin-top: 16px; display: flex; justify-content: flex-end">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="loadList"
      />
    </div>

    <MinutesFormDialog
      v-model="formVisible"
      :edit-data="editRow"
      @success="onFormSuccess"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import MinutesFormDialog from './MinutesFormDialog.vue'
import { getMinutes, deleteMinutes } from '../../api/minutes'
import { getProjects } from '../../api/projects'
import { getCustomers } from '../../api/customers'
import { useApiWarning } from '../../composables/useApiWarning'
import PageHelpDrawer from '../../components/PageHelpDrawer.vue'

const { handleResponse } = useApiWarning()

const loading = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const formVisible = ref(false)
const editRow = ref(null)
const filterProject = ref(null)
const filterClient = ref(null)
const projects = ref([])
const customers = ref([])

function getProjectName(id) {
  if (!id) return '-'
  return projects.value.find((p) => p.id === id)?.name || id
}

function getCustomerName(id) {
  if (!id) return '-'
  return customers.value.find((c) => c.id === id)?.name || id
}

async function loadList() {
  loading.value = true
  try {
    const params = {
      limit: pageSize,
      offset: (page.value - 1) * pageSize,
    }
    if (filterProject.value) params.project_id = filterProject.value
    if (filterClient.value) params.client_id = filterClient.value
    const { data } = await getMinutes(params)
    list.value = data.items || []
    total.value = data.total || 0
  } catch {
    list.value = []
  } finally {
    loading.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定删除此纪要？', '确认', { type: 'warning' })
    const { data } = await deleteMinutes(row.id)
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
  try {
    const [projRes, custRes] = await Promise.all([getProjects(), getCustomers()])
    projects.value = projRes.data?.items || projRes.data || []
    customers.value = custRes.data?.items || custRes.data || []
  } catch { /* ignore */ }
  loadList()
})
</script>
