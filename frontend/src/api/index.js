import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// v1.10 帮助系统——全局错误拦截
// 4xx 有 help → ErrorHelp 对话框
// 4xx 无 help → ElMessage.error(detail)
// 5xx → 通用提示
// 网络错误 → 网络提示
let _errorHelpInstance = null

export function setErrorHelpRef(ref) {
  _errorHelpInstance = ref
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const { data } = await axios.post('/api/v1/auth/refresh', { refresh_token: refreshToken })
          localStorage.setItem('access_token', data.access_token)
          localStorage.setItem('refresh_token', data.refresh_token)
          error.config.headers.Authorization = `Bearer ${data.access_token}`
          return api(error.config)
        } catch {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      } else {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }

    const status = error.response?.status
    const responseData = error.response?.data

    // HTTP 5xx：通用提示，不显示 help
    if (status >= 500) {
      ElMessage.error('服务器错误，请稍后重试')
      return Promise.reject(error)
    }

    // HTTP 4xx：检查是否有 help 字段
    if (status >= 400 && status < 500 && responseData?.help) {
      if (_errorHelpInstance) {
        _errorHelpInstance.show(responseData.help)
      } else {
        // fallback：降级为 ElMessage
        ElMessage.error(responseData.detail || '操作失败')
      }
      return Promise.reject(error)
    }

    // 网络错误
    if (!error.response) {
      ElMessage.error('网络连接失败，请检查网络')
      return Promise.reject(error)
    }

    // 其他 4xx 无 help：维持现有 ElMessage
    const msg = responseData?.detail || '请求失败'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

export default api
