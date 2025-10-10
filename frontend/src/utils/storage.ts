const ACCESS_KEY = 'nutribot_access'
const ACCESS_EXP_KEY = 'nutribot_access_exp'
const REFRESH_KEY = 'nutribot_refresh'

export const AUTH_CHANGE_EVENT = 'nutribot:auth-change'
export const AUTH_REFRESH_FAILED_EVENT = 'nutribot:auth-refresh-failed'

function emit(event: string): void {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new Event(event))
}

function decodeJwtExp(token: string | null): number | null {
  if (!token) return null
  const parts = token.split('.')
  if (parts.length < 2) return null
  try {
    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')))
    const exp = payload?.exp
    return typeof exp === 'number' ? exp : null
  } catch {
    return null
  }
}

function setAccessExp(exp: number | null): void {
  if (exp && Number.isFinite(exp)) {
    localStorage.setItem(ACCESS_EXP_KEY, String(exp))
  } else {
    localStorage.removeItem(ACCESS_EXP_KEY)
  }
  emit(AUTH_CHANGE_EVENT)
}

export const tokenStore = {
  get access(): string {
    return localStorage.getItem(ACCESS_KEY) || ''
  },
  set access(value: string) {
    if (value) {
      localStorage.setItem(ACCESS_KEY, value)
      const exp = decodeJwtExp(value)
      if (exp) {
        localStorage.setItem(ACCESS_EXP_KEY, String(exp))
      }
    } else {
      localStorage.removeItem(ACCESS_KEY)
      localStorage.removeItem(ACCESS_EXP_KEY)
    }
    emit(AUTH_CHANGE_EVENT)
  },
  get refresh(): string {
    return localStorage.getItem(REFRESH_KEY) || ''
  },
  set refresh(value: string) {
    if (value) {
      localStorage.setItem(REFRESH_KEY, value)
    } else {
      localStorage.removeItem(REFRESH_KEY)
    }
    emit(AUTH_CHANGE_EVENT)
  },
  get accessExpiresAt(): number | null {
    const raw = localStorage.getItem(ACCESS_EXP_KEY)
    if (!raw) return null
    const parsed = Number(raw)
    return Number.isFinite(parsed) ? parsed : null
  },
  set accessExpiresAt(exp: number | null) {
    setAccessExp(exp)
  },
  clear(): void {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(ACCESS_EXP_KEY)
    localStorage.removeItem(REFRESH_KEY)
    emit(AUTH_CHANGE_EVENT)
  },
  notifyRefreshFailed(): void {
    emit(AUTH_REFRESH_FAILED_EVENT)
  },
}
