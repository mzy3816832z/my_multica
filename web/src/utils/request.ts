import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig, type AxiosResponse } from 'axios'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import type { ApiResponse } from '@/types'

const request: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器：注入 JWT Token
request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：统一解构 + 错误处理
request.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    const res = response.data
    if (res.code !== 0) {
      // 按业务码分发
      if (res.code === 401001) {
        showToast('登录已过期，请重新登录')
        const authStore = useAuthStore()
        authStore.logout()
        window.location.href = '/login'
        const err = new Error(res.message || '登录已过期，请重新登录') as Error & { code?: number }
        err.code = res.code
        return Promise.reject(err) as any
      }

      if (res.code === 410001) {
        // 已下架/已删除，不弹通用 toast，reject 时携带 code 供页面级处理
        const err = new Error(res.message || '资源已下架或删除') as Error & { code?: number }
        err.code = res.code
        return Promise.reject(err) as any
      }

      // 其余业务码统一 toast message 后 reject，Error 对象挂 code 字段
      showToast(res.message || '请求失败')
      const err = new Error(res.message || '请求失败') as Error & { code?: number }
      err.code = res.code
      return Promise.reject(err) as any
    }
    return res.data
  },
  (error: AxiosError<ApiResponse>) => {
    const uiStore = useUiStore()
    uiStore.hideLoading()

    const status = error.response?.status
    const message = error.response?.data?.message || error.message

    if (status === 401) {
      showToast('登录已过期，请重新登录')
      const authStore = useAuthStore()
      authStore.logout()
      window.location.href = '/login'
      return Promise.reject(error)
    }

    if (status === 403) {
      showToast('暂无权限访问')
      return Promise.reject(error)
    }

    if (status === 429) {
      showToast('操作过于频繁，请稍后再试')
      return Promise.reject(error)
    }

    showToast(message || '网络异常，请稍后重试')
    return Promise.reject(error)
  }
)

export default request
