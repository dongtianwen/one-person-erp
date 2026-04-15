<template>
  <div class="agent-logs-page">
    <div class="page-header">
      <h2>Agent 运行日志</h2>
      <el-button @click="fetchRuns" :loading="loading">刷新</el-button>
    </div>

    <!-- 加载状态 -->
    <el-card v-if="loading && runs.length === 0" class="loading-card">
      <div class="loading-status">
        <el-icon class="loading-icon" :size="32"><Loading /></el-icon>
        <p>正在加载运行记录...</p>
      </div>
    </el-card>

    <!-- 筛选 -->
    <el-form :inline="true" class="filter-form">
      <el-form-item label="Agent 类型">
        <el-select v-model="filters.agent_type" placeholder="全部" clearable @change="fetchRuns">
          <el-option label="经营决策" value="business_decision" />
          <el-option label="项目管理" value="project_management" />
        </el-select>
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="filters.status" placeholder="全部" clearable @change="fetchRuns">
          <el-option label="完成" value="completed" />
          <el-option label="失败" value="failed" />
          <el-option label="运行中" value="running" />
        </el-select>
      </el-form-item>
    </el-form>

    <!-- 运行列表 -->
    <el-table :data="runs" stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="agent_type" label="类型" width="130">
        <template #default="{ row }">
          {{ row.agent_type === 'business_decision' ? '经营决策' : '项目管理' }}
        </template>
      </el-table-column>
      <el-table-column prop="llm_provider" label="Provider" width="100" />
      <el-table-column prop="llm_enhanced" label="LLM" width="80">
        <template #default="{ row }">
          {{ row.llm_enhanced ? 'Yes' : 'No' }}
        </template>
      </el-table-column>
      <el-table-column prop="suggestion_count" label="建议数" width="80" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="error_message" label="错误信息" show-overflow-tooltip />
      <el-table-column prop="created_at" label="时间" width="160">
        <template #default="{ row }">
          {{ formatTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80">
        <template #default="{ row }">
          <el-button size="small" @click="viewDetail(row)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="运行详情" width="700px">
      <div v-if="detailRun">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="ID">{{ detailRun.id }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTag(detailRun.status)">{{ detailRun.status }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="LLM Provider">{{ detailRun.llm_provider }}</el-descriptions-item>
          <el-descriptions-item label="LLM 增强">{{ detailRun.llm_enhanced ? '是' : '否' }}</el-descriptions-item>
        </el-descriptions>

        <h4 style="margin-top: 16px">建议列表</h4>
        <el-table :data="detailRun.suggestions" size="small" stripe>
          <el-table-column prop="priority" label="优先级" width="80">
            <template #default="{ row }">
              <el-tag :type="priorityType(row.priority)" size="small">{{ row.priority }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="title" label="标题" />
          <el-table-column prop="status" label="状态" width="80" />
          <el-table-column label="来源" width="80">
            <template #default="{ row }">
              <el-tag v-if="row.llm_enhanced" type="success" size="small">AI</el-tag>
              <el-tag v-else type="info" size="small">规则</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { getAgentRuns, getAgentRun } from '../api/agents'

const runs = ref([])
const loading = ref(false)
const filters = ref({ agent_type: '', status: '' })
const detailVisible = ref(false)
const detailRun = ref(null)

const statusTag = (s) => ({ completed: 'success', failed: 'danger', running: 'warning' }[s] || 'info')
const priorityType = (p) => ({ high: 'danger', medium: 'warning', low: 'info' }[p] || 'info')

const formatTime = (t) => {
  if (!t) return ''
  const d = new Date(t)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const fetchRuns = async () => {
  loading.value = true
  try {
    const params = { limit: 50 }
    if (filters.value.agent_type) params.agent_type = filters.value.agent_type
    if (filters.value.status) params.status = filters.value.status
    const { data } = await getAgentRuns(params)
    runs.value = data || []
  } catch (e) {
    ElMessage.error('加载运行记录失败')
    runs.value = []
  } finally {
    loading.value = false
  }
}

const viewDetail = async (row) => {
  detailRun.value = null
  detailVisible.value = true
  try {
    const { data } = await getAgentRun(row.id)
    detailRun.value = data
  } catch (e) {
    ElMessage.error('加载详情失败')
    detailVisible.value = false
  }
}

onMounted(fetchRuns)
</script>

<style scoped>
.agent-logs-page { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; }
.filter-form { margin-bottom: 16px; }
.loading-card {
  text-align: center;
  padding: 40px 20px;
}
.loading-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}
.loading-icon {
  animation: rotate 1s linear infinite;
  color: #409eff;
}
@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.loading-status p {
  color: #909399;
  margin: 0;
}
</style>
