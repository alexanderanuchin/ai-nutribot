import React, { useCallback, useEffect, useMemo, useState } from 'react'
import api from '../api/client'
import MacroBar from '../ui/MacroBar'
import MenuCard from '../ui/MenuCard'
import type { MenuPlanResponse, PlanMeal, PlanStatus } from '../types'
import {
  fetchPlans,
  type MealUpdatePayload,
  searchMenuItems,
  updatePlanMeal,
  updatePlanStatus,
} from '../api/menuPlans'

interface MealUpdatingState {
  [mealId: number]: boolean
}


function useHistoryUpdater(setHistory: React.Dispatch<React.SetStateAction<MenuPlanResponse[]>>) {
  return useCallback(
    (updatedPlan: MenuPlanResponse) => {
      setHistory(prev => {
        const idx = prev.findIndex(entry => entry.plan_id === updatedPlan.plan_id)
        if (idx === -1) {
          return [updatedPlan, ...prev]
        }
        const next = [...prev]
        next[idx] = updatedPlan
        return next
      })
    },
    [setHistory],
  )
}

export default function Dashboard() {
  const [plan, setPlan] = useState<MenuPlanResponse | null>(null)
  const [history, setHistory] = useState<MenuPlanResponse[]>([])
  const [loading, setLoading] = useState(false)
  const [planLoading, setPlanLoading] = useState(false)
  const [planProcessing, setPlanProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [statusUpdating, setStatusUpdating] = useState<PlanStatus | null>(null)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [selectedDate, setSelectedDate] = useState<string>('')
  const [mealUpdating, setMealUpdating] = useState<MealUpdatingState>({})

  const applyHistoryUpdate = useHistoryUpdater(setHistory)

  useEffect(() => {
    void fetchHistory()
  }, [])

  useEffect(() => {
    if (!plan && history.length) {
      setPlan(history[0])
      setSelectedDate(history[0].date)
    }
  }, [history, plan])

  const formattedHistory = useMemo(() => {
    return history.map(entry => ({
      ...entry,
      displayDate: new Date(entry.date).toLocaleDateString('ru-RU'),
      createdDisplay: new Date(entry.created_at).toLocaleString('ru-RU'),
    }))
  }, [history])

  async function fetchHistory() {
    setHistoryLoading(true)
    setHistoryError(null)
    try {
      const data = await fetchPlans({ limit: 45 })
      setHistory(data)
    } catch (err: any) {
      setHistoryError(err?.response?.data?.detail || 'Не удалось загрузить историю планов')
    } finally {
      setHistoryLoading(false)
    }
  }

  async function handleDateChange(value: string) {
    setSelectedDate(value)
    if (!value) return

    setPlanLoading(true)
    setError(null)
    try {
      const plansForDate = await fetchPlans({ date: value, limit: 1 })
      if (plansForDate.length) {
        setPlan(plansForDate[0])
        applyHistoryUpdate(plansForDate[0])
      } else {
        setPlan(null)
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Не удалось загрузить план на выбранную дату')
    } finally {
      setPlanLoading(false)
    }
  }

  async function generate() {
    setLoading(true)
    setError(null)
    setPlanProcessing(true)
    try {
      const { data } = await api.post<MenuPlanResponse>('/nutrition/generate/', {})
      setPlan(data)
      setSelectedDate(data.date)
      applyHistoryUpdate(data)
      await fetchHistory()
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Ошибка генерации плана')
    }finally{
      setLoading(false)
      setPlanProcessing(false)
    }
  }

  async function changeStatus(nextStatus: PlanStatus) {
    if (!plan) return
    setStatusUpdating(nextStatus)
    setError(null)
    try {
      const updated = await updatePlanStatus(plan.plan_id, nextStatus)
      setPlan(updated)
      applyHistoryUpdate(updated)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Не удалось обновить статус плана')
    } finally {
      setStatusUpdating(null)
    }
  }

  async function handleMealUpdate(mealId: number, payload: MealUpdatePayload) {
    if (!plan) return
    setMealUpdating(prev => ({ ...prev, [mealId]: true }))
    try {
      const updated = await updatePlanMeal(plan.plan_id, mealId, payload)
      setPlan(updated)
      applyHistoryUpdate(updated)
    } catch (err: any) {
      const detail = err?.response?.data?.detail || 'Не удалось сохранить изменения'
      throw new Error(detail)
    } finally {
      setMealUpdating(prev => {
        const next = { ...prev }
        delete next[mealId]
        return next
      })
    }
  }

  function handleHistorySelect(entry: MenuPlanResponse) {
    setPlan(entry)
    setSelectedDate(entry.date)
  }

  const isProcessing = planProcessing || plan?.status === 'processing'


  return (
    <div className="row">
      <div className="col">
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Ваш план питания</h2>
          <p className="small">План составляется на основе анкеты, доступности блюд и таргетов по калориям/макро.</p>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end', marginTop: 8 }}>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <label className="small" htmlFor="plan-date">Дата плана</label>
              <input
                id="plan-date"
                type="date"
                value={selectedDate || ''}
                onChange={event => void handleDateChange(event.target.value)}
                max={new Date().toISOString().split('T')[0]}
              />
            </div>
            <div className="form-actions" style={{ marginTop: 0 }}>
              <button onClick={() => void generate()} disabled={loading}>
                {loading ? 'Считаю…' : 'Сгенерировать меню'}
              </button>
            </div>
          </div>
          {error && <div className="small" style={{ color: '#ff8b8b', marginTop: 8 }}>{error}</div>}
          {isProcessing && (
            <div className="small" style={{ marginTop: 12, color: '#f2b544' }}>
              План в обработке. Это займёт около минуты.
            </div>
          )}
          {plan && !planLoading && (
            <>
              <div className="hr" style={{ marginTop: 12 }}></div>
              <div className="small" style={{ marginBottom: 8 }}>
                Статус: <b>{plan.status_display || plan.status}</b>
                <br />
                Составлен: {new Date(plan.created_at).toLocaleString('ru-RU')}
              </div>
              <div className="form-actions" style={{ gap: 8, marginBottom: 8 }}>
                <button
                  onClick={() => void changeStatus('accepted')}
                  disabled={statusUpdating === 'accepted' || plan.status === 'accepted'}
                >
                  {statusUpdating === 'accepted' ? 'Сохраняю…' : 'Отметить как принят'}
                </button>
                <button
                  onClick={() => void changeStatus('rejected')}
                  disabled={statusUpdating === 'rejected' || plan.status === 'rejected'}
                  className="ghost"
                >
                  {statusUpdating === 'rejected' ? 'Сохраняю…' : 'Отклонить план'}
                </button>
              </div>
              <MacroBar targets={plan.targets} />
            </>
          )}
          {planLoading && <div className="small" style={{ marginTop: 12 }}>Загрузка плана…</div>}
          {!plan && !planLoading && (
            <div className="small" style={{ marginTop: 12 }}>На выбранную дату план не найден. Сгенерируйте новый или выберите другую дату.</div>
          )}
        </div>

        <div className="card" style={{ marginTop: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: 0 }}>История планов</h3>
            <button onClick={() => void fetchHistory()} disabled={historyLoading} className="ghost">
              {historyLoading ? 'Обновляю…' : 'Обновить'}
            </button>
          </div>
          {historyError && <div className="small" style={{ color: '#ff8b8b', marginTop: 8 }}>{historyError}</div>}
          {!historyLoading && !formattedHistory.length && <div className="small" style={{ marginTop: 8 }}>История пока пуста.</div>}
          {historyLoading && <div className="small" style={{ marginTop: 8 }}>Загрузка…</div>}
          {formattedHistory.map(entry => {
            const isCurrent = plan && plan.plan_id === entry.plan_id
            return (
              <div key={entry.plan_id} style={{ marginTop: 10, borderTop: '1px solid #2d2d2d22', paddingTop: 8, display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start' }}>
                <div>
                  <div className="small" style={{ fontWeight: 600 }}>
                    {entry.displayDate} {isCurrent ? '· текущий' : ''}
                  </div>
                  <div className="small">Статус: {entry.status_display || entry.status}</div>
                  <div className="small">Создан: {entry.createdDisplay}</div>
                </div>
                <div className="form-actions" style={{ marginTop: 0 }}>
                  <button className={isCurrent ? '' : 'ghost'} onClick={() => handleHistorySelect(entry)}>
                    {isCurrent ? 'Открыто' : 'Открыть'}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      </div>
      <div className="col" style={{ flex: '1 1 100%' }}>
        <div className="card">
          <h3 style={{marginTop:0}}>Позиции</h3>
          {!plan && <div className="small">Нажмите «Сгенерировать меню», чтобы увидеть предложения на день.</div>}
          {plan?.plan?.length
            ? plan.plan.map((meal: PlanMeal) => (
                <MenuCard
                  key={meal.id}
                  item={meal}
                  updating={!!mealUpdating[meal.id]}
                  onUpdate={payload => handleMealUpdate(meal.id, payload)}
                  onSearch={query => searchMenuItems(query)}
                />
              ))
            : null}
        </div>
      </div>
    </div>
  )
}
