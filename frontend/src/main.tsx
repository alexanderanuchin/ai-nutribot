import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import { ThemeProvider } from './hooks/useTheme'
import { AuthProvider } from './providers/AuthProvider'
import { CommandPaletteProvider } from './hooks/useCommandPalette'
import { logout as performLogout } from './api/auth'
import './styles/index.css'
import { DEFAULT_BASE_PATH, getAppBasePath } from './lib/basePath'
import { bootstrapTelegramAuth } from './lib/telegram'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

const appBasePath = getAppBasePath()
const routerBasename = appBasePath === DEFAULT_BASE_PATH ? undefined : appBasePath

;(async () => {
  try {
    await bootstrapTelegramAuth()
  } catch {}
})()

createRoot(document.getElementById('root')!).render(
  <BrowserRouter basename={routerBasename}>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider onLogout={performLogout}>
          <CommandPaletteProvider>
            <App />
          </CommandPaletteProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  </BrowserRouter>
)
