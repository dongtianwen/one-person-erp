import api from './index'

export const getDeliverables = (projectId, params) => api.get(`/projects/${projectId}/deliverables`, { params }).then(r => r.data)
export const createDeliverable = (projectId, data) => api.post(`/projects/${projectId}/deliverables`, data).then(r => r.data)
export const getDeliverableDetail = (projectId, id) => api.get(`/projects/${projectId}/deliverables/${id}`).then(r => r.data)
