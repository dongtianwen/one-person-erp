// v1.7 项目执行控制 API
import api from './index'

// ========== 项目级变更单 ==========
export const getProjectChangeOrders = (projectId) => api.get(`/projects/${projectId}/change-orders`)
export const getChangeOrder = (coId) => api.get(`/change-orders/${coId}`)
export const createProjectChangeOrder = (projectId, data) => api.post(`/projects/${projectId}/change-orders`, data)
export const confirmChangeOrder = (coId) => api.patch(`/change-orders/${coId}/confirm`)
export const rejectChangeOrder = (coId, reason) => api.patch(`/change-orders/${coId}/reject`, { rejection_reason: reason })
export const cancelChangeOrder = (coId) => api.patch(`/change-orders/${coId}/cancel`)

// ========== 里程碑收款 ==========
export const markMilestoneInvoiced = (milestoneId) => api.patch(`/milestones/${milestoneId}/payment-invoiced`)
export const markMilestonePaymentReceived = (milestoneId) => api.patch(`/milestones/${milestoneId}/payment-received`)
export const getProjectPaymentSummary = (projectId) => api.get(`/projects/${projectId}/payment-summary`)

// ========== 项目关闭 ==========
export const checkProjectCloseConditions = (projectId) => api.get(`/projects/${projectId}/close-check`)
export const closeProject = (projectId) => api.get(`/projects/${projectId}/close`)

// ========== 工时记录 ==========
export const createWorkHourLog = (projectId, data) => api.post(`/projects/${projectId}/work-hours`, data)
export const getWorkHours = (projectId) => api.get(`/projects/${projectId}/work-hours`)
export const getWorkHoursSummary = (projectId) => api.get(`/projects/${projectId}/work-hours/summary`)
export const updateEstimatedHours = (projectId, estimatedHours) => api.patch(`/projects/${projectId}/estimated-hours`, { estimated_hours })

// ========== 需求冻结状态 ==========
export const isProjectRequirementsFrozen = (projectId) => api.get(`/projects/${projectId}/requirements/frozen`)
