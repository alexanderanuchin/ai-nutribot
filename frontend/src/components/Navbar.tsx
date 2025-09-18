import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { logout } from '../api/auth'
import { useAuth } from '../hooks/useAuth'
import Logo from './Logo'
import ThemeToggle from './ThemeToggle'

export default function Navbar(){
  const { pathname } = useLocation()
  const { authenticated } = useAuth()
  const isActive = (p: string) => pathname.startsWith(p)
  const linkClass = (path: string) => `nav-link${isActive(path) ? ' nav-link--active' : ''}`
  return (
    <div className="nav">
      <Link to="/" className="nav-logo" aria-label="На главную CaloIQ">
        <Logo />
      </Link>
      {authenticated && (
        <nav className="nav-links" aria-label="Основная навигация">
          <Link to="/dashboard" className={linkClass('/dashboard')}>План</Link>
          <Link to="/profile" className={linkClass('/profile')}>Профиль</Link>
        </nav>
      )}
      <div className="right">
        <ThemeToggle />
        {authenticated ? (
          <button type="button" onClick={logout}>Выйти</button>
        ) : (
          <nav className="nav-links" aria-label="Навигация гостя">
            <Link to="/login" className={linkClass('/login')}>Войти</Link>
            <Link to="/register" className={linkClass('/register')}>Регистрация</Link>
          </nav>
        )}
      </div>
    </div>
  )
}
