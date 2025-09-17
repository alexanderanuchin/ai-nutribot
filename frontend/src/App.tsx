import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Profile from './pages/Profile'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import ProtectedRoute from './routes/ProtectedRoute'
import Navbar from './components/Navbar'
import GridShimmerCanvas from './components/GridShimmerCanvas'

import { useTelegramAuth } from './hooks/useTelegramAuth'
export default function App(){
  useTelegramAuth();
  return (
    <>
      <Navbar />
      <div className="container">
        <GridShimmerCanvas />
        <div className="container__content">
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
      </div>
    </>
  )
}
