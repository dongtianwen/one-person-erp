<template>
  <div class="agent-page">
    <div class="page-header">
      <div class="header-left">
        <h2>经营决策 Agent</h2>
        <span class="ai-badge"><el-icon :size="14"><MagicStick /></el-icon> AI 驱动</span>
      </div>
      <div class="header-actions">
        <PageHelpDrawer pageKey="agent_decision" />
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
    <div v-if="running" class="running-card">
      <div class="running-status">
        <div class="running-icon-wrapper">
          <el-icon class="running-icon" :size="36"><Loading /></el-icon>
        </div>
        <div class="running-text">
          <h3>AI 正在深度分析业务数据...</h3>
          <p v-if="useLlM">正在扫描财务、项目、客户数据并生成专家级决策建议</p>
          <p v-if="runningModel" class="model-tag">{{ runningModel }}</p>
          <p v-else-if="!useLlM">使用规则引擎进行基础分析</p>
          <div class="timer-bar">
            <span class="timer-text">{{ formattedTimer }}</span>
            <el-progress :percentage="Math.min(agentTimer / 30 * 100, 95)" :stroke-width="6" color="#ffd700" style="flex: 1; max-width: 200px;" />
            <el-button type="danger" plain size="small" @click="cancelRun">终止</el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 最近运行结果摘要 -->
    <div v-if="currentRun && !running" class="summary-bar">
      <div class="summary-item">
        <span class="label">分析时间</span>
        <span class="value">{{ formatTime(currentRun.completed_at) || '-' }}</span>
      </div>
      <div class="summary-divider" />
      <div class="summary-item">
        <span class="label">分析方式</span>
        <el-tag :type="currentRun.llm_enhanced ? 'success' : 'info'" size="small">{{ currentRun.llm_enhanced ? 'AI 增强' : '规则引擎' }}</el-tag>
      </div>
      <div class="summary-divider" />
      <div class="summary-item">
        <span class="label">生成建议</span>
        <span class="value highlight">{{ currentRun.suggestion_count }} 条</span>
      </div>
    </div>

    <!-- AI 决策建议卡片列表 -->
    <div class="decisions-section">
      <div class="section-header">
        <h3><el-icon :size="18"><ChatDotRound /></el-icon> AI 决策建议</h3>
        <el-badge :value="suggestions.length" :max="99" type="warning">
          <el-tag size="small" effect="dark" round>待处理</el-tag>
        </el-badge>
      </div>

      <div v-if="!suggestions.length" class="empty-state">
        <el-empty description="暂无 AI 建议，点击「立即运行」开始分析" />
      </div>

      <div v-else class="decision-cards">
        <div
          v-for="(item, idx) in suggestions"
          :key="item.id"
          class="decision-card"
          :class="[`priority-${item.priority}`, { 'anim-in': true }]"
          :style="{ animationDelay: `${idx * 0.1}s` }"
        >
          <!-- 卡片头部：结论 + 优先级 -->
          <div class="card-header">
            <div class="decision-conclusion">
              <el-icon class="conclusion-icon" :class="item.priority === 'high' ? 'pulse' : ''">
                <Warning v-if="item.priority === 'high'" />
                <InfoFilled v-else-if="item.priority === 'medium'" />
                <CircleCheck v-else />
              </el-icon>
              <span class="conclusion-text">{{ item.title }}</span>
            </div>
            <div class="card-meta">
              <el-tag :type="priorityType(item.priority)" size="small" effect="dark" round>{{ priorityLabel(item.priority) }}</el-tag>
              <el-tag v-if="item.llm_enhanced" type="success" size="small" plain round><el-icon :size="12"><MagicStick /></el-icon> AI</el-tag>
            </div>
          </div>

          <!-- 原因说明 -->
          <div class="card-body">
            <div class="reason-section">
              <span class="section-label"><el-icon :size="14"><Document /></el-icon> 分析依据</span>
              <p class="reason-text">{{ item.description }}</p>
            </div>

            <!-- 风险评分条 -->
            <div class="risk-section">
              <div class="risk-header">
                <span class="section-label"><el-icon :size="14"><Warning /></el-icon> 风险评估</span>
                <span class="risk-score" :class="riskLevelClass(item.risk_score)">{{ item.risk_score || '--' }} 分</span>
              </div>
              <div class="risk-bar-track">
                <div
                  class="risk-bar-fill"
                  :style="{ width: `${item.risk_score}%`, background: riskGradient(item.risk_score) }"
                />
              </div>
              <span class="risk-hint">{{ riskHint(item.risk_score) }}</span>
            </div>
          </div>

          <!-- 底部操作区 -->
          <div class="card-footer">
            <div class="action-hint">
              <span class="action-label">建议动作：</span>
              <span class="action-value">{{ actionLabel(item.suggested_action) }}</span>
            </div>
            <div class="action-buttons">
              <el-button size="small" type="success" @click="handleConfirm(item, 'accepted')">
                <el-icon :size="12"><CircleCheck /></el-icon> 采纳
              </el-button>
              <el-button size="small" @click="handleConfirm(item, 'postponed')">
                <el-icon :size="12"><Clock /></el-icon> 暂缓
              </el-button>
              <el-button size="small" type="info" plain @click="handleConfirm(item, 'rejected')">
                <el-icon :size="12"><Close /></el-icon> 忽略
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 确认对话框 -->
    <el-dialog v-model="confirmVisible" title="确认 AI 建议" width="520px" destroy-on-close>
      <div class="confirm-content">
        <div class="confirm-header">
          <el-icon :size="24" color="#409eff"><ChatDotRound /></el-icon>
          <strong>{{ confirmForm.title }}</strong>
        </div>
        <div class="confirm-desc">
          {{ confirmForm.description }}
        </div>
        <el-form :model="confirmForm" label-position="top">
          <el-form-item label="您的反馈（可选，AI 将学习您的偏好）">
            <el-input v-model="confirmForm.reason" type="textarea" :rows="3" placeholder="填写处理理由或修改意见..." />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="confirmVisible = false">取消</el-button>
        <el-button type="primary" @click="submitConfirm">确认执行</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Loading, Setting, MagicStick, ChatDotRound, Warning,
  InfoFilled, CircleCheck, Document, Clock, Close
} from '@element-plus/icons-vue'
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
  timerId = setInterval(() => { agentTimer.value++ }, 1000)

  abortController = new AbortController()
  runningModel.value = useLlM.value ? (currentModel.value || 'gemma4:e2b:q4') : ''

  try {
    const res = await runBusinessDecision(useLlM.value, abortController.signal)
    ElMessage.success('AI 分析完成')
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
  if (abortController) abortController.abort()
}

const formatTime = (t) => {
  if (!t) return ''
  const d = new Date(t)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const fetchRuns = async () => {
  try {
    const { data } = await getAgentRuns({ limit: 1, agent_type: 'business_decision' })
    if (data && data.length > 0) currentRun.value = data[0]
  } catch (e) { console.error('获取运行记录失败', e) }
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
  } catch (e) { console.error('获取建议失败', e) }
}

const handleConfirm = (row, decision) => {
  confirmForm.value = { id: row.id, title: row.title, description: row.description, decision, reason: '' }
  confirmVisible.value = true
}

const submitConfirm = async () => {
  try {
    await confirmSuggestion(confirmForm.value.id, {
      decision_type: confirmForm.value.decision,
      free_text_reason: confirmForm.value.reason
    })
    ElMessage.success('已登记您的决策')
    confirmVisible.value = false
    await fetchSuggestions()
  } catch (e) {
    const code = e?.response?.data?.code || ''
    if (code === 'SUGGESTION_NOT_PENDING') {
      ElMessage.warning('该建议已被处理')
      confirmVisible.value = false
      await fetchSuggestions()
    } else {
      ElMessage.error(e?.response?.data?.detail || e?.message || '确认失败')
    }
  }
}

// UI 辅助函数
const priorityType = (p) => ({ high: 'danger', medium: 'warning', low: 'info' })[p] || 'info'
const priorityLabel = (p) => ({ high: '高优先级', medium: '中优先级', low: '低优先级' })[p] || p

const actionLabel = (action) => ({
  pause_new_orders: '暂停新接单',
  create_reminder: '创建提醒',
  adjust_resource: '调整资源',
  continue_monitoring: '持续观察',
  create_todo: '创建任务',
  none: '无需操作',
})[action] || action

const riskLevelClass = (score) => {
  if (!score) return ''
  if (score >= 70) return 'risk-high'
  if (score >= 40) return 'risk-medium'
  return 'risk-low'
}

const riskGradient = (score) => {
  if (!score) return '#e6a23c'
  if (score >= 70) return 'linear-gradient(90deg, #f56c6c, #e63946)'
  if (score >= 40) return 'linear-gradient(90deg, #e6a23c, #f5a623)'
  return 'linear-gradient(90deg, #67c23a, #409eff)'
}

const riskHint = (score) => {
  if (!score) return '等待评估'
  if (score >= 70) return '高风险 - 建议立即处理'
  if (score >= 40) return '中风险 - 建议关注'
  return '低风险 - 可持续观察'
}

onMounted(async () => {
  fetchRuns()
  fetchSuggestions()
  try {
    const { data } = await getAgentConfig()
    if (data) currentModel.value = data.local_model || 'gemma4:e2b:q4'
  } catch (e) { console.error('获取配置失败', e) }
})

onBeforeUnmount(() => { if (timerId) clearInterval(timerId) })
</script>

<style scoped>
.agent-page { padding: 24px; max-width: 1200px; margin: 0 auto; }

.page-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 28px;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.header-left h2 { margin: 0; font-weight: 700; font-size: 22px; color: #1a1a2e; }
.ai-badge {
  display: inline-flex; align-items: center; gap: 4px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white; padding: 4px 12px; border-radius: 20px;
  font-size: 12px; font-weight: 500;
}
.header-actions { display: flex; align-items: center; gap: 10px; }

/* 运行状态 */
.running-card {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  border-radius: 16px; padding: 32px; margin-bottom: 24px;
  box-shadow: 0 8px 32px rgba(102, 126, 234, 0.25);
}
.running-status { display: flex; align-items: center; gap: 24px; }
.running-icon-wrapper {
  width: 72px; height: 72px; border-radius: 50%;
  background: rgba(255,255,255,0.08); display: flex; align-items: center; justify-content: center;
}
.running-icon { color: #ffd700; animation: rotate 2s linear infinite; }
@keyframes rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.running-text h3 { margin: 0 0 8px; font-size: 20px; color: #fff; }
.running-text p { margin: 4px 0; opacity: 0.85; font-size: 13px; color: #e0e0e0; }
.model-tag {
  font-family: monospace; background: rgba(255,215,0,0.15); color: #ffd700;
  padding: 2px 10px; border-radius: 4px; font-size: 12px; display: inline-block; margin-top: 6px;
}
.timer-bar { display: flex; align-items: center; gap: 12px; margin-top: 14px; }
.timer-text { font-family: monospace; color: #ffd700; font-size: 15px; min-width: 52px; }

/* 摘要栏 */
.summary-bar {
  display: flex; align-items: center; gap: 20px;
  background: linear-gradient(135deg, #f8f9ff 0%, #eef2ff 100%);
  padding: 16px 24px; border-radius: 12px; margin-bottom: 24px;
  border: 1px solid #e0e7ff;
}
.summary-item { display: flex; align-items: center; gap: 8px; }
.summary-item .label { color: #6b7280; font-size: 13px; }
.summary-item .value { font-weight: 600; color: #374151; font-size: 14px; }
.summary-item .value.highlight { color: #667eea; font-size: 16px; }
.summary-divider { width: 1px; height: 24px; background: #d1d5db; }

/* 决策区域 */
.decisions-section { margin-bottom: 32px; }
.section-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 18px;
}
.section-header h3 {
  margin: 0; font-size: 17px; font-weight: 600; color: #1a1a2e;
  display: flex; align-items: center; gap: 8px;
}
.empty-state { text-align: center; padding: 48px 0; }

/* 决策卡片 */
.decision-cards { display: grid; grid-template-columns: 1fr; gap: 16px; }

.decision-card {
  background: #fff; border-radius: 12px; border: 1px solid #e5e7eb;
  overflow: hidden; transition: all 0.3s ease;
  animation: slideUp 0.5s ease both;
}
@keyframes slideUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
.decision-card:hover {
  box-shadow: 0 8px 24px rgba(0,0,0,0.08); transform: translateY(-2px);
}
.decision-card.priority-high { border-left: 4px solid #f56c6c; }
.decision-card.priority-medium { border-left: 4px solid #e6a23c; }
.decision-card.priority-low { border-left: 4px solid #67c23a; }

.card-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  padding: 18px 20px 12px; background: #fafbfc; border-bottom: 1px solid #f0f0f0;
}
.decision-conclusion { display: flex; align-items: flex-start; gap: 10px; flex: 1; }
.conclusion-icon {
  flex-shrink: 0; margin-top: 2px;
}
.conclusion-icon.pulse { animation: pulse-glow 2s ease infinite; }
@keyframes pulse-glow {
  0%, 100% { filter: drop-shadow(0 0 4px rgba(245,108,108,0.4)); }
  50% { filter: drop-shadow(0 0 12px rgba(245,108,108,0.8)); }
}
.conclusion-text {
  font-size: 15px; font-weight: 600; color: #1a1a2e; line-height: 1.5;
}
.card-meta { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }

.card-body { padding: 16px 20px; }
.reason-section { margin-bottom: 14px; }
.section-label {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 12px; color: #9ca3af; font-weight: 500; margin-bottom: 6px;
}
.reason-text {
  margin: 0; font-size: 13px; color: #4b5563; line-height: 1.7;
  padding: 10px 12px; background: #f9fafb; border-radius: 8px;
}

.risk-section {}
.risk-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;
}
.risk-score { font-weight: 700; font-size: 15px; }
.risk-score.risk-high { color: #f56c6c; }
.risk-score.risk-medium { color: #e6a23c; }
.risk-score.risk-low { color: #67c23a; }
.risk-bar-track {
  height: 6px; background: #f3f4f6; border-radius: 3px; overflow: hidden;
}
.risk-bar-fill { height: 100%; border-radius: 3px; transition: width 0.8s ease; }
.risk-hint { font-size: 11px; color: #9ca3af; margin-top: 4px; display: block; }

.card-footer {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 20px; background: #fafbfc; border-top: 1px solid #f0f0f0;
}
.action-hint { font-size: 12px; }
.action-label { color: #9ca3af; }
.action-value {
  color: #667eea; font-weight: 600;
}
.action-buttons { display: flex; gap: 6px; }

/* 确认对话框 */
.confirm-content {}
.confirm-header {
  display: flex; align-items: center; gap: 10px; margin-bottom: 14px;
  font-size: 16px; color: #1a1a2e;
}
.confirm-desc {
  background: #f8f9fa; padding: 14px 16px; border-radius: 8px;
  border-left: 4px solid #667eea; font-size: 13px; color: #4b5563;
  line-height: 1.7; margin-bottom: 16px;
}
</style>
