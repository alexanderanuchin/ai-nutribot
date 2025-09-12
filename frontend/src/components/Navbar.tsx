import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { logout } from '../api/auth'

export default function Navbar(){
  const { pathname } = useLocation()
  const isActive = (p: string) => pathname.startsWith(p)
  return (
    <div className="nav">
      <b>🍽️ NutriBot</b>
      <Link to="/dashboard" style={{background: isActive('/dashboard')?'#1a1e26':''}}>План</Link>
      <Link to="/profile" style={{background: isActive('/profile')?'#1a1e26':''}}>Профиль</Link>
      <div className="right">
        <button onClick={logout}>Выйти</button>
      </div>
    </div>
  )
}
