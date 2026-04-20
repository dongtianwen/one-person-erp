import api from './index'

export const getCompanySettings = () => api.get('/settings/company')
export const updateCompanySettings = (data) => api.put('/settings/company', data)
export const getTaxConfig = () => api.get('/settings/tax-config')
export const updateTaxConfig = (data) => api.put('/settings/tax-config', data)
