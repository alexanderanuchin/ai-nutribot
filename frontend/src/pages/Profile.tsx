import React, { useEffect, useMemo, useState } from 'react'
import api from '../api/client'
import { me } from '../api/auth'
import type { Profile as ProfileT, User } from '../types'

const emptyProfile: ProfileT = {
  sex: 'm',
  height_cm: 175,
  weight_kg: 70,
  activity_level: 'moderate',
  goal: 'recomp',
  allergies: [],
  exclusions: [],
  birth_date: null,
  body_fat_pct: null,
  daily_budget: null
}

export default function Profile(){
  const [user, setUser] = useState<User | null>(null)
  const [profile, setProfile] = useState<ProfileT>(emptyProfile)
  const [profileId, setProfileId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  useEffect(() => {
    (async () => {
      const u = await me()
      setUser(u)
      // получим текущую анкету
      const { data } = await api.get('/users/profile/')
      const p = Array.isArray(data) && data.length ? data[0] : null
      if (p){ setProfileId(p.id); setProfile({...p}) }
    })()
  }, [])

  const change = (key: keyof ProfileT, v: any) => setProfile(prev => ({...prev, [key]: v}))
  const allergyStr = useMemo(()=> profile.allergies.join(', '), [profile])
  const exclStr = useMemo(()=> profile.exclusions.join(', '), [profile])

  async function save(){
    setSaving(true); setMsg(null)
    try{
      // PATCH/PUT на профиль пользователя
      if (profileId){
        await api.patch(`/users/profile/${profileId}/`, profile)
      } else {
        await api.post(`/users/profile/`, profile)
      }
      setMsg('Сохранено ✅')
    }catch(e: any){
      setMsg(e?.response?.data?.detail || 'Ошибка сохранения')
    }finally{ setSaving(false) }
  }

  return (
    <div className="card">
      <h2 style={{marginTop:0}}>Анкета</h2>
      {user && <div className="small">Пользователь: <b>{user.username}</b> ({user.email||'нет e-mail'})</div>}
      <div className="row" style={{marginTop:10}}>
        <div className="col">
          <label>Пол</label>
          <select value={profile.sex} onChange={e=>change('sex', e.target.value as any)}>
            <option value="m">Мужской</option>
            <option value="f">Женский</option>
          </select>
        </div>
        <div className="col">
          <label>Дата рождения</label>
          <input type="date" value={profile.birth_date || ''} onChange={e=>change('birth_date', e.target.value)} />
        </div>
        <div className="col">
          <label>Рост (см)</label>
          <input type="number" value={profile.height_cm} onChange={e=>change('height_cm', Number(e.target.value))}/>
        </div>
        <div className="col">
          <label>Вес (кг)</label>
          <input type="number" step="0.1" value={profile.weight_kg} onChange={e=>change('weight_kg', Number(e.target.value))}/>
        </div>
      </div>

      <div className="row">
        <div className="col">
          <label>Активность</label>
          <select value={profile.activity_level} onChange={e=>change('activity_level', e.target.value as any)}>
            <option value="sedentary">sedentary</option>
            <option value="light">light</option>
            <option value="moderate">moderate</option>
            <option value="high">high</option>
            <option value="athlete">athlete</option>
          </select>
        </div>
        <div className="col">
          <label>Цель</label>
          <select value={profile.goal} onChange={e=>change('goal', e.target.value as any)}>
            <option value="lose">lose</option>
            <option value="maintain">maintain</option>
            <option value="gain">gain</option>
            <option value="recomp">recomp</option>
          </select>
        </div>
        <div className="col">
          <label>Доля жира, % (опц.)</label>
          <input type="number" step="0.1" value={profile.body_fat_pct ?? ''} onChange={e=>change('body_fat_pct', e.target.value? Number(e.target.value): null)}/>
        </div>
        <div className="col">
          <label>Дневной бюджет (опц.)</label>
          <input type="number" value={profile.daily_budget ?? ''} onChange={e=>change('daily_budget', e.target.value? Number(e.target.value): null)}/>
        </div>
      </div>

      <div className="row">
        <div className="col">
          <label>Аллергии (через запятую)</label>
          <input value={allergyStr} onChange={e=>change('allergies', e.target.value.split(',').map(s=>s.trim()).filter(Boolean))}/>
        </div>
        <div className="col">
          <label>Исключения (через запятую)</label>
          <input value={exclStr} onChange={e=>change('exclusions', e.target.value.split(',').map(s=>s.trim()).filter(Boolean))}/>
        </div>
      </div>

      <div className="form-actions" style={{marginTop:12}}>
        <button onClick={save} disabled={saving}>{saving?'Сохраняю…':'Сохранить'}</button>
      </div>
      {msg && <div className="small" style={{marginTop:8}}>{msg}</div>}
    </div>
  )
}
