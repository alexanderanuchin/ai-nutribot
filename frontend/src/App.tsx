import React, { useState } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Profile from './pages/Profile'
import Orders from './pages/Orders'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import ProtectedRoute from './routes/ProtectedRoute'

import { useTelegramAuth } from './hooks/useTelegramAuth'
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
  useTelegramAuth()
  const location = useLocation()
  const { ready, authenticated } = useAuth()
  const { theme, resolvedTheme } = useTheme()
  const { openPalette } = useCommandPalette()
  const [drawerOpen, setDrawerOpen] = useState(false)

  const isAuthRoute = AUTH_ROUTES.some(path => location.pathname.startsWith(path))
  const showAuthBackground = ready && !authenticated && isAuthRoute
  const showShell = ready && authenticated

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
                  <Route path="/" element={<Navigate to="/plan" replace />} />
                  <Route path="/plan" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
                  <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
                  <Route path="/billing" element={<ProtectedRoute><Orders /></ProtectedRoute>} />
                  <Route path="*" element={<div className="card">Страница не найдена</div>} />
                </Routes>
              </div>
            </main>
          </div>
          <MobileTabBar onOpenCommand={openPalette} />
          <NavDrawer open={drawerOpen} onOpenChange={setDrawerOpen} />
          <CommandPanel />
        </>
      )}

      {!showShell && (
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
          <CommandPanel />
        </>
      )}
    </div>
  )
}
