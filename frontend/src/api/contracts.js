import api from './index'

export const getContracts = (params) => api.get('/contracts', { params })
export const getContract = (id) => api.get(`/contracts/${id}`)
export const createContract = (data) => api.post('/contracts', data)
export const updateContract = (id, data) => api.put(`/contracts/${id}`, data)
export const deleteContract = (id) => api.delete(`/contracts/${id}`)
export const generateContractContent = (id, force = false, content = null) => {
  const params = { force }
  if (content !== null) {
    return api.put(`/contracts/${id}/generated-content`, content, { params })
  }
  return api.post(`/contracts/${id}/generate`, null, { params })
}
export const previewContractContent = (id) => api.get(`/contracts/${id}/preview`)
export const convertQuotationToContract = (quotationId) => api.post(`/quotations/${quotationId}/generate-contract`)
