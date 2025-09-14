import React, { useState } from 'react'
import { register, login, checkPhone } from '../api/auth'
import { useNavigate, Link } from 'react-router-dom'
import { formatPhoneInput } from '../utils/phone'

export default function Register(){
  const [phone, setPhone] = useState('')
  const [phoneAvailable, setPhoneAvailable] = useState<boolean | null>(null)
  const [password, setPassword] = useState('')
  const [password2, setPassword2] = useState('')
  const [showPassword2, setShowPassword2] = useState(false)
  const [passwordError, setPasswordError] = useState<string | null>(null)
  const [smsCode, setSmsCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const nav = useNavigate()


  function validatePassword(p: string): string | null{
    if(p.length < 8) return 'Пароль должен быть не меньше 8 символов'
    if(!/[A-Z]/.test(p)) return 'Пароль должен содержать заглавную букву'
    if(!/[a-z]/.test(p)) return 'Пароль должен содержать строчную букву'
    if(!/\d/.test(p)) return 'Пароль должен содержать цифру'
    if(!/[^\w\s]/.test(p)) return 'Пароль должен содержать спецсимвол'
    return null
  }

  async function onPhoneBlur(){
    if(!phone) return
    try{
      const { available } = await checkPhone(phone)
      setPhoneAvailable(available)
    }catch{
      setPhoneAvailable(null)
    }
  }


  async function onSubmit(e: React.FormEvent){
    e.preventDefault()
    const pwdErr = validatePassword(password)
    if(pwdErr){ setError(pwdErr); return }
    if(password !== password2){ setError('Пароли не совпадают'); return }
    if(phoneAvailable === false){ setError('Номер уже зарегистрирован'); return }
    if(!/^\d{4}$/.test(smsCode)){ setError('Код из SMS должен состоять из 4 цифр'); return }
    setError(null); setLoading(true)
    try{
      await register(phone, password, smsCode)
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
          onChange={e=>{setPhone(prev=>formatPhoneInput(e.target.value, prev)); setPhoneAvailable(null)}}
          onBlur={onPhoneBlur}
          placeholder="+7 (___) ___-__-__"
          autoFocus
        />
        {phoneAvailable === false && <div className="small" style={{color:'#ff8b8b'}}>Номер уже зарегистрирован</div>}
        {phoneAvailable === true && <div className="small" style={{color:'#42a742'}}>Номер свободен</div>}
        <label>Код из SMS</label>
        <input
          type="text"
          value={smsCode}
          onChange={e=>setSmsCode(e.target.value.replace(/\D/g, '').slice(0,4))}
          maxLength={4}
          placeholder="1234"
          style={{width:'33%', display:'block'}}
        />
        <div className="small" style={{color:'#0066c0', cursor:'pointer', width:'33%', textAlign:'right'}}>Получить код</div>
        <label>Придумайте пароль</label>
        <input
          type="password"
          value={password}
          onFocus={()=>setShowPassword2(true)}
          onChange={e=>{setPassword(e.target.value); setPasswordError(validatePassword(e.target.value))}}
        />
        {showPassword2 && (
          <>
            <label>Повторите пароль</label>
            <input type="password" value={password2} onChange={e=>setPassword2(e.target.value)} />
          </>
        )}
        {passwordError && <div className="small" style={{color:'#ff8b8b'}}>{passwordError}</div>}
        {showPassword2 && password && password2 && password !== password2 && (
          <div className="small" style={{color:'#ff8b8b'}}>Пароли не совпадают</div>
        )}
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