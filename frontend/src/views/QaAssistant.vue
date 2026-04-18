<template>
  <div class="qa-page">
    <div class="page-header">
      <h2>经营助手</h2>
      <PageHelpDrawer pageKey="qa_assistant" />
      <el-tag v-if="providerAvailable" type="success" size="small">{{ providerModel }}</el-tag>
      <el-tag v-else type="info" size="small">API 未配置</el-tag>
    </div>

    <template v-if="providerAvailable">
      <div class="chat-container">
        <div class="chat-messages" ref="messagesRef">
          <div v-if="messages.length === 0" class="empty-hint">
            <p>向经营助手提问，例如：</p>
            <ul>
              <li>最近三个月收入趋势如何？</li>
              <li>哪些项目还有待收款？</li>
              <li>当前有哪些逾期合同？</li>
            </ul>
          </div>
          <div v-for="(msg, idx) in messages" :key="idx" :class="['chat-bubble', msg.role]">
            <div class="bubble-content">{{ msg.content }}</div>
          </div>
          <div v-if="loading" class="chat-bubble assistant">
            <div class="bubble-content loading-dots">思考中...</div>
          </div>
        </div>

        <div class="chat-input">
          <el-input
            v-model="inputText"
            placeholder="输入经营相关问题..."
            :disabled="loading"
            @keyup.enter="handleSend"
            clearable
          />
          <el-button type="primary" @click="handleSend" :disabled="loading || !inputText.trim()">
            发送
          </el-button>
        </div>
      </div>
    </template>

    <template v-else>
      <el-card shadow="never" class="unavailable-card">
        <el-result icon="info" title="此功能需接入外部模型">
          <template #sub-title>
            <p>请在「<el-link type="primary" @click="$router.push('/agents/settings')">Agent 设置</el-link>」中配置 API Provider</p>
            <p style="font-size: 13px; color: #909399; margin-top: 8px;">
              需填写 LLM_API_BASE、LLM_API_KEY、LLM_API_MODEL，并将模式切换为「云端 API」
            </p>
          </template>
        </el-result>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { askQuestion, getProviderStatus } from '../api/qa'
import PageHelpDrawer from '../components/PageHelpDrawer.vue'

const messages = ref([])
const inputText = ref('')
const loading = ref(false)
const providerAvailable = ref(false)
const providerModel = ref('')
const messagesRef = ref(null)

const scrollToBottom = async () => {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

const handleSend = async () => {
  const question = inputText.value.trim()
  if (!question || loading.value) return

  messages.value.push({ role: 'user', content: question })
  inputText.value = ''
  loading.value = true
  await scrollToBottom()

  try {
    const history = messages.value.slice(0, -1)
    const { data } = await askQuestion(question, history)
    messages.value.push({ role: 'assistant', content: data.answer || '未获取到回答' })
  } catch (e) {
    ElMessage.error('请求失败，请重试')
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

onMounted(async () => {
  try {
    const { data } = await getProviderStatus()
    if (data && data.provider === 'api' && data.api_key && data.api_base) {
      providerAvailable.value = true
      providerModel.value = data.api_model || 'API Model'
    }
  } catch (e) {
    providerAvailable.value = false
  }
})
</script>

<style scoped>
.qa-page { padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; font-weight: 600; }

.chat-container { display: flex; flex-direction: column; height: calc(100vh - 180px); background: #f5f7fa; border-radius: 12px; overflow: hidden; }
.chat-messages { flex: 1; overflow-y: auto; padding: 20px; }
.empty-hint { text-align: center; color: #909399; padding: 60px 20px; }
.empty-hint ul { list-style: none; padding: 0; }
.empty-hint li { padding: 6px 0; cursor: pointer; }
.empty-hint li:hover { color: #409eff; }

.chat-bubble { max-width: 70%; margin-bottom: 16px; display: flex; }
.chat-bubble.user { margin-left: auto; }
.chat-bubble.assistant { margin-right: auto; }
.bubble-content { padding: 12px 16px; border-radius: 12px; line-height: 1.6; white-space: pre-wrap; font-size: 14px; }
.chat-bubble.user .bubble-content { background: #409eff; color: white; border-bottom-right-radius: 4px; }
.chat-bubble.assistant .bubble-content { background: white; color: #303133; border-bottom-left-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
.loading-dots { color: #909399; }

.chat-input { display: flex; gap: 12px; padding: 16px 20px; background: white; border-top: 1px solid #ebeef5; }
.chat-input .el-input { flex: 1; }

.unavailable-card { border-radius: 12px; }
</style>
