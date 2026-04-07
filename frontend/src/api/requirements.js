import api from './index'

export const getRequirements = (projectId) => api.get(`/projects/${projectId}/requirements`).then(r => r.data)
export const createRequirement = (projectId, data) => api.post(`/projects/${projectId}/requirements`, data).then(r => r.data)
export const getRequirementDetail = (projectId, id) => api.get(`/projects/${projectId}/requirements/${id}`).then(r => r.data)
export const updateRequirement = (projectId, id, data) => api.put(`/projects/${projectId}/requirements/${id}`, data).then(r => r.data)
export const patchRequirement = (projectId, id, data) => api.patch(`/projects/${projectId}/requirements/${id}`, data).then(r => r.data)
export const setCurrentRequirement = (projectId, id) => api.post(`/projects/${projectId}/requirements/${id}/set-current`).then(r => r.data)
export const createRequirementChange = (projectId, reqId, data) => api.post(`/projects/${projectId}/requirements/${reqId}/changes`, data).then(r => r.data)
