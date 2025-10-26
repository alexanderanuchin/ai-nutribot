import React, { useState } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Feed from './pages/Feed'
import NewsArticle from './pages/NewsArticle'
import Profile from './pages/Profile'
import Orders from './pages/Orders'
import Search from './pages/Search'
import Compose from './pages/Compose'
import Notifications from './pages/Notifications'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import MarketLayout from './pages/market/MarketLayout'
import MarketHubPage from './pages/market/MarketHubPage'
import MarketRecipesPage from './pages/market/MarketRecipesPage'
import MarketProductsPage from './pages/market/MarketProductsPage'
import MarketStoresPage from './pages/market/MarketStoresPage'
import ProtectedRoute from './routes/ProtectedRoute'

import GridShimmerCanvas from './components/GridShimmerCanvas'
import GlowingLineCloudsCanvas from './components/GlowingLineCloudsCanvas'
import { useAuth } from './hooks/useAuth'
import { useTheme } from './hooks/useTheme'
import { useCommandPalette } from './hooks/useCommandPalette'
import AppNavbar from './components/nav/AppNavbar'
import SideRail from './components/nav/SideRail'
import MobileTabBar from './components/nav/MobileTabBar'
import NavDrawer from './components/nav/NavDrawer'
import CommandPanel from './components/nav/CommandPanel'

const AUTH_ROUTES = ['/login', '/register', '/forgot-password', '/reset-password']

export default function App(){
  const location = useLocation()
  const { ready, authenticated, authReady, bootstrapping } = useAuth()
  const { theme, resolvedTheme } = useTheme()
  const { openPalette } = useCommandPalette()
  const [drawerOpen, setDrawerOpen] = useState(false)

  const isAuthRoute = AUTH_ROUTES.some(path => location.pathname.startsWith(path))
  const hasTokens = authReady
  const showShell = ready && authenticated
  const shouldShowAuthRoutes = (!authenticated && !hasTokens) || ((!authenticated || !ready) && isAuthRoute)
  const showAuthBackground = shouldShowAuthRoutes && (isAuthRoute || !hasTokens)
  const showLoadingState = !showShell && !shouldShowAuthRoutes

  return (
    <div className="min-h-screen bg-[var(--bg)]">
      {showShell && (
        <>
          <AppNavbar onMenuClick={() => setDrawerOpen(true)} onOpenCommand={openPalette} />
          <div className="mx-auto flex w-full max-w-7xl">
            <SideRail onOpenCommand={openPalette} />
            <main className="flex min-h-screen flex-1 flex-col bg-transparent pb-24">
              <div className="relative z-10 px-4 pb-12 pt-6 sm:px-6 lg:px-10">
                <Routes>
                  <Route path="/" element={<Navigate to="/feed" replace />} />
                  <Route path="/feed" element={<ProtectedRoute><Feed /></ProtectedRoute>} />
                  <Route path="/feed/news/:id" element={<ProtectedRoute><NewsArticle /></ProtectedRoute>} />
                  <Route path="/plan" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
                  <Route path="/search" element={<ProtectedRoute><Search /></ProtectedRoute>} />
                  <Route path="/compose" element={<ProtectedRoute><Compose /></ProtectedRoute>} />
                  <Route
                    path="/market/*"
                    element={(
                      <ProtectedRoute>
                        <MarketLayout />
                      </ProtectedRoute>
                    )}
                  >
                    <Route index element={<MarketHubPage />} />
                    <Route path="recipes" element={<MarketRecipesPage />} />
                    <Route path="products" element={<MarketProductsPage />} />
                    <Route path="stores" element={<MarketStoresPage />} />
                  </Route>
                  <Route path="/notifications" element={<ProtectedRoute><Notifications /></ProtectedRoute>} />
                  <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
                  <Route path="/billing" element={<ProtectedRoute><Orders /></ProtectedRoute>} />
                  <Route path="*" element={<div className="card">Страница не найдена</div>} />
                </Routes>
              </div>
            </main>
          </div>
          <MobileTabBar onOpenCommand={openPalette} />
          <NavDrawer open={drawerOpen} onOpenChange={setDrawerOpen} />
        </>
      )}

      {!showShell && shouldShowAuthRoutes && (
        <>
          {showAuthBackground && (
            <div className="auth-background">
              {resolvedTheme === 'dark' || theme === 'dark' ? <GridShimmerCanvas /> : <GlowingLineCloudsCanvas />}
            </div>
          )}
          <div className="relative z-10 px-4 pb-12 pt-10 sm:px-6 lg:px-10">
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="*" element={<Navigate to="/login" replace />} />
            </Routes>
          </div>
        </>
      )}

      {!showShell && showLoadingState && (
        <>
          <div className="flex min-h-screen items-center justify-center px-4 pb-12 pt-10 sm:px-6 lg:px-10">
            <div className="card max-w-md text-center">
              <div className="text-lg font-semibold">Загружаем личный кабинет…</div>
              <div className="mt-2 text-sm text-muted-foreground">
                {bootstrapping
                  ? 'Подготавливаем окружение и проверяем авторизацию'
                  : 'Получаем актуальные данные профиля'}
              </div>
            </div>
          </div>
        </>
      )}
      <CommandPanel />
    </div>
  )
}
