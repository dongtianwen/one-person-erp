import api from './index'

export const getQuotations = (params) => api.get('/quotations', { params })
export const getQuotation = (id) => api.get(`/quotations/${id}`)
export const createQuotation = (data) => api.post('/quotations', data)
export const updateQuotation = (id, data) => api.put(`/quotations/${id}`, data)
export const deleteQuotation = (id) => api.delete(`/quotations/${id}`)
export const convertToContract = (id) => api.post(`/quotations/${id}/convert-to-contract`)
