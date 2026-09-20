import axios, { AxiosError } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const TOKEN_KEY = 'mini_soc_token'
export const USER_KEY = 'mini_soc_user'

export const api = axios.create({
  baseURL: API_BASE_URL,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export function getApiErrorMessage(err: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as { detail?: unknown; message?: string } | undefined
    if (data?.detail) {
      if (typeof data.detail === 'string') return data.detail
      try {
        return JSON.stringify(data.detail)
      } catch {
        return fallback
      }
    }
    if (data?.message) return data.message
    if (err.code === 'ECONNABORTED') return 'Request timed out.'
    if (!err.response) return 'Cannot reach the backend server. Is it running?'
    return `${err.response.status} ${err.response.statusText}`
  }
  if (err instanceof Error) return err.message
  return fallback
}

export function getApiBaseUrl(): string {
  return API_BASE_URL
}
