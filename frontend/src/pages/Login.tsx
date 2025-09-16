import React, { useState, useEffect } from 'react'
import { login, loginWithEmail } from '../api/auth'
import { useNavigate, Link } from 'react-router-dom'
import { formatPhoneInput } from '../utils/phone'

type LoginMode = 'phone' | 'email'

export default function Login(){
  const [mode, setMode] = useState<LoginMode>('phone')
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const nav = useNavigate()

  useEffect(()=>{
    setError(null)
  }, [mode])

  async function onSubmit(e: React.FormEvent){
    e.preventDefault()
    setError(null); setLoading(true)
    try{
      if(mode === 'phone'){
        await login(phone, password)
      }else{
        await loginWithEmail(email, password)
      }
      nav('/dashboard', { replace: true })
    }catch(err: any){
      setError(err?.response?.data?.detail || 'Неверные учётные данные')
    }finally{
      setLoading(false)
    }
  }

  return (
    <div className="card" style={{maxWidth:420, margin:'60px auto'}}>
      <h2>Вход</h2>
      <div
        style={{
          display: 'flex',
          overflow: 'hidden',
          margin: '16px 0'
        }}
      >
        <button
          type="button"
          onClick={()=>setMode('phone')}
          style={{
            flex: 1,
            padding: '10px 12px',
            backgroundColor: mode === 'phone' ? '#e1f6eb' : '#f5f5f5',
            color: mode === 'phone' ? '#1f7a54' : '#777',
            border: 'none',
            fontWeight: mode === 'phone' ? 600 : 500,
            cursor: 'pointer',
            transition: 'background-color 0.2s ease, color 0.2s ease'
          }}
        >
          По номеру телефона
        </button>
        <button
          type="button"
          onClick={()=>setMode('email')}
          style={{
            flex: 1,
            padding: '10px 12px',
            backgroundColor: mode === 'email' ? '#e1f6eb' : '#f5f5f5',
            color: mode === 'email' ? '#1f7a54' : '#777',
            border: 'none',
            fontWeight: mode === 'email' ? 600 : 500,
            cursor: 'pointer',
            transition: 'background-color 0.2s ease, color 0.2s ease'
          }}
        >
          По электронной почте
        </button>
      </div>
      <form onSubmit={onSubmit}>
        {mode === 'phone' ? (
          <>
            <label htmlFor="login-phone">Телефон</label>
            <input
              id="login-phone"
              key="phone"
              type="tel"
              value={phone}
              onChange={e=>setPhone(prev=>formatPhoneInput(e.target.value, prev))}
              placeholder="+7 (___) ___-__-__"
              autoFocus
            />
          </>
        ) : (
          <>
            <label htmlFor="login-email">Электронная почта</label>
            <input
              id="login-email"
              key="email"
              type="email"
              value={email}
              onChange={e=>setEmail(e.target.value)}
              placeholder="you@example.com"
              autoFocus
            />
          </>
        )}
        <label>Пароль</label>
        <input type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="••••••••" />
        {error && <div className="small" style={{color:'#ff8b8b'}}>{error}</div>}
        <div className="form-actions" style={{marginTop:10}}>
          <button type="submit" disabled={loading}>{loading?'Входим…':'Войти'}</button>
        </div>
      </form>
      <div className="small" style={{marginTop:10}}><Link to="/forgot-password">Забыли пароль?</Link></div>
      <div className="hr"></div>
      <div className="small">Нет аккаунта? <Link to="/register">Зарегистрируйся</Link></div>
    </div>
  )
}
