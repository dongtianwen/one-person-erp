import api from './index'

export const getReleases = (projectId) => api.get(`/projects/${projectId}/releases`).then(r => r.data)
export const createRelease = (projectId, data) => api.post(`/projects/${projectId}/releases`, data).then(r => r.data)
export const getReleaseDetail = (projectId, id) => api.get(`/projects/${projectId}/releases/${id}`).then(r => r.data)
export const patchRelease = (projectId, id, data) => api.patch(`/projects/${projectId}/releases/${id}`, data).then(r => r.data)
export const setReleaseOnline = (projectId, id) => api.post(`/projects/${projectId}/releases/${id}/set-online`).then(r => r.data)
