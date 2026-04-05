import api from './index'

export const getFileIndexes = (params) => api.get('/file-indexes', { params })
export const getFileIndex = (id) => api.get(`/file-indexes/${id}`)
export const createFileIndex = (data) => api.post('/file-indexes', data)
export const updateFileIndex = (id, data) => api.put(`/file-indexes/${id}`, data)
export const deleteFileIndex = (id) => api.delete(`/file-indexes/${id}`)
export const createFileVersion = (id, data) => api.post(`/file-indexes/${id}/version`, data)
export const getFileVersions = (id) => api.get(`/file-indexes/${id}/versions`)
