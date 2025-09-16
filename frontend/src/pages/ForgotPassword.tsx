import React, { useState } from 'react'
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
  const nav = useNavigate()

  async function onSubmit(e: React.FormEvent){
    e.preventDefault()
    setLoading(true); setError(null)
    try{
      const { exists } = await checkEmail(email)
      if(!exists){
        setError('Пользователь с таким email не найден')
        return
      }
      await requestPasswordReset(email)
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
        <input type="email" value={email} onChange={e=>setEmail(e.target.value)} autoFocus />
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