import React, { useEffect, useState } from 'react'
import api from '../api/client'
import type { MenuPlanResponse, PlanMeal, PlanStatus } from '../types'
import MacroBar from '../ui/MacroBar'
import MenuCard from '../ui/MenuCard'

export default function Dashboard(){
  const [plan, setPlan] = useState<MenuPlanResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [history, setHistory] = useState<MenuPlanResponse[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [statusUpdating, setStatusUpdating] = useState<PlanStatus | null>(null)

  useEffect(() => {
    fetchHistory()
  }, [])

  async function fetchHistory(){
    setHistoryLoading(true); setHistoryError(null)
    try {
      const { data } = await api.get<MenuPlanResponse[]>('/nutrition/plans/')
      setHistory(data)
    } catch(err: any){
      setHistoryError(err?.response?.data?.detail || 'Не удалось загрузить историю планов')
    } finally {
      setHistoryLoading(false)
    }
  }

  async function generate(){
    setLoading(true); setError(null)
    try{
      const { data } = await api.post<MenuPlanResponse>('/nutrition/generate/', {})
      setPlan(data)
      await fetchHistory()
    }catch(err: any){
      setError(err?.response?.data?.detail || 'Ошибка генерации плана')
    }finally{
      setLoading(false)
    }
  }

  async function changeStatus(nextStatus: PlanStatus){
    if (!plan) return
    setStatusUpdating(nextStatus); setError(null)
    try{
      const { data } = await api.patch<MenuPlanResponse>(`/nutrition/plans/${plan.plan_id}/`, { status: nextStatus })
      setPlan(data)
      setHistory(prev => {
        const exists = prev.some(item => item.plan_id === data.plan_id)
        if (!exists) {
          return [data, ...prev]
        }
        return prev.map(item => item.plan_id === data.plan_id ? data : item)
      })
    }catch(err: any){
      setError(err?.response?.data?.detail || 'Не удалось обновить статус плана')
    }finally{
      setStatusUpdating(null)
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
              <div className="small" style={{marginBottom:8}}>
                Статус: <b>{plan.status_display || plan.status}</b>
                <br />
                Составлен: {new Date(plan.created_at).toLocaleString('ru-RU')}
              </div>
              <div className="form-actions" style={{gap:8, marginBottom:8}}>
                <button
                  onClick={() => changeStatus('accepted')}
                  disabled={statusUpdating === 'accepted' || plan.status === 'accepted'}
                >
                  {statusUpdating === 'accepted' ? 'Сохраняю…' : 'Отметить как принят'}
                </button>
                <button
                  onClick={() => changeStatus('rejected')}
                  disabled={statusUpdating === 'rejected' || plan.status === 'rejected'}
                  className="ghost"
                >
                  {statusUpdating === 'rejected' ? 'Сохраняю…' : 'Отклонить план'}
                </button>
              </div>
              <MacroBar targets={plan.targets} />
            </>
          )}
        </div>
        <div className="card" style={{marginTop:16}}>
          <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
            <h3 style={{margin:0}}>История планов</h3>
            <button onClick={fetchHistory} disabled={historyLoading} className="ghost">
              {historyLoading ? 'Обновляю…' : 'Обновить'}
            </button>
          </div>
          {historyError && <div className="small" style={{color:'#ff8b8b', marginTop:8}}>{historyError}</div>}
          {!historyLoading && !history.length && <div className="small" style={{marginTop:8}}>История пока пуста.</div>}
          {historyLoading && <div className="small" style={{marginTop:8}}>Загрузка…</div>}
          {history.map(entry => (
            <div key={entry.plan_id} style={{marginTop:10, borderTop:'1px solid #2d2d2d22', paddingTop:8}}>
              <div className="small" style={{fontWeight:600}}>
                {new Date(entry.date).toLocaleDateString('ru-RU')} {plan && plan.plan_id === entry.plan_id ? '· текущий' : ''}
              </div>
              <div className="small">Статус: {entry.status_display || entry.status}</div>
              <div className="small">Создан: {new Date(entry.created_at).toLocaleString('ru-RU')}</div>
            </div>
          ))}
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
