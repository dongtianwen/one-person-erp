import api from './index'

export const getQuotations = (params) => api.get('/quotations', { params })
export const getQuotation = (id) => api.get(`/quotations/${id}`)
export const createQuotation = (data) => api.post('/quotations', data)
export const updateQuotation = (id, data) => api.put(`/quotations/${id}`, data)
export const deleteQuotation = (id) => api.delete(`/quotations/${id}`)
export const convertToContract = (id) => api.post(`/quotations/${id}/convert-to-contract`)
export const sendQuotation = (id) => api.post(`/quotations/${id}/send`)
export const acceptQuotation = (id) => api.post(`/quotations/${id}/accept`)
export const rejectQuotation = (id) => api.post(`/quotations/${id}/reject`)
export const cancelQuotation = (id) => api.post(`/quotations/${id}/cancel`)
export const previewQuotation = (data) => api.post('/quotations/preview', data)
export const getQuotationItems = (id) => api.get(`/quotations/${id}/items`)
export const createQuotationItem = (id, data) => api.post(`/quotations/${id}/items`, data)
export const generateQuotationContent = (id, force = false, content = null) => {
  const params = { force }
  if (content !== null) {
    return api.put(`/quotations/${id}/generated-content`, content, { params })
  }
  return api.post(`/quotations/${id}/generate`, null, { params })
}
export const previewQuotationContent = (id) => api.get(`/quotations/${id}/preview`)
export const createQuotationFromProject = (projectId) => api.post(`/quotations/projects/${projectId}/generate-quotation`)
