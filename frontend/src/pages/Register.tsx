import React, { useState } from 'react'
import { register, login, checkPhone, checkEmail } from '../api/auth'
import { useNavigate, Link } from 'react-router-dom'
import { formatPhoneInput } from '../utils/phone'

export default function Register(){
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [emailAvailable, setEmailAvailable] = useState<boolean | null>(null)
  const [phoneAvailable, setPhoneAvailable] = useState<boolean | null>(null)
  const [password, setPassword] = useState('')
  const [password2, setPassword2] = useState('')
  const [showPassword2, setShowPassword2] = useState(false)
  const [passwordError, setPasswordError] = useState<string | null>(null)
  const [smsCode, setSmsCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [privacyAccepted, setPrivacyAccepted] = useState(false)
  const [newsletterOptIn, setNewsletterOptIn] = useState(false)
  const nav = useNavigate()
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  const isFormValid =
    phone &&
    emailPattern.test(email) &&
    password &&
    password2 &&
    password === password2 &&
    !passwordError &&
    /^\d{4}$/.test(smsCode) &&
    phoneAvailable !== false &&
    emailAvailable !== false &&
    privacyAccepted


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

  async function onEmailBlur(){
    const trimmed = email.trim()
    if(!trimmed || !emailPattern.test(trimmed)){
      setEmailAvailable(null)
      return
    }
    try{
      const { exists } = await checkEmail(trimmed)
      setEmailAvailable(!exists)
    }catch{
      setEmailAvailable(null)
    }
  }


  async function onSubmit(e: React.FormEvent){
    e.preventDefault()
    const pwdErr = validatePassword(password)
    if(pwdErr){ setError(pwdErr); return }
    if(password !== password2){ setError('Пароли не совпадают'); return }
    const trimmedEmail = email.trim()
    if(!emailPattern.test(trimmedEmail)){ setError('Введите корректный email'); return }
    if(emailAvailable === false){ setError('Email уже зарегистрирован'); return }
    if(phoneAvailable === false){ setError('Номер уже зарегистрирован'); return }
    if(!/^\d{4}$/.test(smsCode)){ setError('Код из SMS должен состоять из 4 цифр'); return }
    if(!privacyAccepted){ setError('Необходимо согласиться с политикой конфиденциальности'); return }
    setError(null); setLoading(true)
    try{
      await register(phone, trimmedEmail, password, smsCode)
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
        <div
          className="small"
          style={{color:'#0066c0', cursor:'pointer', width:'33%', textAlign:'right'}}
        >
          Получить код
        </div>
        <label>Email</label>
        <input
          type="email"
          value={email}
          onChange={e=>{ setEmail(e.target.value); setEmailAvailable(null) }}
          onBlur={onEmailBlur}
          placeholder="you@example.com"
        />
        {email && !emailPattern.test(email) && (
          <div className="small" style={{color:'#ff8b8b'}}>Введите корректный email</div>
        )}
        {email && emailPattern.test(email) && emailAvailable === true && (
          <div className="small" style={{color:'#42a742'}}>Email свободен</div>
        )}
        {emailAvailable === false && (
          <div className="small" style={{color:'#ff8b8b'}}>Email уже зарегистрирован</div>
        )}
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
        <div className="consent-block">
          <label className="consent-option">
            <input
              type="checkbox"
              checked={privacyAccepted}
              onChange={e=>{ setPrivacyAccepted(e.target.checked); if(e.target.checked) setError(null) }}
            />
            <span>
              Я принимаю&nbsp;
              <a href="/privacy" target="_blank" rel="noopener noreferrer">
                политику конфиденциальности
              </a>
              &nbsp;и условия обработки данных
            </span>
          </label>
          <label className="consent-option">
            <input
              type="checkbox"
              checked={newsletterOptIn}
              onChange={e=>setNewsletterOptIn(e.target.checked)}
            />
            <span>
              Получать новости и продуктовые обновления на email
            </span>
          </label>
        </div>
        {error && <div className="small" style={{color:'#ff8b8b'}}>{error}</div>}
        <div className="form-actions" style={{marginTop:10}}>
          <button type="submit" disabled={loading || !isFormValid}>{loading?'Регистрируем…':'Зарегистрироваться'}</button>
        </div>
      </form>
      <div className="hr"></div>
      <div className="small">Уже есть аккаунт? <Link to="/login">Войти</Link></div>
    </div>
  )
}