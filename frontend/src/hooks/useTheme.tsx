import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

export type ThemeMode = 'dark' | 'light'

type ThemeContextValue = {
  theme: ThemeMode
  setTheme: (mode: ThemeMode) => void
  toggleTheme: () => void
}

const STORAGE_KEY = 'nutribot_theme'
const DEFAULT_THEME: ThemeMode = 'dark'

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined)

function isTheme(value: unknown): value is ThemeMode {
  return value === 'dark' || value === 'light'
}

function applyTheme(theme: ThemeMode){
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
  const [theme, setTheme] = useState<ThemeMode>(() => {
    const initial = getInitialTheme()
    if(typeof document !== 'undefined'){
      applyTheme(initial)
    }
    return initial
  })

  useEffect(() => {
    applyTheme(theme)
    if(typeof window !== 'undefined'){
      window.localStorage.setItem(STORAGE_KEY, theme)
    }
  }, [theme])

  const toggleTheme = useCallback(() => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark')
  }, [])

  const value = useMemo<ThemeContextValue>(() => ({ theme, setTheme, toggleTheme }), [theme, toggleTheme])

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme(){
  const context = useContext(ThemeContext)
  if(!context){
    throw new Error('useTheme must be used within ThemeProvider')
  }
  return context
}