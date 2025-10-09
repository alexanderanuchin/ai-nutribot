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
import { bootstrapTelegramAuth, tg } from './lib/telegram'

void bootstrapTelegramAuth()
  .then(session => {
    if (!session) return
    const webApp = tg()
    if (!webApp) return
    const { accessToken, telegramUserId } = session
    if (!accessToken || !telegramUserId) return
    try {
      webApp.sendData(
        JSON.stringify({ type: 'auth', access_token: accessToken, user_id: telegramUserId })
      )
    } catch (error) {
      console.error('Не удалось отправить авторизационные данные в бота', error)
    }
  })
  .catch(error => {
    console.error('Не удалось валидировать initData в WebApp', error)
  })

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <BrowserRouter>
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
