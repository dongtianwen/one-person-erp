import api from './index'

export const getChangeOrders = (contractId) => api.get(`/contracts/${contractId}/change-orders`).then(r => r.data)
export const createChangeOrder = (contractId, data) => api.post(`/contracts/${contractId}/change-orders`, data).then(r => r.data)
export const getChangeOrderDetail = (contractId, id) => api.get(`/contracts/${contractId}/change-orders/${id}`).then(r => r.data)
export const patchChangeOrder = (contractId, id, data) => api.patch(`/contracts/${contractId}/change-orders/${id}`, data).then(r => r.data)
export const getProjectChangeOrders = (projectId) => api.get(`/projects/${projectId}/change-orders/summary`).then(r => r.data)
