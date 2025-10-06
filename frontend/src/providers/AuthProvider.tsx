import { createContext, useContext, useMemo, useCallback, useEffect } from 'react'
import type { ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchCurrentUser } from '../api/api'
import { AUTH_CHANGE_EVENT } from '../utils/storage'
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
}

export interface AuthContextValue {
  ready: boolean
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
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['current-user'],
    queryFn: fetchCurrentUser,
    staleTime: 1000 * 60 * 5,
    retry: false,
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
      queryClient.invalidateQueries({ queryKey: ['current-user'] })
    }

    window.addEventListener(AUTH_CHANGE_EVENT, handleAuthChange)
    return () => window.removeEventListener(AUTH_CHANGE_EVENT, handleAuthChange)
  }, [queryClient])

  const value = useMemo<AuthContextValue>(() => {
    const ready = !isLoading && !isFetching

    if (!data) {
      return { ready, authenticated: false, logout }
    }

    const role = (data.role as AuthRole) ?? 'legend'
    const avatarState = deriveAvatarState(data.profile?.avatar_preferences ?? null, data.avatarUrl ?? null)
    const avatarImageSrc = getAvatarImageSrc(avatarState)

    return {
      ready,
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
      },
      profile: data.profile,
      logout,
    }
  }, [data, isFetching, isLoading, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuthContext(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuthContext must be used within AuthProvider')
  }
  return context
}