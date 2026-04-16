import api from './index'

const AGENT_RUN_TIMEOUT = 5 * 60 * 1000

export const askQuestion = (question, history = null) =>
  api.post('/qa/ask', { question, history }, { timeout: AGENT_RUN_TIMEOUT })

export const getProviderStatus = () => api.get('/agents/config')
