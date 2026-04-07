import api from './index'

export const getMaintenancePeriods = (projectId, params) => api.get(`/projects/${projectId}/maintenance-periods`, { params }).then(r => r.data)
export const createMaintenancePeriod = (projectId, data) => api.post(`/projects/${projectId}/maintenance-periods`, data).then(r => r.data)
export const getMaintenanceDetail = (projectId, id) => api.get(`/projects/${projectId}/maintenance-periods/${id}`).then(r => r.data)
export const patchMaintenance = (projectId, id, data) => api.patch(`/projects/${projectId}/maintenance-periods/${id}`, data).then(r => r.data)
export const renewMaintenance = (projectId, id, data) => api.post(`/projects/${projectId}/maintenance-periods/${id}/renew`, data).then(r => r.data)
