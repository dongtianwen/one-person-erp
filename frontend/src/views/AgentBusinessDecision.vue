<template>
  <div class="agent-page">
    <div class="page-header">
      <h2>经营决策 Agent</h2>
      <PageHelpDrawer pageKey="agent_decision" />
      <div class="header-actions">
        <el-switch
          v-model="useLlM"
          active-text="AI 增强"
          inactive-text="规则模式"
          :disabled="running"
          inline-prompt
        />
        <el-button type="primary" @click="handleRun" :loading="running" :disabled="running">
          {{ running ? '分析中...' : '立即运行' }}
        </el-button>
        <el-button @click="fetchRuns" :disabled="running">刷新</el-button>
        <el-button @click="$router.push('/agents/settings')" icon="Setting" circle title="前往 Agent 设置" />
      </div>
    </div>

    <!-- 运行中状态 -->
    <el-card v-if="running" class="running-card" shadow="never">
      <div class="running-status">
        <el-icon class="running-icon" :size="32"><Loading /></el-icon>
        <div class="running-text">
          <h3>AI 正在分析中...</h3>
          <p v-if="useLlM">正在扫描业务数据并由 AI 生成专家建议</p>
          <p v-if="runningModel" style="font-family: monospace; font-size: 13px; color: #ffd700;">{{ runningModel }}</p>
          <p v-else-if="!useLlM">使用规则引擎进行分析</p>
          <div style="display: flex; align-items: center; gap: 16px; margin-top: 12px;">
            <p class="hint" style="font-family: monospace; font-size: 14px; color: #fff; margin: 0;">已用时：{{ formattedTimer }}</p>
            <el-button type="danger" plain size="small" @click="cancelRun">终止分析</el-button>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 最近运行结果摘要 -->
    <el-card v-if="currentRun && !running" class="result-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>最近分析概览</span>
          <el-tag :type="statusTag(currentRun.status)" size="small">{{ currentRun.status }}</el-tag>
        </div>
      </template>
      <el-descriptions :column="3" border size="small">
        <el-descriptions-item label="任务 ID">#{{ currentRun.id }}</el-descriptions-item>
        <el-descriptions-item label="分析方式">{{ currentRun.llm_enhanced ? 'AI 增强型' : '基础规则型' }}</el-descriptions-item>
        <el-descriptions-item label="建议数量">{{ currentRun.suggestion_count }}</el-descriptions-item>
        <el-descriptions-item label="完成时间">{{ formatTime(currentRun.completed_at) || '-' }}</el-descriptions-item>
        <el-descriptions-item label="AI 模型" :span="2">{{ currentRun.llm_provider || '未记录' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 待确认建议列表 -->
    <el-card class="suggestion-card" shadow="hover" style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <span>待确认建议箱</span>
          <el-tag type="warning" size="small">{{ suggestions.length }} 条待处理</el-tag>
        </div>
      </template>
      <el-table :data="suggestions" stripe style="width: 100%">
        <el-table-column prop="priority" label="优先级" width="90">
          <template #default="{ row }">
            <el-tag :type="priorityType(row.priority)" size="small" effect="dark">{{ row.priority }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="核心建议" width="200" />
        <el-table-column label="详情描述" min-width="300">
          <template #default="{ row }">
            <div style="white-space: pre-wrap; line-height: 1.6; padding: 4px 0;">{{ row.description }}</div>
          </template>
        </el-table-column>
        <el-table-column label="数据源" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.llm_enhanced" type="success" size="small" plain>AI</el-tag>
            <el-tag v-else type="info" size="small" plain>规则</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="handleConfirm(row, 'accepted')">接受</el-button>
            <el-button size="small" type="danger" plain @click="handleConfirm(row, 'rejected')">忽略</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 确认对话框 -->
    <el-dialog v-model="confirmVisible" title="确认 AI 建议" width="550px" destroy-on-close>
      <el-form :model="confirmForm" label-width="80px">
        <el-form-item label="建议主题"><strong>{{ confirmForm.title }}</strong></el-form-item>
        <el-form-item label="建议正文">
          <div style="background: #f8f9fa; padding: 12px; border-radius: 4px; border-left: 4px solid #409eff;">{{ confirmForm.description }}</div>
        </el-form-item>
        <el-form-item label="反馈/备注">
          <el-input v-model="confirmForm.reason" type="textarea" :rows="3" placeholder="填写您的处理理由或修改意见，AI 将学习您的偏好..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="confirmVisible = false">取消</el-button>
        <el-button type="primary" @click="submitConfirm">确认执行</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading, Setting } from '@element-plus/icons-vue'
import {
  runBusinessDecision,
  getPendingSuggestions,
  confirmSuggestion,
  getAgentRuns,
  getAgentConfig,
} from '../api/agents'
import PageHelpDrawer from '../components/PageHelpDrawer.vue'

const running = ref(false)
const useLlM = ref(true)
const currentModel = ref('')
const agentTimer = ref(0)
const currentRun = ref(null)
const suggestions = ref([])
const confirmVisible = ref(false)
const confirmForm = ref({ id: null, title: '', description: '', decision: '', reason: '' })
const runningModel = ref('')

let abortController = null
let timerId = null

const formattedTimer = computed(() => {
  const m = Math.floor(agentTimer.value / 60)
  const s = agentTimer.value % 60
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
})

const handleRun = async () => {
  running.value = true
  agentTimer.value = 0
  timerId = setInterval(() => {
    agentTimer.value++
  }, 1000)

  abortController = new AbortController()
  runningModel.value = useLlM.value ? (currentModel.value || 'gemma4:e2b:q4') : ''

  try {
    const res = await runBusinessDecision(useLlM.value, abortController.signal)
    ElMessage.success('分析机运行完成')
    await fetchRuns()
    await fetchSuggestions()
  } catch (e) {
    if (e.name === 'CanceledError' || e.name === 'AbortError') {
      ElMessage.info('已停止当前分析')
    } else {
      ElMessage.error('运行失败')
    }
  } finally {
    running.value = false
    clearInterval(timerId)
    runningModel.value = ''
  }
}

const cancelRun = () => {
  if (abortController) {
    abortController.abort()
  }
}

const formatTime = (t) => {
  if (!t) return ''
  const d = new Date(t)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const fetchRuns = async () => {
  try {
    const { data } = await getAgentRuns({ limit: 1, agent_type: 'business_decision' })
    if (data && data.length > 0) {
      currentRun.value = data[0]
    }
  } catch (e) {
    console.error('获取运行记录失败', e)
  }
}

const fetchSuggestions = async () => {
  try {
    const { data } = await getPendingSuggestions({ agent_type: 'business_decision' })
    const sorted = [...(data || [])].sort((a, b) => b.id - a.id)
    const seen = {}
    const deduped = []
    for (const item of sorted) {
      if (!seen[item.suggestion_type]) {
        seen[item.suggestion_type] = true
        deduped.push(item)
      }
    }
    suggestions.value = deduped
  } catch (e) {
    console.error('获取建议失败', e)
  }
}

const handleConfirm = (row, decision) => {
  confirmForm.value = {
    id: row.id,
    title: row.title,
    description: row.description,
    decision: decision,
    reason: ''
  }
  confirmVisible.value = true
}

const submitConfirm = async () => {
  try {
    await confirmSuggestion(confirmForm.value.id, {
      decision_type: confirmForm.value.decision,
      free_text_reason: confirmForm.value.reason
    })
    ElMessage.success('已登记决策')
    confirmVisible.value = false
    await fetchSuggestions()
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '确认失败'
    const code = e?.response?.data?.code || ''
    if (code === 'SUGGESTION_NOT_PENDING') {
      ElMessage.warning('该建议已被处理，将刷新列表')
      confirmVisible.value = false
      await fetchSuggestions()
    } else {
      ElMessage.error(msg)
    }
  }
}

const priorityType = (p) => {
  const map = { high: 'danger', medium: 'warning', low: 'info' }
  return map[p] || 'info'
}

const statusTag = (s) => {
  const map = { completed: 'success', running: 'primary', failed: 'danger' }
  return map[s] || 'info'
}

onMounted(async () => {
  fetchRuns()
  fetchSuggestions()
  try {
    const { data } = await getAgentConfig()
    if (data) {
      currentModel.value = data.local_model || 'gemma4:e2b:q4'
    }
  } catch (e) {
    console.error('获取配置失败', e)
  }
})

onBeforeUnmount(() => {
  if (timerId) clearInterval(timerId)
})
</script>

<style scoped>
.agent-page { padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-header h2 { margin: 0; font-weight: 600; color: #303133; }
.header-actions { display: flex; align-items: center; gap: 12px; }

.running-card {
  background: linear-gradient(135deg, #409eff 0%, #3a8ee6 100%);
  color: white;
  border: none;
  margin-bottom: 20px;
  border-radius: 12px;
}
.running-status { display: flex; align-items: center; gap: 20px; padding: 10px; }
.running-icon { animation: rotate 2s linear infinite; }
@keyframes rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.running-text h3 { margin: 0 0 4px 0; font-size: 18px; }
.running-text p { margin: 2px 0; opacity: 0.9; font-size: 13px; }

.result-card, .suggestion-card { border-radius: 8px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.ml-2 { margin-left: 8px; }
</style>
