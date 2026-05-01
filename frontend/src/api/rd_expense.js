import api from './index'

export const getRdExpenses = (params) => api.get('/rd-expenses', { params })
export const getRdExpense = (id) => api.get(`/rd-expenses/${id}`)
export const createRdExpense = (data) => api.post('/rd-expenses', data)
export const updateRdExpense = (id, data) => api.put(`/rd-expenses/${id}`, data)
export const deleteRdExpense = (id) => api.delete(`/rd-expenses/${id}`)
export const updateRdStatus = (id, data) => api.patch(`/rd-expenses/${id}/status`, data)
export const getRdSummary = (params) => api.get('/rd-expenses/summary', { params })
export const exportRdExpenses = (params) => api.get('/rd-expenses/export/file', {
  params,
  responseType: 'blob',
})
export const getRdMeta = () => api.get('/rd-expenses/meta/categories')
export const importFromFinance = (financeRecordId, data) => api.post(`/rd-expenses/import-from-finance/${financeRecordId}`, data)
export const unlinkFinanceRecord = (id) => api.patch(`/rd-expenses/${id}/unlink-finance`)
