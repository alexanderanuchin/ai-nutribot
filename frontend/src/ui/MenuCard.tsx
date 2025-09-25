import React, { useEffect, useMemo, useState } from 'react'
import type { MealUpdatePayload, MenuItemSearchResult } from '../api/menuPlans'
import type { PlanMeal } from '../types'

const TIME_OPTIONS: Array<{ value: string; label: string }> = [
  { value: 'breakfast', label: 'Завтрак' },
  { value: 'brunch', label: 'Поздний завтрак' },
  { value: 'lunch', label: 'Обед' },
  { value: 'snack', label: 'Перекус' },
  { value: 'dinner', label: 'Ужин' },
  { value: 'supper', label: 'Поздний ужин' },
  { value: 'any', label: 'Без привязки' },
]

interface MenuCardProps {
  item: PlanMeal
  updating?: boolean
  onUpdate: (payload: MealUpdatePayload) => Promise<void>
  onSearch: (query: string) => Promise<MenuItemSearchResult[]>
}

interface FeedbackState {
  status: 'success' | 'error'
  message: string
}

export default function MenuCard({ item, updating = false, onUpdate, onSearch }: MenuCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [qtyInput, setQtyInput] = useState(item.qty.toString())
  const [noteInput, setNoteInput] = useState(item.user_note || '')
  const [timeValue, setTimeValue] = useState(item.time_hint || 'any')
  const [searchQuery, setSearchQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [results, setResults] = useState<MenuItemSearchResult[]>([])
  const [feedback, setFeedback] = useState<FeedbackState | null>(null)

  useEffect(() => {
    setQtyInput(item.qty.toString())
    setNoteInput(item.user_note || '')
    setTimeValue(item.time_hint || 'any')
  }, [item])

  useEffect(() => {
    if (!feedback) return
    const timer = setTimeout(() => setFeedback(null), 3000)
    return () => clearTimeout(timer)
  }, [feedback])

  const nutrients = item.nutrients
  const timeOptions = useMemo(() => {
    if (!timeValue) return TIME_OPTIONS
    if (TIME_OPTIONS.some(option => option.value === timeValue)) return TIME_OPTIONS
    return [{ value: timeValue, label: timeValue }, ...TIME_OPTIONS]
  }, [timeValue])

  async function handleUpdate(payload: MealUpdatePayload, successMessage = 'Сохранено') {
    try {
      await onUpdate(payload)
      setFeedback({ status: 'success', message: successMessage })
    } catch (err: any) {
      const detail = err?.message || 'Не удалось сохранить изменения'
      setFeedback({ status: 'error', message: detail })
      throw err
    }
  }

  async function handleTimeChange(next: string) {
    setTimeValue(next)
    if (next === item.time_hint) return
    await handleUpdate({ time_hint: next })
  }

  async function handleQtyBlur() {
    const parsed = parseFloat(qtyInput.replace(',', '.'))
    if (Number.isNaN(parsed) || parsed <= 0) {
      setFeedback({ status: 'error', message: 'Количество должно быть больше нуля' })
      setQtyInput(item.qty.toString())
      return
    }
    if (Math.abs(parsed - item.qty) < 1e-3) return
    await handleUpdate({ qty: parsed }, 'Порция обновлена')
  }

  async function handleNoteSave() {
    if ((item.user_note || '') === noteInput.trim()) {
      setFeedback({ status: 'success', message: 'Без изменений' })
      return
    }
    await handleUpdate({ user_note: noteInput.trim() || null }, 'Заметка сохранена')
  }

  async function executeSearch() {
    const query = searchQuery.trim()
    if (query.length < 2) {
      setFeedback({ status: 'error', message: 'Введите минимум 2 символа' })
      return
    }
    setSearching(true)
    try {
      const found = await onSearch(query)
      setResults(found)
      if (!found.length) {
        setFeedback({ status: 'error', message: 'Ничего не найдено' })
      }
    } catch (err: any) {
      const detail = err?.message || 'Не удалось выполнить поиск'
      setFeedback({ status: 'error', message: detail })
    } finally {
      setSearching(false)
    }
  }

  async function handleReplacement(result: MenuItemSearchResult) {
    await handleUpdate({ item_id: result.id }, `Заменено на «${result.title}»`)
    setResults([])
    setSearchQuery('')
  }

  return (
    <div className="card" style={{ marginTop: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
        <div>
          <b>{item.title || `Позиция #${item.item_id}`}</b>
          <div className="small" style={{ opacity: 0.75 }}>
            Приём: {item.time_hint === 'any' ? 'не указан' : item.time_hint}
          </div>
        </div>
        <div className="badge">x{item.qty}</div>
      </div>

      {nutrients && (
        <div className="small" style={{ marginTop: 6, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <span>Ккал: {Math.round(nutrients.calories)}</span>
          <span>Б: {Math.round(nutrients.protein)}</span>
          <span>Ж: {Math.round(nutrients.fat)}</span>
          <span>У: {Math.round(nutrients.carbs)}</span>
        </div>
      )}

      {item.tags?.length ? (
        <div className="small" style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {item.tags.map(tag => (
            <span key={tag} className="badge" style={{ background: '#2d2d2d', color: '#fff' }}>
              {tag}
            </span>
          ))}
        </div>
      ) : null}

      <button
        className="ghost"
        style={{ marginTop: 10 }}
        onClick={() => setExpanded(prev => !prev)}
      >
        {expanded ? 'Скрыть настройки' : 'Настроить приём'}
      </button>

      {expanded && (
        <div style={{ marginTop: 12, borderTop: '1px solid #2d2d2d22', paddingTop: 12, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label className="small" htmlFor={`time-${item.id}`}>
              Время приёма
            </label>
            <select
              id={`time-${item.id}`}
              value={timeValue}
              onChange={event => void handleTimeChange(event.target.value)}
              disabled={updating}
            >
              {timeOptions.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label className="small" htmlFor={`qty-${item.id}`}>
              Количество порций
            </label>
            <input
              id={`qty-${item.id}`}
              type="number"
              min={0.1}
              step={0.1}
              value={qtyInput}
              onChange={event => setQtyInput(event.target.value)}
              onBlur={() => void handleQtyBlur()}
              disabled={updating}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label className="small" htmlFor={`note-${item.id}`}>
              Заметка к блюду
            </label>
            <textarea
              id={`note-${item.id}`}
              rows={2}
              value={noteInput}
              onChange={event => setNoteInput(event.target.value)}
              disabled={updating}
            />
            <div className="form-actions" style={{ justifyContent: 'flex-end' }}>
              <button onClick={() => void handleNoteSave()} disabled={updating}>
                Сохранить заметку
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label className="small">Заменить блюдо</label>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                type="text"
                placeholder="Введите название"
                value={searchQuery}
                onChange={event => setSearchQuery(event.target.value)}
                disabled={updating}
              />
              <button type="button" onClick={() => void executeSearch()} disabled={updating || searching}>
                {searching ? 'Ищу…' : 'Найти'}
              </button>
            </div>
            {results.length > 0 && (
              <div className="small" style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {results.map(result => (
                  <div key={result.id} style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center', border: '1px solid #2d2d2d33', borderRadius: 8, padding: '6px 10px' }}>
                    <div>
                      <div style={{ fontWeight: 600 }}>{result.title}</div>
                      {typeof result.price === 'number' && (
                        <div style={{ opacity: 0.7 }}>≈ {result.price} ₽</div>
                      )}
                    </div>
                    <button className="ghost" onClick={() => void handleReplacement(result)} disabled={updating}>
                      Выбрать
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {feedback && (
        <div
          className="small"
          style={{
            marginTop: 12,
            color: feedback.status === 'success' ? '#6ce4a1' : '#ff8b8b',
          }}
        >
          {feedback.message}
        </div>
      )}

      {updating && <div className="small" style={{ marginTop: 8 }}>Сохраняю изменения…</div>}
    </div>
  )
}