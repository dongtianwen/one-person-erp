// v1.8 财务对接 API
import api from './index'

// ========== 发票台账 ==========
export const getInvoices = (params) => api.get('/invoices', { params })
export const getInvoice = (invoiceId) => api.get(`/invoices/${invoiceId}`)
export const createInvoice = (data) => api.post('/invoices', data)
export const updateInvoice = (invoiceId, data) => api.put(`/invoices/${invoiceId}`, data)
export const patchInvoice = (invoiceId, data) => api.patch(`/invoices/${invoiceId}`, data)
export const deleteInvoice = (invoiceId) => api.delete(`/invoices/${invoiceId}`)
export const issueInvoice = (invoiceId) => api.post(`/invoices/${invoiceId}/issue`)
export const receiveInvoice = (invoiceId) => api.post(`/invoices/${invoiceId}/receive`)
export const verifyInvoice = (invoiceId) => api.post(`/invoices/${invoiceId}/verify`)
export const cancelInvoice = (invoiceId, reason) => api.post(`/invoices/${invoiceId}/cancel`, { reason })
export const getContractInvoices = (contractId) => api.get(`/contracts/${contractId}/invoices`)
export const getInvoiceSummary = (params) => api.get('/invoices/summary', { params })

// ========== 财务数据导出 ==========
export const createExportBatch = (data) => api.post('/finance/export', data)
export const getExportBatches = (params) => api.get('/finance/export/batches', { params })
export const getExportBatch = (batchId) => api.get(`/finance/export/batches/${batchId}`)
export const downloadExportFile = (batchId) => api.get(`/finance/export/download/${batchId}`, { responseType: 'blob' })

// ========== 会计期间对账 ==========
export const getReconciliationPeriods = () => api.get('/finance/reconciliation')
export const getReconciliationReport = (period) => api.get(`/finance/reconciliation/${period}`)
export const syncReconciliationStatus = (recordIds) => api.post('/finance/reconciliation/sync', { record_ids: recordIds })
