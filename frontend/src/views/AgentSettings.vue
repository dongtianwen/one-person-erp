<template>
  <div class="agent-settings-page">
    <div class="page-header">
      <h2>AI Agent 核心配置</h2>
      <el-button type="primary" @click="saveConfig" :loading="savingConfig">保存全局设置</el-button>
    </div>

    <el-row :gutter="20">
      <el-col :span="14">
        <el-card shadow="never" class="config-card">
          <template #header>服务提供商 (LLM Provider)</template>
          
          <el-form :model="configForm" label-width="140px" label-position="left">
            <el-alert 
              title="配置说明：此处设置将存储在系统数据库中，优先级高于 .env 文件。保存后 Agent 运行将立即采用新配置。" 
              type="success" 
              show-icon 
              :closable="false" 
              style="margin-bottom: 24px;" 
            />

            <el-form-item label="当前模式">
              <el-radio-group v-model="configForm.provider">
                <el-radio-button value="none">关闭 AI</el-radio-button>
                <el-radio-button value="local">本地 Ollama</el-radio-button>
                <el-radio-button value="api">云端 API</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <el-divider />

            <!-- 本地模型配置 -->
            <template v-if="configForm.provider === 'local'">
              <el-form-item label="选择模型">
                <div style="display: flex; gap: 10px; width: 100%;">
                  <el-select 
                    v-model="configForm.local_model" 
                    placeholder="请选择本地已安装模型" 
                    style="flex: 1;"
                    filterable
                    allow-create
                    clearable
                    :loading="loadingModels"
                  >
                    <el-option v-for="m in modelList" :key="m" :label="m" :value="m" />
                  </el-select>
                  <el-button :icon="Refresh" circle @click="fetchModels" :loading="loadingModels" />
                </div>
                <p class="hint">如列表为空，请启动 Ollama 并拉取模型（例如：ollama pull gemma）</p>
              </el-form-item>
              <el-form-item label="Ollama 地址">
                <el-input v-model="configForm.local_base_url" placeholder="http://localhost:11434" />
              </el-form-item>
            </template>

            <!-- 云端模型配置 -->
            <template v-if="configForm.provider === 'api'">
              <el-form-item label="API 模型名称">
                <el-input v-model="configForm.api_model" placeholder="如: gpt-4o-mini" />
              </el-form-item>
              <el-form-item label="Base URL">
                <el-input v-model="configForm.api_base" placeholder="https://api.openai.com/v1" />
              </el-form-item>
              <el-form-item label="API Key">
                <el-input v-model="configForm.api_key" type="password" show-password placeholder="sk-..." />
              </el-form-item>
            </template>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card shadow="never">
          <template #header>自由问答</template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="当前 Provider">
              <el-tag :type="configForm.provider === 'api' ? 'success' : 'info'" size="small">
                {{ configForm.provider === 'api' ? '云端 API（可用）' : configForm.provider === 'local' ? '本地 Ollama（不支持问答）' : '未启用' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="问答入口">
              <el-button v-if="configForm.provider === 'api'" type="primary" size="small" @click="$router.push('/assistant/qa')">
                进入经营助手
              </el-button>
              <span v-else style="color: #909399; font-size: 13px;">
                需切换为「云端 API」模式并配置 API Key 后可用
              </span>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card shadow="never" style="margin-top: 16px;">
          <template #header>规则引擎逻辑（预设）</template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="逾期回款">由于支付期已过且未回款，自动标记为 anomaly</el-descriptions-item>
            <el-descriptions-item label="利润异常">毛利率较初始预算下降 > 30%</el-descriptions-item>
            <el-descriptions-item label="现金流">未来 4 周预测结余为负值</el-descriptions-item>
          </el-descriptions>
          <p style="margin-top: 16px; font-size: 13px; color: #909399;">* 规则逻辑目前为硬编码，未来版本将支持自定义规则表达式。</p>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getAgentConfig, updateAgentConfig, getOllamaModels } from '../api/agents'

const savingConfig = ref(false)
const loadingModels = ref(false)
const modelList = ref([])
const configForm = ref({
  provider: 'none',
  local_model: '',
  local_base_url: '',
  api_model: '',
  api_base: '',
  api_key: '',
})

const fetchConfig = async () => {
  try {
    const { data } = await getAgentConfig()
    if (data) {
      configForm.value = data
      if (configForm.value.provider === 'local') {
        fetchModels()
      }
    }
  } catch (e) {
    console.error('获取配置失败', e)
  }
}

const fetchModels = async () => {
  if (configForm.value.provider !== 'local') return
  loadingModels.value = true
  try {
    const { data } = await getOllamaModels()
    if (Array.isArray(data)) {
      modelList.value = data
    } else {
      modelList.value = []
    }
  } catch (e) {
    // 错误现在由全局 API 拦截器处理并弹出详细提示
    modelList.value = []
  } finally {
    loadingModels.value = false
  }
}

const saveConfig = async () => {
  savingConfig.value = true
  try {
    await updateAgentConfig(configForm.value)
    ElMessage.success('Agent 全局设置已保存')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    savingConfig.value = false
  }
}

watch(() => configForm.value.provider, (newP) => {
  if (newP === 'local' && modelList.value.length === 0) {
    fetchModels()
  }
})

onMounted(() => {
  fetchConfig()
})
</script>

<style scoped>
.agent-settings-page { padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-header h2 { margin: 0; font-weight: 600; }
.config-card { border-radius: 8px; }
.hint { font-size: 12px; color: #909399; margin-top: 4px; }
</style>
