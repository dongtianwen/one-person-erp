import api from './index'

export const getCustomerAssets = (customerId) => api.get(`/customers/${customerId}/assets`)
export const createCustomerAsset = (customerId, data) => api.post(`/customers/${customerId}/assets`, data)
export const updateCustomerAsset = (customerId, id, data) => api.put(`/customers/${customerId}/assets/${id}`, data)
export const deleteCustomerAsset = (customerId, id) => api.delete(`/customers/${customerId}/assets/${id}`)
