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

  const loginModes: Array<{ key: LoginMode; title: string; hint: string }> = [
    {
      key: 'phone',
      title: 'По номеру телефона',
      hint: 'Используйте привязанный мобильный',
    },
    {
      key: 'email',
      title: 'По электронной почте',
      hint: 'Войдите через корпоративную почту',
    },
  ]


  return (
    <div className="card auth-card">
      <h2>Вход</h2>
      <div className="segmented-control" role="tablist" aria-label="Способ входа">
        {loginModes.map(({ key, title, hint }) => {
          const active = mode === key
          return (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={active}
              className={`segmented-control__tab${active ? ' is-active' : ''}`}
              onClick={()=>setMode(key)}
            >
              <span className="segmented-control__title">{title}</span>
              <span className="segmented-control__hint">{hint}</span>
            </button>
          )
        })}
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
