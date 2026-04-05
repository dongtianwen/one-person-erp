import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getMe } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)

  const login = (tokenData) => {
    localStorage.setItem('access_token', tokenData.access_token)
    localStorage.setItem('refresh_token', tokenData.refresh_token)
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    user.value = null
  }

  const fetchUser = async () => {
    try {
      const { data } = await getMe()
      user.value = data
    } catch {
      logout()
    }
  }

  const isAuthenticated = () => !!localStorage.getItem('access_token')

  return { user, login, logout, fetchUser, isAuthenticated }
})
