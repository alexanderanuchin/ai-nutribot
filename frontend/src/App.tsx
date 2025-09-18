import React from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Profile from './pages/Profile'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import ProtectedRoute from './routes/ProtectedRoute'
import Navbar from './components/Navbar'

import { useTelegramAuth } from './hooks/useTelegramAuth'
import GridShimmerCanvas from './components/GridShimmerCanvas'
import GlowingLineCloudsCanvas from './components/GlowingLineCloudsCanvas'
import { useAuth } from './hooks/useAuth'
import { useTheme } from './hooks/useTheme'

const AUTH_ROUTES = ['/login', '/register', '/forgot-password', '/reset-password']

export default function App(){
  useTelegramAuth();
  const location = useLocation()
  const { ready, authenticated } = useAuth()
  const { theme } = useTheme()
  const isAuthRoute = AUTH_ROUTES.some(path => location.pathname.startsWith(path))
  const showAuthBackground = ready && !authenticated && isAuthRoute
  return (
    <>
      <Navbar />
      {showAuthBackground && (
        <div className="auth-background">
          {theme === 'dark' ? <GridShimmerCanvas /> : <GlowingLineCloudsCanvas />}
        </div>
      )}
      <div className="container">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={
            <ProtectedRoute><Dashboard /></ProtectedRoute>
          } />
          <Route path="/profile" element={
            <ProtectedRoute><Profile /></ProtectedRoute>
          } />
          <Route path="*" element={<div className="card">Страница не найдена</div>} />
        </Routes>
      </div>
    </>
  )
}
