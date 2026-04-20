import { ElMessage } from 'element-plus'
import { WARNING_MESSAGES } from '../constants/warnings'

const FALLBACK_MESSAGE = '操作完成，但存在异常，请查看日志'

export function useApiWarning() {
  function handleResponse(response) {
    if (response && response.warning_code) {
      const msg = WARNING_MESSAGES[response.warning_code] || FALLBACK_MESSAGE
      ElMessage.warning(msg)
    }
    return response
  }

  return { handleResponse }
}
