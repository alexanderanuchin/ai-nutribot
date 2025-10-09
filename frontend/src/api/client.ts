import axios, { AxiosHeaders, type InternalAxiosRequestConfig } from 'axios'
import { tokenStore } from '../utils/storage'
import { getInitData } from '../lib/telegram'

const baseURL = import.meta.env.VITE_API_BASE || '/api'
export const api = axios.create({ baseURL, timeout: 15000 })

function ensureHeaders(config: InternalAxiosRequestConfig): Record<string, string> {
  if (config.headers instanceof AxiosHeaders) {
    return config.headers.toJSON() as Record<string, string>
  }
  return { ...(config.headers as Record<string, string> | undefined) }
}

let isRefreshing = false
let queue: Array<() => void> = []

api.interceptors.request.use(cfg => {
  const headers = ensureHeaders(cfg)
  const access = tokenStore.access
  if (access) {
    headers.Authorization = `Bearer ${access}`
  }
  const initData = typeof window !== 'undefined' ? getInitData() : null
  if (initData) {
    headers['X-Telegram-Init-Data'] = initData
  }
  cfg.headers = headers
  return cfg
})

api.interceptors.response.use(
  r => r,
  async err => {
    const original = err.config
    if (err.response?.status === 401 && !original._retry) {
      if (isRefreshing) {
        await new Promise<void>(res => queue.push(res))
      } else {
        isRefreshing = true
        try {
          const refresh = tokenStore.refresh
          if (!refresh) throw new Error('No refresh')
          const resp = await axios.post(`${baseURL}/users/auth/refresh/`, { refresh })
          tokenStore.access = resp.data.access
        } catch {
          tokenStore.clear()
          return Promise.reject(err)
        } finally {
          isRefreshing = false
          queue.forEach(fn => fn()); queue = []
        }
      }
      original._retry = true
      original.headers = { ...(original.headers||{}), Authorization: `Bearer ${tokenStore.access}` }
      return api(original)
    }
    return Promise.reject(err)
  }
)

export default api
