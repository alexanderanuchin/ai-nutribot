import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

export type ThemeMode = 'dark' | 'light' | 'system'

type ResolvedTheme = Exclude<ThemeMode, 'system'>

type ThemeContextValue = {
  theme: ThemeMode
  resolvedTheme: ResolvedTheme
  setTheme: (mode: ThemeMode) => void
  toggleTheme: () => void
}

const STORAGE_KEY = 'nutribot_theme'
const DEFAULT_THEME: ThemeMode = 'system'

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined)

function isTheme(value: unknown): value is ThemeMode {
  return value === 'dark' || value === 'light' || value === 'system'
}

function resolveSystemTheme(): ResolvedTheme {
  if (typeof window === 'undefined') return 'dark'
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(theme: ResolvedTheme){
  if(typeof document === 'undefined') return
  const root = document.documentElement
  root.dataset.theme = theme
  root.style.colorScheme = theme
}

function getInitialTheme(): ThemeMode {
  if(typeof window === 'undefined'){
    return DEFAULT_THEME
  }
  const stored = window.localStorage.getItem(STORAGE_KEY)
  if(isTheme(stored)){
    return stored
  }
  return DEFAULT_THEME
}

export function ThemeProvider({ children }: { children: React.ReactNode }){
  const [theme, setTheme] = useState<ThemeMode>(() => getInitialTheme())
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() =>
    theme === 'system' ? resolveSystemTheme() : theme,
  )

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    if (theme === 'system') {
      const media = window.matchMedia('(prefers-color-scheme: dark)')
      const handleChange = () => {
        const next = media.matches ? 'dark' : 'light'
        setResolvedTheme(next)
        applyTheme(next)
      }

      handleChange()
      media.addEventListener('change', handleChange)
      window.localStorage.setItem(STORAGE_KEY, 'system')
      return () => media.removeEventListener('change', handleChange)
    }

    setResolvedTheme(theme)
    applyTheme(theme)
    window.localStorage.setItem(STORAGE_KEY, theme)
    return
  }, [theme])

  const toggleTheme = useCallback(() => {
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'))
  }, [])

  const value = useMemo<ThemeContextValue>(
    () => ({ theme, resolvedTheme, setTheme, toggleTheme }),
    [resolvedTheme, theme, toggleTheme],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme(){
  const context = useContext(ThemeContext)
  if(!context){
    throw new Error('useTheme must be used within ThemeProvider')
  }
  return context
}