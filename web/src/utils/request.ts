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

let isRefreshing = false
type QueueItem = {
  resolve: (token: string) => void
  reject: (error: unknown) => void
}
let failedQueue: QueueItem[] = []

function processQueue(error: unknown, token: string | null = null) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error)
    } else {
      resolve(token!)
    }
  })
  failedQueue = []
}

async function refreshAccessToken(): Promise<string> {
  const authStore = useAuthStore()
  if (!authStore.refreshToken) {
    throw new Error('No refresh token')
  }
  const response = await axios.post(
    `${request.defaults.baseURL}/auth/refresh/`,
    { refresh_token: authStore.refreshToken }
  )
  const { access_token, refresh_token } = response.data.data
  authStore.setToken(access_token, refresh_token)
  return access_token
}

function handle401WithRefresh(config: InternalAxiosRequestConfig): Promise<unknown> {
  if (config.url?.includes('/auth/refresh/')) {
    const authStore = useAuthStore()
    authStore.logout()
    window.location.href = '/login'
    return Promise.reject(new Error('login expired'))
  }

  if (!isRefreshing) {
    isRefreshing = true

    refreshAccessToken()
      .then((newToken) => {
        isRefreshing = false
        processQueue(null, newToken)
      })
      .catch((error) => {
        isRefreshing = false
        processQueue(error, null)
        const authStore = useAuthStore()
        authStore.logout()
        window.location.href = '/login'
      })
  }

  return new Promise<string>((resolve, reject) => {
    failedQueue.push({ resolve, reject })
  }).then((token) => {
    config.headers.Authorization = `Bearer ${token}`
    return request(config)
  })
}

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
      if (res.code === 401001) {
        return handle401WithRefresh(response.config)
      }

      if (res.code === 410001) {
        const err = new Error(res.message || '资源已下架或删除') as Error & { code?: number }
        err.code = res.code
        return Promise.reject(err) as any
      }

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
      return handle401WithRefresh(error.config!)
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
