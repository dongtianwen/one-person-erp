import api from './index'

export const getReminders = (params) => api.get('/reminders', { params })
export const getUpcomingReminders = (params) => api.get('/reminders/upcoming', { params })
export const createReminder = (data) => api.post('/reminders', data)
export const updateReminder = (id, data) => api.put(`/reminders/${id}`, data)
export const completeReminder = (id) => api.put(`/reminders/${id}/complete`)
export const deleteReminder = (id) => api.delete(`/reminders/${id}`)
export const getReminderSettings = () => api.get('/reminders/settings')
export const updateReminderSetting = (id, data) => api.put(`/reminders/settings/${id}`, data)
