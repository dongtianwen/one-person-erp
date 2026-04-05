import api from './index'

export const getProjects = (params) => api.get('/projects', { params })
export const getProject = (id) => api.get(`/projects/${id}`)
export const createProject = (data) => api.post('/projects', data)
export const updateProject = (id, data) => api.put(`/projects/${id}`, data)
export const deleteProject = (id) => api.delete(`/projects/${id}`)
export const getTasks = (projectId) => api.get(`/projects/${projectId}/tasks`)
export const createTask = (projectId, data) => api.post(`/projects/${projectId}/tasks`, data)
export const updateTask = (taskId, data) => api.put(`/projects/tasks/${taskId}`, data)
export const getMilestones = (projectId) => api.get(`/projects/${projectId}/milestones`)
export const createMilestone = (projectId, data) => api.post(`/projects/${projectId}/milestones`, data)
export const updateMilestone = (milestoneId, data) => api.put(`/projects/milestones/${milestoneId}`, data)
