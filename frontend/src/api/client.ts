import axios, {
  AxiosError,
  AxiosHeaders,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'
import { getInitData } from '../lib/telegram'
import { tokenStore } from '../utils/storage'
import { debugLog, generateRequestId, maskToken, warnLog } from '../lib/logging'
import { sendApplicationLog } from '../lib/monitoring'

const baseURL = import.meta.env.VITE_API_BASE || '/api'
export const api = axios.create({ baseURL, timeout: 15000 })

type RefreshListener = (refreshing: boolean) => void

const refreshListeners = new Set<RefreshListener>()

function notifyRefreshing(state: boolean): void {
  refreshListeners.forEach(listener => {
    try {
      listener(state)
    } catch (error) {
      console.error('refresh listener error', error)
    }
  })
}

function ensureHeaders(config: InternalAxiosRequestConfig): Record<string, string> {
  if (config.headers instanceof AxiosHeaders) {
    return config.headers.toJSON() as Record<string, string>
  }
  return { ...(config.headers as Record<string, string> | undefined) }
}

function shouldAttemptRefresh(response: AxiosResponse | undefined): boolean {
  if (!response || response.status !== 401) {
    return false
  }
  const data = response.data
  const code = (data && (data.code || data?.detail?.code)) ?? null
  if (code === 'token_not_valid') return true
  const detail = data?.detail
  if (typeof detail === 'string' && detail.toLowerCase().includes('token_not_valid')) {
    return true
  }
  if (Array.isArray(data?.messages)) {
    return data.messages.some(
      (item: any) => item && typeof item.code === 'string' && item.code === 'token_not_valid'
    )
  }
  return false
}

async function performTokenRefresh(): Promise<string> {
  const refreshToken = tokenStore.refresh
  if (!refreshToken) {
    throw new Error('Refresh token is missing')
  }
  const initData = typeof window !== 'undefined' ? getInitData() : null
  const headers: Record<string, string> = {}
  if (initData) {
    headers['X-Telegram-Init-Data'] = initData
  }
  const rid = generateRequestId()
  headers['X-Request-Id'] = rid
  debugLog('auth/refresh', 'request', {
    rid,
    refresh: maskToken(refreshToken),
    hasInitData: Boolean(initData),
  })
  void sendApplicationLog({
    level: 'INFO',
    logger: 'webapp.auth.refresh',
    message: 'request',
    requestId: rid,
    extra: {
      hasInitData: Boolean(initData),
    },
  })
  const { data } = await axios.post(
    `${baseURL}/auth/webapp/refresh/`,
    { refresh: refreshToken },
    { headers }
  )
  const access = data?.access
  if (!access || typeof access !== 'string') {
    throw new Error('Failed to obtain access token from refresh response')
  }
  tokenStore.access = access
  if (typeof data?.refresh === 'string' && data.refresh) {
    tokenStore.refresh = data.refresh
  }
  if (typeof data?.exp === 'number') {
    tokenStore.accessExpiresAt = data.exp
  }
  debugLog('auth/refresh', 'success', {
    rid,
    exp: data?.exp,
    refresh: maskToken(data?.refresh || refreshToken),
  })
  void sendApplicationLog({
    level: 'INFO',
    logger: 'webapp.auth.refresh',
    message: 'success',
    requestId: rid,
    extra: {
      exp: data?.exp,
      hasRefresh: Boolean(data?.refresh || refreshToken),
    },
  })
  return access
}

let refreshPromise: Promise<string | null> | null = null

export function subscribeToTokenRefresh(listener: RefreshListener): () => void {
  refreshListeners.add(listener)
  return () => {
    refreshListeners.delete(listener)
  }
}

export function isRefreshingTokens(): boolean {
  return Boolean(refreshPromise)
}

export async function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    notifyRefreshing(true)
    refreshPromise = performTokenRefresh()
      .catch(error => {
        warnLog('auth/refresh', 'request failed', {
          error: error instanceof Error ? error.message : String(error),
        })
        void sendApplicationLog({
          level: 'WARNING',
          logger: 'webapp.auth.refresh',
          message: 'request failed',
          extra: {
            error: error instanceof Error ? error.message : String(error),
          },
        })
        tokenStore.clear()
        tokenStore.notifyRefreshFailed()
        throw error
      })
      .finally(() => {
        notifyRefreshing(false)
        refreshPromise = null
      })
  }
  return refreshPromise
}

api.interceptors.request.use(config => {
  const headers = ensureHeaders(config)
  const access = tokenStore.access
  if (access) {
    headers.Authorization = `Bearer ${access}`
  }
  const initData = typeof window !== 'undefined' ? getInitData() : null
  if (initData) {
    headers['X-Telegram-Init-Data'] = initData
  }
  const rid = headers['X-Request-Id'] || generateRequestId()
  headers['X-Request-Id'] = rid
  const exp = tokenStore.accessExpiresAt
  const expDelta = typeof exp === 'number' ? exp - Math.floor(Date.now() / 1000) : null
  debugLog('api/request', 'dispatch', {
    rid,
    method: (config.method || 'get').toUpperCase(),
    url: config.url,
    hasAuth: Boolean(access),
    hasInitData: Boolean(initData),
    accessExpDeltaSec: expDelta,
  })
  config.headers = headers
  return config
})

api.interceptors.response.use(
  response => response,
  async error => {
    const axiosError = error as AxiosError
    const originalRequest = axiosError.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined
    if (!originalRequest || originalRequest._retry) {
      return Promise.reject(error)
    }

    if (shouldAttemptRefresh(axiosError.response)) {
      originalRequest._retry = true
      try {
        debugLog('api/response', '401 encountered, attempting refresh', {
          rid: originalRequest.headers?.['X-Request-Id'],
          url: originalRequest.url,
        })
        const newAccess = await refreshAccessToken()
        if (!newAccess) {
          return Promise.reject(error)
        }
        const headers = ensureHeaders(originalRequest)
        headers.Authorization = `Bearer ${newAccess}`
        const initData = typeof window !== 'undefined' ? getInitData() : null
        if (initData) {
          headers['X-Telegram-Init-Data'] = initData
        }
        headers['X-Request-Id'] = headers['X-Request-Id'] || generateRequestId()
        debugLog('api/response', 'retrying after refresh', {
          rid: headers['X-Request-Id'],
          url: originalRequest.url,
        })
        originalRequest.headers = headers
        return api(originalRequest)
      } catch (refreshError) {
        warnLog('api/response', 'refresh failed', {
          rid: originalRequest.headers?.['X-Request-Id'],
          url: originalRequest.url,
          error: refreshError instanceof Error ? refreshError.message : String(refreshError),
        })
        void sendApplicationLog({
          level: 'WARNING',
          logger: 'webapp.api.response',
          message: 'refresh failed',
          requestId: originalRequest.headers?.['X-Request-Id'],
          extra: {
            url: originalRequest.url,
            error: refreshError instanceof Error ? refreshError.message : String(refreshError),
          },
        })
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

export default api
