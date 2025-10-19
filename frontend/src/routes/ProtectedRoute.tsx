import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function ProtectedRoute({ children }: { children: React.ReactNode }){
  const { ready, authenticated } = useAuth()
  const location = useLocation()
  if (!ready) return null
  if (!authenticated) return <Navigate to="/login" replace state={{ from: location }} />
  return <>{children}</>
}
