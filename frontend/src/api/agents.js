import api from './index'

// Agent 运行（AI 增强模式可能需要数分钟，单独设置 5 分钟超时）
const AGENT_RUN_TIMEOUT = 5 * 60 * 1000 // 300 000 ms

export const runBusinessDecision = (useLlM = true, config = {}) =>
  api.post('/agents/business-decision/run', {}, { params: { use_llm: useLlM }, timeout: AGENT_RUN_TIMEOUT, ...config })
export const runProjectManagement = (projectId, useLlM = true, config = {}) => {
  const params = { use_llm: useLlM, ...(projectId ? { project_id: projectId } : {}) }
  return api.post('/agents/project-management/run', null, { params, timeout: AGENT_RUN_TIMEOUT, ...config })
}

export const runDeliveryQc = (packageId, useLlM = true, config = {}) =>
  api.post('/agents/delivery-qc/run', null, { params: { package_id: packageId, use_llm: useLlM }, timeout: AGENT_RUN_TIMEOUT, ...config })

// 运行记录
export const getAgentRuns = (params) => api.get('/agents/runs', { params })
export const getAgentRun = (id) => api.get(`/agents/runs/${id}`)

// 建议
export const getPendingSuggestions = (params) => api.get('/agents/suggestions/pending', { params })
export const confirmSuggestion = (id, data) => api.post(`/agents/suggestions/${id}/confirm`, data)

// 动作
export const getAgentActions = (params) => api.get('/agents/actions', { params })
export const getAgentAction = (id) => api.get(`/agents/actions/${id}`)

// 配置
export const getAgentConfig = () => api.get('/agents/config')
export const updateAgentConfig = (data) => api.post('/agents/config', data)
export const getOllamaModels = () => api.get('/agents/ollama-models')
