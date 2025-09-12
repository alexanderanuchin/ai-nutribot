import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function ProtectedRoute({ children }: { children: React.ReactNode }){
  const { ready, authenticated } = useAuth()
  if (!ready) return null
  if (!authenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}
