import React, { useState } from 'react'
import { login } from '../api/auth'
import { useNavigate, Link } from 'react-router-dom'
import { formatPhoneInput } from '../utils/phone'

export default function Login(){
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const nav = useNavigate()

  async function onSubmit(e: React.FormEvent){
    e.preventDefault()
    setError(null); setLoading(true)
    try{
      await login(phone, password)
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
      <form onSubmit={onSubmit}>
        <label>Телефон</label>
        <input
          type="tel"
          value={phone}
          onChange={e=>setPhone(formatPhoneInput(e.target.value))}
          placeholder="+7 (___) ___-__-__"
          autoFocus
        />
        <label>Пароль</label>
        <input type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="••••••••" />
        {error && <div className="small" style={{color:'#ff8b8b'}}>{error}</div>}
        <div className="form-actions" style={{marginTop:10}}>
          <button type="submit" disabled={loading}>{loading?'Входим…':'Войти'}</button>
        </div>
      </form>
      <div className="hr"></div>
      <div className="small">Нет аккаунта? <Link to="/register">Зарегистрируйся</Link></div>
    </div>
  )
}
