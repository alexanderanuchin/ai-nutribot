import React, { useState } from 'react'
import { resetPassword } from '../api/auth'
import { useSearchParams, useNavigate } from 'react-router-dom'
import Lottie from 'lottie-react'
import sendAnimation from '../assets/send-message.json'
import successAnimation from '../assets/animation.json'
import { useLegacyStyles } from '../hooks/useLegacyStyles'
import { Button } from '../components/ui'

export default function ResetPassword(){
  useLegacyStyles()
  const [params] = useSearchParams()
  const uid = params.get('uid') || ''
  const token = params.get('token') || ''
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [step, setStep] = useState<'send' | 'success' | undefined>(undefined)
  const nav = useNavigate()

  async function onSubmit(e: React.FormEvent){
    e.preventDefault()
    setError(null); setLoading(true)
    try{
      await resetPassword(uid, token, password)
      setStep('send')
    }catch(err: any){
      setError(err?.response?.data?.detail || 'Ошибка')
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
      <h2>Новый пароль</h2>
      <form onSubmit={onSubmit}>
        <label>Пароль</label>
        <input type="password" value={password} onChange={e=>setPassword(e.target.value)} autoFocus />
        {error && <div className="small" style={{color:'#ff8b8b'}}>{error}</div>}
        <div className="form-actions" style={{marginTop:10}}>
          <Button type="submit" loading={loading} disabled={loading} className="w-full justify-center">
            {loading ? 'Сохраняем…' : 'Сохранить'}
          </Button>
        </div>
      </form>
    </div>
  )
}