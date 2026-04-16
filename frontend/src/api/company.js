import api from './index'

export const getCompanySettings = () => api.get('/settings/company')
export const updateCompanySettings = (data) => api.put('/settings/company', data)
