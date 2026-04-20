import api from './index'

export const getToolEntries = (params) => api.get('/tool-entries', { params })
export const createToolEntry = (data) => api.post('/tool-entries', data)
export const updateToolEntryStatus = (id, data) => api.patch(`/tool-entries/${id}/status`, data)
export const deleteToolEntry = (id) => api.delete(`/tool-entries/${id}`)

export const getLeads = (params) => api.get('/leads', { params })
export const createLead = (data) => api.post('/leads', data)
export const getLead = (id) => api.get(`/leads/${id}`)
export const updateLead = (id, data) => api.put(`/leads/${id}`, data)
export const deleteLead = (id) => api.delete(`/leads/${id}`)
