import api from './index'

export const login = (username, password) =>
  api.post('/auth/login', new URLSearchParams({ username, password }), {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  })

export const getMe = () => api.get('/auth/me')
export const logout = () => api.post('/auth/logout')
