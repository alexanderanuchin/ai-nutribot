import React, { useRef, useState } from 'react'
import { requestPasswordReset, checkEmail } from '../api/auth'
import Lottie from 'lottie-react'
import sendAnimation from '../assets/send-message.json'
import successAnimation from '../assets/animation.json'
import { Link, useNavigate } from 'react-router-dom'

export default function ForgotPassword(){
  const [email, setEmail] = useState('')
  const [step, setStep] = useState<'send' | 'success' | undefined>(undefined)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [emailExists, setEmailExists] = useState<boolean | null>(null)
  const [checkingEmail, setCheckingEmail] = useState(false)
  const emailCheckId = useRef(0)
  const nav = useNavigate()
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

  async function verifyEmail(currentEmail: string){
    const trimmed = currentEmail.trim()
    if(!trimmed || !emailPattern.test(trimmed)){
      setEmailExists(null)
      return null
    }
    const requestId = ++emailCheckId.current
    setCheckingEmail(true)
    try{
      const { exists } = await checkEmail(trimmed)
      if(emailCheckId.current === requestId && email.trim() === trimmed){
        setEmailExists(exists)
      }
      return exists
    }catch{
      if(emailCheckId.current === requestId && email.trim() === trimmed){
        setEmailExists(null)
      }
      return null
    }finally{
      if(emailCheckId.current === requestId){
        setCheckingEmail(false)
      }
    }
  }

  async function onEmailBlur(){
    await verifyEmail(email)
  }

  async function onSubmit(e: React.FormEvent){
    e.preventDefault()
    setLoading(true); setError(null)
    try{
      const trimmed = email.trim()
      if(!emailPattern.test(trimmed)){
        setEmailExists(null)
        setError('Введите корректный email')
        return
      }
      const exists = emailExists === null ? await verifyEmail(trimmed) : emailExists
      if(!exists){
        return
      }
      await requestPasswordReset(trimmed)
      setStep('send')
    }finally{
      setLoading(false)
    }
  }

  if (step) return (
    <div className="card" style={{maxWidth:420, margin:'60px auto', textAlign:'center'}}>
      {step === 'send' ? (
        <Lottie
          animationData={sendAnimation}
          loop={false}
          onComplete={() => setStep('success')}
        />
      ) : (
        <Lottie
          animationData={successAnimation}
          loop={false}
          onComplete={() => nav('/login', { replace: true })}
        />
      )}
    </div>
  )

  return (
    <div className="card" style={{maxWidth:420, margin:'60px auto'}}>
      <h2>Восстановление пароля</h2>
      <form onSubmit={onSubmit}>
        <label>Email</label>
        <input
          type="email"
          value={email}
          onChange={e=>{ setEmail(e.target.value); setEmailExists(null); setError(null) }}
          onBlur={onEmailBlur}
          autoFocus
        />
        {checkingEmail && <div className="small" style={{color:'#0066c0'}}>Проверяем…</div>}
        {emailExists === true && (
          <div className="small" style={{color:'#42a742'}}>Аккаунт с таким email найден</div>
        )}
        {emailExists === false && (
          <div className="small" style={{color:'#ff8b8b'}}>Пользователь с таким email не найден</div>
        )}
        {error && <div className="small" style={{color:'#ff8b8b'}}>{error}</div>}
        <div className="form-actions" style={{marginTop:10}}>
          <button type="submit" disabled={loading}>{loading?'Отправляем…':'Отправить'}</button>
        </div>
      </form>
      <div className="hr" style={{marginTop:26}}></div>
      <div className="small" style={{marginTop:26, display:'flex', justifyContent:'space-between', gap:12, flexWrap:'wrap'}}>
        <span>
          Есть аккаунт? <Link to="/login">Войти</Link>
        </span>
        <span>
          Нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
        </span>
      </div>
    </div>
  )
}