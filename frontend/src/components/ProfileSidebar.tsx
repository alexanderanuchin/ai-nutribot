import React from 'react'
import type { Profile as ProfileT, User } from '../types'

interface ProfileSidebarProps {
  user: User | null
  profile: ProfileT
  age: number | null
  bmi: number | null
  bmiStatus: string | null
  tdee: number | null
  recommendedCalories: number | null
}

const goalLabels: Record<ProfileT['goal'], string> = {
  lose: 'Снижение веса',
  maintain: 'Поддержание формы',
  gain: 'Набор массы',
  recomp: 'Рекомпозиция'
}

const activityLabels: Record<ProfileT['activity_level'], string> = {
  sedentary: 'Минимальная активность',
  light: 'Лёгкая активность',
  moderate: 'Умеренная активность',
  high: 'Высокая активность',
  athlete: 'Спортивный режим'
}

const NAV_SECTIONS = [
  {
    title: 'Панель управления',
    items: [
      {
        label: 'Главная сводка',
        description: 'Дневник энергии, воды, восстановления и планов на день.'
      },
      {
        label: 'Профиль и биомаркеры',
        description: 'Анкеты, обследования, интеграции с носимыми устройствами.'
      },
      {
        label: 'Цифровой двойник',
        description: 'Прогноз благополучия на 7 дней вперед с контекстными задачами.',
        badge: 'AI'
      }
    ]
  },
  {
    title: 'Питание и калории',
    items: [
      {
        label: 'Аналитика калорий',
        description: 'Текущий баланс БЖУ, окна питания, рекомендации по дефициту.'
      },
      {
        label: 'Конструктор рационов',
        description: 'Соберите меню из готовых блюд и собственных рецептов.',
        badge: 'Builder'
      },
      {
        label: 'Заказ и доставка',
        description: 'Маркетплейс здоровой еды с синхронизацией с таргетами.',
        badge: 'FoodTech'
      }
    ]
  },
  {
    title: 'Фитнес и восстановление',
    items: [
      {
        label: 'Программы тренировок',
        description: 'AI-планировщик, periodization, синхронизация с устройствами.'
      },
      {
        label: 'Мониторинг восстановления',
        description: 'HRV, сон, стресс и дыхательные протоколы.'
      },
      {
        label: 'Цели на неделю',
        description: 'Умные чек-листы привычек и восстановления.'
      }
    ]
  },
  {
    title: 'Интеллект и автоматизация',
    items: [
      {
        label: 'AI-куратор здоровья',
        description: 'Диалоговый ассистент 24/7 с объяснимыми рекомендациями.',
        badge: 'AI'
      },
      {
        label: 'Прогноз рисков',
        description: 'Предиктивные алерты по данным сна, калорий и активности.',
        badge: 'Predictive'
      },
      {
        label: 'Команда экспертов',
        description: 'Нутрициолог, тренер и врач в одном пространстве.'
      }
    ]
  },
  {
    title: 'Конструкторы',
    items: [
      {
        label: 'Таргеты и макросы',
        description: 'Личные сценарии для будней, тренировок и отдыха.'
      },
      {
        label: 'Конструктор привычек',
        description: 'Сформируйте дорожную карту здоровья и напоминания.'
      },
      {
        label: 'Экосистема гаджетов',
        description: 'Подключите весы, трекеры, анализаторы воздуха и воды.'
      }
    ]
  }
]

export default function ProfileSidebar({ user, profile, age, bmi, bmiStatus, tdee, recommendedCalories }: ProfileSidebarProps){
  const displayName = user?.username || 'Профиль'
  const email = user?.email || 'email не указан'
  const avatarUrl = user?.avatar_url || null
  const initials = displayName.slice(0, 2).toUpperCase()

  return (
    <aside className="profile-sidebar card">
      <div className="profile-sidebar__user">
        <div className="profile-sidebar__avatar">
          {avatarUrl ? (
            <img src={avatarUrl} alt={displayName} loading="lazy" />
          ) : (
            initials
          )}
        </div>
        <div className="profile-sidebar__user-info">
          <div className="profile-sidebar__username">{displayName}</div>
          <div className="profile-sidebar__email">{email}</div>
          {user?.city && <div className="profile-sidebar__email">{user.city}</div>}
        </div>
      </div>

      <div className="profile-sidebar__chips">
        <span className="profile-sidebar__chip">{goalLabels[profile.goal]}</span>
        <span className="profile-sidebar__chip">{activityLabels[profile.activity_level]}</span>
      </div>

      <div className="profile-sidebar__metrics">
        <div className="profile-sidebar__metric">
          <div className="profile-sidebar__metric-label">Возраст</div>
          <div className="profile-sidebar__metric-value">{age !== null ? `${age} лет` : 'Укажите'}</div>
        </div>
        <div className="profile-sidebar__metric">
          <div className="profile-sidebar__metric-label">ИМТ</div>
          <div className="profile-sidebar__metric-value">{bmi !== null ? `${bmi}` : '—'}</div>
          {bmiStatus && <div className="profile-sidebar__metric-hint small">{bmiStatus}</div>}
        </div>
        <div className="profile-sidebar__metric">
          <div className="profile-sidebar__metric-label">TDEE</div>
          <div className="profile-sidebar__metric-value">{tdee ? `${tdee} ккал` : '—'}</div>
        </div>
        <div className="profile-sidebar__metric">
          <div className="profile-sidebar__metric-label">Дневная цель</div>
          <div className="profile-sidebar__metric-value">{recommendedCalories ? `${recommendedCalories} ккал` : '—'}</div>
        </div>
      </div>

      <nav className="profile-sidebar__nav">
        {NAV_SECTIONS.map(section => (
          <div key={section.title} className="profile-sidebar__section">
            <div className="profile-sidebar__section-title">{section.title}</div>
            <ul className="profile-sidebar__list">
              {section.items.map(item => (
                <li key={item.label} className="profile-sidebar__item">
                  <div>
                    <div className="profile-sidebar__item-label">{item.label}</div>
                    <div className="profile-sidebar__item-description">{item.description}</div>
                  </div>
                  {item.badge && <span className="profile-sidebar__badge">{item.badge}</span>}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="profile-sidebar__footer">
        <button type="button" className="profile-sidebar__cta">Открыть AI-куратора</button>
        <p className="small">Персональные сценарии обновляются в реальном времени на основе ваших данных и целей.</p>
      </div>
    </aside>
  )
}
