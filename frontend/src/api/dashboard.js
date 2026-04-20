import api from './index'

export const getDashboard = () => api.get('/dashboard')
export const getRevenueTrend = (months = 12) => api.get('/dashboard/revenue-trend', { params: { months } })
export const getCustomerFunnel = () => api.get('/dashboard/customer-funnel')
export const getProjectStatus = () => api.get('/dashboard/project-status')
export const getTodos = () => api.get('/dashboard/todos')
export const backupDatabase = (backupDir) => api.post('/dashboard/backup', null, { params: { backup_dir: backupDir } })
export const listBackups = () => api.get('/dashboard/backups')
export const verifyBackup = (filename) => api.post(`/dashboard/backups/${filename}/verify`)
export const getCashflowForecast = () => api.get('/cashflow/forecast')
export const getTaxSummary = (year, quarter) => api.get('/finances/tax-summary', { params: { year, quarter } })
export const getDashboardSummary = () => api.get('/dashboard/summary')
export const rebuildDashboardSummary = () => api.post('/dashboard/rebuild-summary')
