import React, { useEffect, useMemo, useState } from 'react'
import api from '../api/client'
import { me } from '../api/auth'
import type { Activity, Goal, MacroBreakdown, Profile as ProfileT, User } from '../types'
import { updateProfile, type ProfileUpdatePayload, type ProfileUpdateResult } from '../api/profile'
import ProfileEditDialog from '../components/ProfileEditDialog'
import ProfileSidebar from '../components/ProfileSidebar'
import { tokenStore } from '../utils/storage'

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
  daily_budget: null,
  telegram_id: null,
  city: '',
  telegram_stars_balance: 0,
  telegram_stars_rate_rub: 0,
  calocoin_balance: 0,
  calocoin_rate_rub: 0,
  middle_name: '',
  experience_level: 'newbie',
  experience_level_display: 'Новичок',
  metrics: null,
  avatar_preferences: { kind: 'initials' },
  wallet_settings: { show_wallet: false }
}

const goalLabels: Record<Goal, string> = {
  lose: 'Снижение веса',
  maintain: 'Поддержание формы',
  gain: 'Набор массы',
  recomp: 'Рекомпозиция'
}

const activityLabels: Record<Activity, string> = {
  sedentary: 'Минимальная активность',
  light: 'Лёгкая активность',
  moderate: 'Умеренная активность',
  high: 'Высокая активность',
  athlete: 'Спортивный режим'
}

function formatYears(age: number){
  const mod10 = age % 10
  const mod100 = age % 100
  if (mod10 === 1 && mod100 !== 11) return `${age} год`
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return `${age} года`
  return `${age} лет`
}

type MacroSuggestion = MacroBreakdown & { color: string }


export default function Profile(){
  const [user, setUser] = useState<User | null>(null)
  const [profile, setProfile] = useState<ProfileT>(emptyProfile)
  const [profileId, setProfileId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [isEditOpen, setEditOpen] = useState(false)
  const [editSubmitting, setEditSubmitting] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)
  const [profileNotice, setProfileNotice] = useState<string | null>(null)

  const syncProfileState = (data: ProfileUpdateResult) => {
    const { user: updatedUser, profile: profilePayload, metrics, tokens } = data
    const mergedProfile = {
      ...profilePayload,
      metrics: metrics ?? profilePayload.metrics ?? null
    }
    setProfileId(mergedProfile.id ?? null)
    setProfile(prev => ({ ...prev, ...mergedProfile }))
    setUser(prev => (prev ? { ...prev, ...updatedUser } : updatedUser))
    if (tokens) {
      if (tokens.refresh) {
        tokenStore.refresh = tokens.refresh
      }
      tokenStore.access = tokens.access
    }
    return data
  }

  const submitProfileUpdate = async (payload: ProfileUpdatePayload) => {
    const data = await updateProfile(payload)
    return syncProfileState(data)
  }


  useEffect(() => {
    let cancelled = false

    async function loadProfile(){
      try {
        const meData = await me()

        if (cancelled) return

        const normalizedProfile = {
          ...meData.profile,
          metrics: meData.metrics ?? meData.profile.metrics ?? null
        }

        setUser(prev => (prev ? { ...prev, ...meData.user } : meData.user))
        setProfileId(normalizedProfile.id ?? null)
        setProfile(prev => ({ ...prev, ...normalizedProfile }))
      } catch (error) {
        console.error('Не удалось загрузить данные пользователя', error)
      }
    }

    loadProfile()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!profileNotice) return
    const timer = window.setTimeout(() => setProfileNotice(null), 6000)
    return () => window.clearTimeout(timer)
  }, [profileNotice])

  const change = (key: keyof ProfileT, v: any) => setProfile(prev => ({...prev, [key]: v}))
  const allergyStr = useMemo(()=> profile.allergies.join(', '), [profile])
  const exclStr = useMemo(()=> profile.exclusions.join(', '), [profile])
  const metrics = profile.metrics ?? null
  const metricsAge = metrics?.age ?? null
  const ageDisplay = metrics?.age_display ?? (metricsAge !== null ? formatYears(metricsAge) : null)
  const bmi = metrics?.bmi ?? null
  const bmiStatus = metrics?.bmi_status ?? null
  const tdee = metrics?.tdee ?? null
  const recommendedCalories = metrics?.recommended_calories ?? null
  const age = metricsAge

  const macros = useMemo<MacroSuggestion[] | null>(() => {
    const macroList = metrics?.macros ?? []
    if (!macroList.length) return null
    const palette = ['var(--primary)', 'var(--accent)', 'rgba(124, 211, 255, 0.6)']
    return macroList.map((macro, index) => ({
      ...macro,
      color: macro.color ?? palette[index % palette.length]
    }))
  }, [metrics])

  const summaryStats = useMemo(() => ([
    {
      label: 'Возраст',
      value: ageDisplay ?? 'Добавьте дату',
      hint: metricsAge !== null ? 'Используется в расчётах BMR' : 'Укажите дату рождения для точности'
    },
    {
      label: 'ИМТ',
      value: bmi ? `${bmi}` : 'Нет данных',
      hint: bmiStatus ?? 'Расчёт выполнится при указании роста и веса'
    },
    {
      label: 'TDEE',
      value: tdee ? `${tdee} ккал` : '—',
      hint: 'Расход энергии с учётом активности'
    },
    {
      label: 'Дневная цель',
      value: recommendedCalories ? `${recommendedCalories} ккал` : '—',
      hint: goalLabels[profile.goal]
    }
  ]), [ageDisplay, metricsAge, bmi, bmiStatus, tdee, recommendedCalories, profile.goal])

  const aiCapabilities = [
    {
      title: 'AI-сценарии питания',
      description: 'Алгоритм синхронизирует меню с тренировками, сном и расписанием встреч.'
    },
    {
      title: 'Превентивные уведомления',
      description: 'Ранние сигналы, если калорийность, сон или активность выходят из баланса.'
    },
    {
      title: 'Совместная работа с экспертами',
      description: 'Общий чат и заметки для нутрициолога, тренера и врача.'
    }
  ]

  const serviceHighlights = [
    {
      title: 'Умная доставка еды',
      description: 'Подбор сервисов и расписание заказов под ваш план и бюджет.'
    },
    {
      title: 'Конструктор продуктовых наборов',
      description: 'Соберите боксы под разные сценарии: офис, тренировки, путешествия.'
    },
    {
      title: 'Управление запасами',
      description: 'Ведите учёт суперфудов, добавок и автоматически пополняйте их.'
    }
  ]
  const handleProfileEditSubmit = async (payload: ProfileUpdatePayload) => {
    setEditSubmitting(true)
    setEditError(null)
    try {
      await submitProfileUpdate(payload)
      setProfileNotice('Профиль обновлён — изменения применены.')
      setEditOpen(false)
    } catch (error) {
      let message = 'Не удалось сохранить изменения. Проверьте введённые данные.'
      if (error && typeof error === 'object') {
        const response = (error as any).response
        const data = response?.data
        if (typeof data === 'string') {
          message = data
        } else if (data?.detail) {
          message = data.detail
        } else if (data && typeof data === 'object') {
          const firstKey = Object.keys(data)[0]
          const firstValue = (data as Record<string, unknown>)[firstKey]
          if (Array.isArray(firstValue) && firstValue.length) {
            const candidate = firstValue[0]
            if (typeof candidate === 'string') {
              message = candidate
            }
          }
        }
      }
      setEditError(message)
    } finally {
      setEditSubmitting(false)
    }
  }
  const handlePreferencesUpdate = async (payload: Pick<ProfileUpdatePayload, 'avatar_preferences' | 'wallet_settings'>) => {
    return submitProfileUpdate(payload)
  }

  const openEditDialog = () => {
    setEditError(null)
    setEditOpen(true)
  }

  async function save(){
    setSaving(true); setMsg(null)
    try{
      // PATCH/PUT на профиль пользователя
      if (profileId){
        await api.patch(`/users/profiles/${profileId}/`, profile)
      } else {
        await api.post(`/users/profiles/`, profile)
      }
      setMsg('Сохранено ✅')
    }catch(e: any){
      setMsg(e?.response?.data?.detail || 'Ошибка сохранения')
    }finally{ setSaving(false) }
  }

  return (
    <>
      <div className="profile-layout">
      <ProfileSidebar
        user={user}
        profile={profile}
        age={age}
        bmi={bmi}
        bmiStatus={bmiStatus}
        tdee={tdee}
        recommendedCalories={recommendedCalories}
        onEditProfile={openEditDialog}
        profileUpdateNotice={profileNotice}
        onPreferencesUpdate={handlePreferencesUpdate}
      />
      <div className="profile-main">
        <div className="profile-main-columns">
          <div className="profile-main-col">
            <div className="card profile-summary-card">
              <div className="profile-card-header">
                <h2 className="profile-section-title">Пульс здоровья</h2>
                <p className="small">Актуализируем ключевые показатели, чтобы AI принимал верные решения.</p>
              </div>
              <div className="profile-stats-grid">
                {summaryStats.map(stat => (
                  <div key={stat.label} className="profile-stat">
                    <div className="profile-stat__label">{stat.label}</div>
                    <div className="profile-stat__value">{stat.value}</div>
                    {stat.hint && <div className="profile-stat__hint small">{stat.hint}</div>}
                  </div>
                ))}
              </div>
            </div>

            <div className="card profile-form-card">
              <div className="profile-card-header">
                <div>
                  <h2 className="profile-section-title">Анкета здоровья</h2>
                  <p className="small">Заполните профиль, чтобы алгоритмы рассчитывали калории и меню точнее.</p>
                </div>
                <span className="profile-card-badge">Live sync</span>
              </div>
              {user && (
                <div className="profile-form-meta small">
                  <span>Пользователь: <b>{user.username}</b></span>
                  <span className="profile-form-meta__separator">•</span>
                  <span>{user.email || 'нет e-mail'}</span>
                </div>
              )}
              <div className="row" style={{marginTop:10}}>
                <div className="col">
                  <label>Пол</label>
                  <select value={profile.sex} onChange={e=>change('sex', e.target.value as ProfileT['sex'])}>
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
                  <select value={profile.activity_level} onChange={e=>change('activity_level', e.target.value as Activity)}>
                    {Object.entries(activityLabels).map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                </div>
                <div className="col">
                  <label>Цель</label>
                  <select value={profile.goal} onChange={e=>change('goal', e.target.value as Goal)}>
                    {Object.entries(goalLabels).map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
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
          </div>

          <div className="profile-aside-col">
            <div className="card profile-calculator-card">
              <h3 className="profile-section-subtitle">AI-калькулятор калорий</h3>
              <p className="small">Сценарий учитывает цель, активность и обновляется при изменении данных.</p>
              <div className="profile-calorie-highlight">
                <div className="profile-calorie-value">{recommendedCalories ? `${recommendedCalories} ккал` : 'Добавьте данные'}</div>
                <div className="small">Целевая норма на сегодня</div>
              </div>
              {macros ? (
                <div className="profile-macro-list">
                  {macros.map(macro => (
                    <div key={macro.label} className="profile-macro">
                      <div className="profile-macro__header">
                        <span className="profile-macro__label">{macro.label}</span>
                        <span className="profile-macro__value">{macro.grams} г</span>
                      </div>
                      <div className="profile-macro__bar">
                        <span style={{ width: `${Math.round(macro.ratio * 100)}%`, background: macro.color }}></span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="small">Укажите дату рождения, рост и вес, чтобы рассчитать БЖУ.</div>
              )}
            </div>

            <div className="card profile-ai-card">
              <h3 className="profile-section-subtitle">Интеллектуальные ассистенты</h3>
              <p className="small">Комбинируйте автоматизацию и живых экспертов для идеального самочувствия.</p>
              <ul className="profile-feature-list">
                {aiCapabilities.map(item => (
                  <li key={item.title} className="profile-feature-item">
                    <div className="profile-feature-item__title">{item.title}</div>
                    <div className="profile-feature-item__description small">{item.description}</div>
                  </li>
                ))}
              </ul>
            </div>

            <div className="card profile-service-card">
              <h3 className="profile-section-subtitle">Питание и сервисы</h3>
              <p className="small">Управляйте заказами еды и создавайте собственные наборы под цели.</p>
              <ul className="profile-feature-list">
                {serviceHighlights.map(item => (
                  <li key={item.title} className="profile-feature-item">
                    <div className="profile-feature-item__title">{item.title}</div>
                    <div className="profile-feature-item__description small">{item.description}</div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
      <ProfileEditDialog
        open={isEditOpen}
        onClose={() => {
          setEditOpen(false)
          setEditError(null)
        }}
        user={user}
        profile={profile}
        onSubmit={handleProfileEditSubmit}
        submitting={editSubmitting}
        error={editError}
      />
    </>
  )
}
