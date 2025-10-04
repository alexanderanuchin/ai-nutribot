import { createContext, useContext, useMemo, useState, useCallback } from 'react'
import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchCurrentUser } from '../api/api'

export type AuthRole = 'legend' | 'member' | 'coach' | 'admin' | 'guest'

export interface AuthUser {
  id: number
  fullName: string
  email: string
  avatarUrl?: string
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
  const [authenticated, setAuthenticated] = useState(true)
  const { data, isLoading } = useQuery({
    queryKey: ['current-user'],
    queryFn: fetchCurrentUser,
    staleTime: 1000 * 60 * 5,
  })

  const logout = useCallback(() => {
    setAuthenticated(false)
    onLogout?.()
  }, [onLogout])

  const value = useMemo<AuthContextValue>(() => {
    if (!data) {
      return { ready: !isLoading, authenticated: false, logout }
    }

    const role = (data.role as AuthRole) ?? 'legend'

    return {
      ready: !isLoading,
      authenticated: authenticated && Boolean(data),
      user: {
        id: data.id,
        fullName: data.fullName,
        email: data.email,
        avatarUrl: data.avatarUrl,
        role,
        locale: data.locale,
        mode: data.mode,
        featureFlags: data.featureFlags,
      },
      profile: data.profile,
      logout,
    }
  }, [authenticated, data, isLoading, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuthContext(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuthContext must be used within AuthProvider')
  }
  return context
}