import api from './index'

const REPORT_RUN_TIMEOUT = 5 * 60 * 1000

export const generateReport = (reportType, entityId, templateId = null) =>
  api.post(
    '/reports/generate',
    { report_type: reportType, entity_id: entityId, template_id: templateId },
    { timeout: REPORT_RUN_TIMEOUT }
  )

export const listReports = (params) => api.get('/reports', { params })

export const getReport = (id) => api.get(`/reports/${id}`)

export const deleteReport = (id) => api.delete(`/reports/${id}`)
