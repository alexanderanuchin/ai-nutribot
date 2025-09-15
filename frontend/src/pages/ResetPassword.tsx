import React, { useState } from 'react'
import { resetPassword } from '../api/auth'
import { useSearchParams, useNavigate } from 'react-router-dom'
import Lottie from 'lottie-react'
import successAnimation from '../assets/animation.json'

export default function ResetPassword(){
  const [params] = useSearchParams()
  const uid = params.get('uid') || ''
  const token = params.get('token') || ''
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  const nav = useNavigate()

  async function onSubmit(e: React.FormEvent){
    e.preventDefault()
    setError(null); setLoading(true)
    try{
      await resetPassword(uid, token, password)
      setDone(true)
      setTimeout(() => nav('/login', { replace: true }), 3000)
    }catch(err: any){
      setError(err?.response?.data?.detail || 'Ошибка')
    }finally{
      setLoading(false)
    }
  }

  if (done) return (
    <div className="card" style={{maxWidth:420, margin:'60px auto', textAlign:'center'}}>
      <Lottie animationData={successAnimation} loop={false} />
    </div>
  )


  return (
    <div className="card" style={{maxWidth:420, margin:'60px auto'}}>
      <h2>Новый пароль</h2>
      <form onSubmit={onSubmit}>
        <label>Пароль</label>
        <input type="password" value={password} onChange={e=>setPassword(e.target.value)} autoFocus />
        {error && <div className="small" style={{color:'#ff8b8b'}}>{error}</div>}
        <div className="form-actions" style={{marginTop:10}}>
          <button type="submit" disabled={loading}>{loading?'Сохраняем…':'Сохранить'}</button>
        </div>
      </form>
    </div>
  )
}