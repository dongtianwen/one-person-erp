import api from './index'

export const getAcceptances = (projectId) => api.get(`/projects/${projectId}/acceptances`).then(r => r.data)
export const createAcceptance = (projectId, data) => api.post(`/projects/${projectId}/acceptances`, data).then(r => r.data)
export const getAcceptanceDetail = (projectId, id) => api.get(`/projects/${projectId}/acceptances/${id}`).then(r => r.data)
export const patchAcceptance = (projectId, id, data) => api.patch(`/projects/${projectId}/acceptances/${id}`, data).then(r => r.data)
export const appendAcceptanceNotes = (projectId, id, notes) => api.patch(`/projects/${projectId}/acceptances/${id}/append-notes`, { notes }).then(r => r.data)
