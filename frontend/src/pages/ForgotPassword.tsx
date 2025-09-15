import React, { useState } from 'react'
import { requestPasswordReset, checkEmail } from '../api/auth'
import Lottie from 'lottie-react'
import sendAnimation from '../assets/send-message.json'
import { useNavigate } from 'react-router-dom'

export default function ForgotPassword(){
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
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
      setSent(true)
      setTimeout(() => nav('/login', { replace: true }), 3000)
    }finally{
      setLoading(false)
    }
  }

  if (sent) return (
      <div className="card" style={{maxWidth:420, margin:'60px auto', textAlign:'center'}}>
      <Lottie animationData={sendAnimation} loop={false} />
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
    </div>
  )
}