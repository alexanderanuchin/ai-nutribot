import React, { useState } from 'react'
import { register, login } from '../api/auth'
import { useNavigate, Link } from 'react-router-dom'
import { formatPhoneInput } from '../utils/phone'

export default function Register(){
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const nav = useNavigate()

  async function onSubmit(e: React.FormEvent){
    e.preventDefault()
    setError(null); setLoading(true)
    try{
      await register(phone, password)
      await login(phone, password)
      nav('/dashboard', { replace: true })
    }catch(err: any){
      setError(err?.response?.data?.detail || 'Ошибка регистрации')
    }finally{
      setLoading(false)
    }
  }

  return (
    <div className="card" style={{maxWidth:420, margin:'60px auto'}}>
      <h2>Регистрация</h2>
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
        <input type="password" value={password} onChange={e=>setPassword(e.target.value)} />
        {error && <div className="small" style={{color:'#ff8b8b'}}>{error}</div>}
        <div className="form-actions" style={{marginTop:10}}>
          <button type="submit" disabled={loading}>{loading?'Регистрируем…':'Зарегистрироваться'}</button>
        </div>
      </form>
      <div className="hr"></div>
      <div className="small">Уже есть аккаунт? <Link to="/login">Войти</Link></div>
    </div>
  )
}