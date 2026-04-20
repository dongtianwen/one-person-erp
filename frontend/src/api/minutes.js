import api from './index'

export const getMinutes = (params) => api.get('/minutes', { params })
export const createMinutes = (data) => api.post('/minutes', data)
export const getMinutesDetail = (id) => api.get(`/minutes/${id}`)
export const updateMinutes = (id, data) => api.put(`/minutes/${id}`, data)
export const deleteMinutes = (id) => api.delete(`/minutes/${id}`)

export const getSnapshotHistory = (entityType, entityId) =>
  api.get(`/snapshots/${entityType}/${entityId}/history`)

export const getSnapshotDiff = (entityType, entityId, v1, v2) =>
  api.get(`/snapshots/${entityType}/${entityId}/diff`, { params: { v1, v2 } })
