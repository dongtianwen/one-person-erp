import api from './index'

export const getTemplates = (params) => api.get('/templates', { params })
export const getTemplate = (id) => api.get(`/templates/${id}`)
export const createTemplate = (data) => api.post('/templates', null, { params: data })
export const updateTemplate = (id, data) => api.put(`/templates/${id}`, null, { params: data })
export const deleteTemplate = (id) => api.delete(`/templates/${id}`)
export const setDefaultTemplate = (templateId, templateType) =>
  api.patch('/templates/set-default', null, { params: { template_id: templateId, template_type: templateType } })
export const getDefaultTemplate = (templateType) => api.get(`/templates/default/${templateType}`)
