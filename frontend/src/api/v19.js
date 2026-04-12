// v1.9 风险控制与成本视图 API
import api from './index'

// ========== 三表一致性校验 ==========
export const getConsistencyCheck = () => api.get('/finance/consistency-check')
export const getSingleConsistencyCheck = (contractId) => api.get(`/finance/consistency-check/${contractId}`)
export const refreshConsistencyCheck = () => api.post('/finance/consistency-check/refresh')

// ========== 收款逾期预警 ==========
export const getOverdueWarnings = () => api.get('/finance/overdue-warnings')
export const getCustomerRisk = (customerId) => api.get(`/finance/overdue-warnings/${customerId}`)
export const refreshOverdueWarnings = () => api.post('/finance/overdue-warnings/refresh')

// ========== 固定成本 ==========
export const getFixedCosts = () => api.get('/fixed-costs')
export const getFixedCost = (costId) => api.get(`/fixed-costs/${costId}`)
export const createFixedCost = (data) => api.post('/fixed-costs', data)
export const updateFixedCost = (costId, data) => api.put(`/fixed-costs/${costId}`, data)
export const deleteFixedCost = (costId) => api.delete(`/fixed-costs/${costId}`)
export const getFixedCostSummary = (period) => api.get('/fixed-costs/summary', { params: { period } })

// ========== 项目粗利润 ==========
export const getProjectProfit = (projectId) => api.get(`/projects/${projectId}/profit`)
export const refreshProjectProfit = (projectId) => api.post(`/projects/${projectId}/profit/refresh`)
export const getProfitOverview = () => api.get('/finance/profit-overview')

// ========== 进项发票 ==========
export const getInputInvoices = () => api.get('/input-invoices')
export const getInputInvoice = (invoiceId) => api.get(`/input-invoices/${invoiceId}`)
export const createInputInvoice = (data) => api.post('/input-invoices', data)
export const updateInputInvoice = (invoiceId, data) => api.put(`/input-invoices/${invoiceId}`, data)
export const deleteInputInvoice = (invoiceId) => api.delete(`/input-invoices/${invoiceId}`)
export const getInputInvoiceSummary = (params) => api.get('/input-invoices/summary', { params })
