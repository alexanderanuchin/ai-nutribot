import React, { useEffect, useMemo, useState } from 'react'
import api from '../api/client'
import { me } from '../api/auth'
import type { Activity, Goal, Profile as ProfileT, User } from '../types'
import { updateProfile, type ProfileUpdatePayload, type ProfileResponse } from '../api/profile'
import ProfileEditDialog from '../components/ProfileEditDialog'
import ProfileSidebar from '../components/ProfileSidebar'

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
  experience_level_display: 'Новичок'
}

const activityFactors: Record<Activity, number> = {
  sedentary: 1.2,
  light: 1.375,
  moderate: 1.55,
  high: 1.725,
  athlete: 1.9
}

const goalAdjustments: Record<Goal, number> = {
  lose: -450,
  maintain: 0,
  gain: 350,
  recomp: -150
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

interface MacroSuggestion {
  label: string
  grams: number
  ratio: number
  color: string
}


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

  useEffect(() => {
    let cancelled = false

    async function loadProfile(){
      try {
        const userData = await me()

        if (cancelled) return

        let profileData: ProfileResponse | null = null
        try {
          const response = await api.get<ProfileResponse>('/users/me/profile/')
          profileData = response.data
        } catch (profileError) {
          console.error('Не удалось загрузить профиль', profileError)
        }

        if (cancelled) return

        const mergedUser: User = (() => {
          const profileUser = profileData?.user
          if (!profileUser) return userData
          return {
            ...userData,
            ...profileUser,
            first_name: profileUser.first_name || userData.first_name,
            last_name: profileUser.last_name || userData.last_name,
            email: profileUser.email || userData.email,
            username: profileUser.username || userData.username,
            avatar_url: profileUser.avatar_url ?? userData.avatar_url,
            city: profileUser.city || userData.city,
            telegram_id: profileUser.telegram_id ?? userData.telegram_id
          }
        })()

        setUser(mergedUser)

        if (profileData) {
          const { user: _profileUser, ...profilePayload } = profileData
          setProfileId(profilePayload.id ?? null)
          setProfile(prev => ({ ...prev, ...profilePayload }))
        }
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

    const age = useMemo(() => {
    if (!profile.birth_date) return null
    const birth = new Date(profile.birth_date)
    if (Number.isNaN(birth.getTime())) return null
    const now = new Date()
    let years = now.getFullYear() - birth.getFullYear()
    const hasHadBirthday =
      now.getMonth() > birth.getMonth() ||
      (now.getMonth() === birth.getMonth() && now.getDate() >= birth.getDate())
    if (!hasHadBirthday) years -= 1
    return years > 0 ? years : null
  }, [profile.birth_date])

  const bmi = useMemo(() => {
    if (!profile.height_cm || !profile.weight_kg) return null
    const heightMeters = profile.height_cm / 100
    if (!heightMeters) return null
    const value = profile.weight_kg / (heightMeters * heightMeters)
    return Number.isFinite(value) ? Number(value.toFixed(1)) : null
  }, [profile.height_cm, profile.weight_kg])

  const bmiStatus = useMemo(() => {
    if (!bmi) return null
    if (bmi < 18.5) return 'Недостаточная масса'
    if (bmi < 25) return 'Норма'
    if (bmi < 30) return 'Избыточная масса'
    return 'Требуется внимание'
  }, [bmi])

  const bmr = useMemo(() => {
    if (!profile.height_cm || !profile.weight_kg) return null
    const ageForCalc = age ?? 30
    const height = profile.height_cm
    const weight = profile.weight_kg
    const base = profile.sex === 'm'
      ? 88.36 + 13.4 * weight + 4.8 * height - 5.7 * ageForCalc
      : 447.6 + 9.2 * weight + 3.1 * height - 4.3 * ageForCalc
    return Math.round(base)
  }, [profile.height_cm, profile.weight_kg, profile.sex, age])

  const tdee = useMemo(() => {
    if (!bmr) return null
    const multiplier = activityFactors[profile.activity_level] ?? 1.2
    return Math.round(bmr * multiplier)
  }, [bmr, profile.activity_level])

  const recommendedCalories = useMemo(() => {
    if (!tdee) return null
    const adjustment = goalAdjustments[profile.goal] ?? 0
    const value = tdee + adjustment
    return Math.max(1200, Math.round(value))
  }, [tdee, profile.goal])

  const macros = useMemo<MacroSuggestion[] | null>(() => {
    if (!recommendedCalories) return null
    const proteinRatio = profile.goal === 'gain' ? 0.28 : profile.goal === 'lose' ? 0.32 : profile.goal === 'recomp' ? 0.3 : 0.27
    const fatRatio = profile.goal === 'lose' ? 0.27 : 0.28
    const carbRatio = Math.max(0, 1 - proteinRatio - fatRatio)
    return [
      {
        label: 'Белки',
        grams: Math.round((recommendedCalories * proteinRatio) / 4),
        ratio: proteinRatio,
        color: 'var(--primary)'
      },
      {
        label: 'Жиры',
        grams: Math.round((recommendedCalories * fatRatio) / 9),
        ratio: fatRatio,
        color: 'var(--accent)'
      },
      {
        label: 'Углеводы',
        grams: Math.round((recommendedCalories * carbRatio) / 4),
        ratio: carbRatio,
        color: 'rgba(124, 211, 255, 0.6)'
      }
    ]
  }, [recommendedCalories, profile.goal])

  const summaryStats = useMemo(() => ([
    {
      label: 'Возраст',
      value: age ? formatYears(age) : 'Добавьте дату',
      hint: age ? 'Используется в расчётах BMR' : 'Укажите дату рождения для точности'
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
  ]), [age, bmi, bmiStatus, tdee, recommendedCalories, profile.goal])

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
      const data = await updateProfile(payload)
      const { user: updatedUser, ...profilePayload } = data
      if (profilePayload.id) {
        setProfileId(profilePayload.id)
      }
      setProfile(prev => ({ ...prev, ...profilePayload }))
      setUser(prev => (prev ? { ...prev, ...updatedUser } : updatedUser))
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
