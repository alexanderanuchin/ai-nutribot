import {
  createContext,
  useContext,
  useMemo,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react'
import type { ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useLocation, useNavigate } from 'react-router-dom'
import { fetchCurrentUser } from '../api/api'
import { refreshAccessToken, subscribeToTokenRefresh, isRefreshingTokens } from '../api/client'
import { bootstrapTelegramAuth } from '../lib/telegram'
import { AUTH_CHANGE_EVENT, AUTH_REFRESH_FAILED_EVENT, tokenStore } from '../utils/storage'
import { deriveAvatarState, getAvatarImageSrc, type AvatarState } from '../utils/avatar'

export type AuthRole = 'legend' | 'member' | 'coach' | 'admin' | 'guest'

export interface AuthUser {
  id: number
  fullName: string
  email: string
  avatarUrl?: string
  avatarState: AvatarState
  avatarImageSrc: string | null
  role: AuthRole
  locale: string
  mode: string
  featureFlags: Record<string, boolean>
  isStaff: boolean
}

export interface AuthContextValue {
  ready: boolean
  bootstrapping: boolean
  authReady: boolean
  refreshing: boolean
  authenticated: boolean
  user?: AuthUser
  profile?: Awaited<ReturnType<typeof fetchCurrentUser>>['profile']
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export interface AuthProviderProps {
  children: ReactNode
  onLogout?: () => void
}

export function AuthProvider({ children, onLogout }: AuthProviderProps) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const location = useLocation()
  const [bootstrapping, setBootstrapping] = useState(true)
  const [authReady, setAuthReady] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    return Boolean(tokenStore.access)
  })
  const [refreshing, setRefreshing] = useState<boolean>(() =>
    typeof window !== 'undefined' ? isRefreshingTokens() : false
  )
  const [lastRefreshFailure, setLastRefreshFailure] = useState<number | null>(null)
  const refreshTimeoutRef = useRef<number | null>(null)

  const clearScheduledRefresh = useCallback(() => {
    if (typeof window === 'undefined') return
    if (refreshTimeoutRef.current !== null) {
      window.clearTimeout(refreshTimeoutRef.current)
      refreshTimeoutRef.current = null
    }
  }, [])

  const triggerSilentRefresh = useCallback(() => {
    if (typeof window === 'undefined') return
    if (!tokenStore.refresh || isRefreshingTokens()) {
      return
    }
    void refreshAccessToken().catch(error => {
      console.warn('Silent refresh failed', error)
    })
  }, [])

  const scheduleSilentRefresh = useCallback(() => {
    if (typeof window === 'undefined') return
    clearScheduledRefresh()
    const exp = tokenStore.accessExpiresAt
    if (!exp) return
    const nowSeconds = Math.floor(Date.now() / 1000)
    const refreshDelaySeconds = exp - nowSeconds - 60
    if (refreshDelaySeconds <= 0) {
      triggerSilentRefresh()
      return
    }
    refreshTimeoutRef.current = window.setTimeout(() => {
      refreshTimeoutRef.current = null
      triggerSilentRefresh()
    }, refreshDelaySeconds * 1000)
  }, [clearScheduledRefresh, triggerSilentRefresh])

  const updateAuthState = useCallback(() => {
    if (typeof window === 'undefined') return
    const hasAccess = Boolean(tokenStore.access)
    setAuthReady(hasAccess)
    if (!hasAccess) {
      clearScheduledRefresh()
      return
    }
    scheduleSilentRefresh()
  }, [clearScheduledRefresh, scheduleSilentRefresh])

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['current-user'],
    queryFn: fetchCurrentUser,
    staleTime: 1000 * 60 * 5,
    retry: false,
    enabled: authReady && !bootstrapping,
  })

  const logout = useCallback(() => {
    queryClient.setQueryData(['current-user'], undefined)
    void queryClient.cancelQueries({ queryKey: ['current-user'] })
    queryClient.removeQueries({ queryKey: ['current-user'], exact: true })
    onLogout?.()
  }, [onLogout, queryClient])

  useEffect(() => {
    if (typeof window === 'undefined') return

    const handleAuthChange = () => {
      updateAuthState()
      queryClient.invalidateQueries({ queryKey: ['current-user'] })
    }

    updateAuthState()

    window.addEventListener(AUTH_CHANGE_EVENT, handleAuthChange)
    return () => window.removeEventListener(AUTH_CHANGE_EVENT, handleAuthChange)
  }, [queryClient, updateAuthState])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const handleRefreshFailure = () => {
      setLastRefreshFailure(Date.now())
    }
    window.addEventListener(AUTH_REFRESH_FAILED_EVENT, handleRefreshFailure)
    return () => window.removeEventListener(AUTH_REFRESH_FAILED_EVENT, handleRefreshFailure)
  }, [])

  useEffect(() => {
    const unsubscribe = subscribeToTokenRefresh(state => {
      setRefreshing(state)
      if (!state) {
        scheduleSilentRefresh()
      }
    })
    return unsubscribe
  }, [scheduleSilentRefresh])

  useEffect(() => {
    let cancelled = false
    setBootstrapping(true)
    const run = async () => {
      try {
        await bootstrapTelegramAuth()
      } catch (error) {
        if (!cancelled) {
          console.error('Не удалось инициализировать авторизацию WebApp', error)
        }
      } finally {
        if (!cancelled) {
          updateAuthState()
          setBootstrapping(false)
        }
      }
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [updateAuthState])

  useEffect(() => {
    return () => {
      if (typeof window === 'undefined') return
      clearScheduledRefresh()
    }
  }, [clearScheduledRefresh])

  useEffect(() => {
    if (!lastRefreshFailure) return
    if (bootstrapping || isLoading || isFetching) return
    if (authReady) return
    if (location.pathname !== '/login') {
      navigate('/login', { replace: true })
    }
  }, [lastRefreshFailure, bootstrapping, isLoading, isFetching, authReady, navigate, location.pathname])

  const value = useMemo<AuthContextValue>(() => {
    const ready = authReady && !bootstrapping && !isLoading && !isFetching

    if (!data) {
      return {
        ready,
        bootstrapping,
        authReady,
        refreshing,
        authenticated: false,
        logout,
      }
    }

    const role = (data.role as AuthRole) ?? 'legend'
    const avatarState = deriveAvatarState(data.profile?.avatar_preferences ?? null, data.avatarUrl ?? null)
    const avatarImageSrc = getAvatarImageSrc(avatarState)

      return {
        ready,
        bootstrapping,
        authReady,
        refreshing,
        authenticated: true,
        user: {
          id: data.id,
          fullName: data.fullName,
          email: data.email,
          avatarUrl: data.avatarUrl,
          avatarState,
          avatarImageSrc,
          role,
          locale: data.locale,
          mode: data.mode,
          featureFlags: data.featureFlags,
          isStaff: data.isStaff,
        },
        profile: data.profile,
        logout,
      }
  }, [authReady, bootstrapping, data, isFetching, isLoading, logout, refreshing])

  return (
    <AuthContext.Provider value={value}>
      {bootstrapping ? null : children}
    </AuthContext.Provider>
  )
}

export function useAuthContext(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuthContext must be used within AuthProvider')
  }
  return context
}