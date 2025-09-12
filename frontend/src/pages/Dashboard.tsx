import React, { useState } from 'react'
import api from '../api/client'
import type { MenuPlanResponse, PlanMeal } from '../types'
import MacroBar from '../ui/MacroBar'
import MenuCard from '../ui/MenuCard'

export default function Dashboard(){
  const [plan, setPlan] = useState<MenuPlanResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function generate(){
    setLoading(true); setError(null)
    try{
      const { data } = await api.post<MenuPlanResponse>('/nutrition/generate/', {})
      setPlan(data)
    }catch(err: any){
      setError(err?.response?.data?.detail || 'Ошибка генерации плана')
    }finally{
      setLoading(false)
    }
  }

  return (
    <div className="row">
      <div className="col">
        <div className="card">
          <h2 style={{marginTop:0}}>Ваш план питания</h2>
          <p className="small">План составляется на основе анкеты, доступности блюд и таргетов по калориям/макро.</p>
          <div className="form-actions" style={{marginTop:6}}>
            <button onClick={generate} disabled={loading}>{loading?'Считаю…':'Сгенерировать меню'}</button>
          </div>
          {error && <div className="small" style={{color:'#ff8b8b', marginTop:8}}>{error}</div>}
          {plan && (
            <>
              <div className="hr"></div>
              <MacroBar targets={plan.targets} />
            </>
          )}
        </div>
      </div>
      <div className="col" style={{flex:'1 1 100%'}}>
        <div className="card">
          <h3 style={{marginTop:0}}>Позиции</h3>
          {!plan && <div className="small">Нажмите «Сгенерировать меню», чтобы увидеть предложения на день.</div>}
          {plan?.plan?.length ? plan.plan.map((m: PlanMeal, idx: number) => (
            <MenuCard key={idx} item={m} />
          )) : null}
        </div>
      </div>
    </div>
  )
}
