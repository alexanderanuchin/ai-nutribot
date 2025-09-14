import React, { useState } from 'react'
import { requestPasswordReset } from '../api/auth'

export default function ForgotPassword(){
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent){
    e.preventDefault()
    setLoading(true)
    try{
      await requestPasswordReset(email)
      setSent(true)
    }finally{
      setLoading(false)
    }
  }

  if (sent) return (
    <div className="card" style={{maxWidth:420, margin:'60px auto'}}>
      <h2>Проверьте почту</h2>
      <div className="small">Мы отправили ссылку для восстановления пароля, если такой аккаунт существует.</div>
    </div>
  )

  return (
    <div className="card" style={{maxWidth:420, margin:'60px auto'}}>
      <h2>Восстановление пароля</h2>
      <form onSubmit={onSubmit}>
        <label>Email</label>
        <input type="email" value={email} onChange={e=>setEmail(e.target.value)} autoFocus />
        <div className="form-actions" style={{marginTop:10}}>
          <button type="submit" disabled={loading}>{loading?'Отправляем…':'Отправить'}</button>
        </div>
      </form>
    </div>
  )
}