import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { logout } from '../api/auth'
import { useAuth } from '../hooks/useAuth'
import Logo from './Logo'

export default function Navbar(){
  const { pathname } = useLocation()
  const { authenticated } = useAuth()
  const isActive = (p: string) => pathname.startsWith(p)
  return (
    <div className="nav">
      <Link to="/" className="nav-logo" aria-label="На главную CaloIQ">
        <Logo />
      </Link>
      {authenticated && (
        <>
          <Link to="/dashboard" style={{background: isActive('/dashboard')?'#1a1e26':''}}>План</Link>
          <Link to="/profile" style={{background: isActive('/profile')?'#1a1e26':''}}>Профиль</Link>
        </>
      )}
      <div className="right">
        {authenticated ? (
          <button onClick={logout}>Выйти</button>
        ) : (
          <>
            <Link to="/login" style={{background: isActive('/login')?'#1a1e26':''}}>Войти</Link>
            <Link to="/register" style={{background: isActive('/register')?'#1a1e26':''}}>Регистрация</Link>
          </>
        )}
      </div>
    </div>
  )
}
