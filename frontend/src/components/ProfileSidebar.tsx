import React, { useEffect, useId, useState } from 'react'
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

const rubFormatter = new Intl.NumberFormat('ru-RU', {
  style: 'currency',
  currency: 'RUB',
  maximumFractionDigits: 0
})
const rubRateFormatter = new Intl.NumberFormat('ru-RU', {
  style: 'currency',
  currency: 'RUB',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})

const integerFormatter = new Intl.NumberFormat('ru-RU', {
  maximumFractionDigits: 0
})

const parseNumber = (value: unknown): number | null => {
  if (value === null || value === undefined || value === '') return null
  const numeric = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(numeric) ? numeric : null
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

const walletPerks = [
  'Эксклюзивные планы питания с адаптацией под ваши тренировки',
  'Доступ к мини-курсам и лайв-сессиям нутрициологов каждую неделю',
  'Экспериментальные фичи AI-куратора без ограничений'
]

function TelegramStarIcon(props: React.SVGProps<SVGSVGElement>){
  return (
    <svg
      viewBox="0 0 40 40"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      <defs>
        <linearGradient id="starGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#9fd8ff" />
          <stop offset="50%" stopColor="#5bbcff" />
          <stop offset="100%" stopColor="#4aa0ff" />
        </linearGradient>
      </defs>
      <circle cx="20" cy="20" r="19" fill="rgba(91, 188, 255, 0.16)" stroke="#5bbcff" strokeWidth="1.5" />
      <path
        d="M20 8l3.18 6.82 7.52 1.06-5.44 5.25 1.28 7.43L20 25.9l-6.54 3.44 1.28-7.43-5.44-5.25 7.52-1.06z"
        fill="url(#starGradient)"
        stroke="rgba(12, 18, 27, 0.22)"
        strokeWidth="0.8"
      />
    </svg>
  )
}

function CaloCoinIcon(props: React.SVGProps<SVGSVGElement>){
  return (
    <svg
      viewBox="0 0 40 40"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      <defs>
        <radialGradient id="caloGradient" cx="50%" cy="40%" r="70%">
          <stop offset="0%" stopColor="#f6ffe2" />
          <stop offset="45%" stopColor="#8ff0a6" />
          <stop offset="100%" stopColor="#47c974" />
        </radialGradient>
      </defs>
      <circle cx="20" cy="20" r="19" fill="rgba(142, 240, 166, 0.14)" stroke="#68e391" strokeWidth="1.5" />
      <path
        d="M20 9.5c5.8 0 10.5 4.7 10.5 10.5S25.8 30.5 20 30.5 9.5 25.8 9.5 20 14.2 9.5 20 9.5zm0 4c-3.6 0-6.5 2.9-6.5 6.5s2.9 6.5 6.5 6.5c1.7 0 3.3-.7 4.5-1.8l-2.2-2.2c-.6.6-1.4 1-2.3 1-1.8 0-3.2-1.4-3.2-3.2 0-1.8 1.4-3.2 3.2-3.2.9 0 1.7.4 2.3 1l2.2-2.2c-1.2-1.1-2.8-1.8-4.5-1.8z"
        fill="url(#caloGradient)"
        stroke="rgba(12, 18, 27, 0.22)"
        strokeWidth="0.8"
      />
    </svg>
  )
}


export default function ProfileSidebar({ user, profile, age, bmi, bmiStatus, tdee, recommendedCalories }: ProfileSidebarProps){
  const [showWallet, setShowWallet] = useState(false)
  const walletHintId = useId()
  const displayName = user?.username || 'Профиль'
  const email = user?.email || 'email не указан'
  const avatarUrl = user?.avatar_url || null
  const initials = displayName.slice(0, 2).toUpperCase()
  const city = profile.city || user?.city || null
  const normalizedDailyBudget = parseNumber(profile.daily_budget)
  const hasDailyBudget = normalizedDailyBudget !== null && normalizedDailyBudget > 0
  const dailyBudgetValue = hasDailyBudget && normalizedDailyBudget !== null ? normalizedDailyBudget : 0
  const starsBalanceRaw = parseNumber(profile.telegram_stars_balance)
  const starsBalance = starsBalanceRaw !== null ? Math.max(0, Math.floor(starsBalanceRaw)) : 0
  const starsRate = parseNumber(profile.telegram_stars_rate_rub)
  const caloBalance = parseNumber(profile.calocoin_balance)
  const caloRate = parseNumber(profile.calocoin_rate_rub)
  const hasStarsRate = typeof starsRate === 'number' && starsRate > 0
  const hasCaloRate = typeof caloRate === 'number' && caloRate > 0
  const starsRateValue = hasStarsRate ? (starsRate as number) : 0
  const caloBalanceValue = caloBalance ?? 0
  const caloRateValue = hasCaloRate ? (caloRate as number) : 0
  const caloBalanceDisplay = caloBalanceValue.toLocaleString('ru-RU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
  const hasTelegramLink = Boolean(profile.telegram_id || user?.telegram_id)
  const starsRubEquivalent = hasStarsRate ? starsBalance * starsRateValue : null
  const caloRubEquivalent = hasCaloRate ? caloBalanceValue * caloRateValue : null
  const dailyBudgetDisplay = hasDailyBudget ? rubFormatter.format(dailyBudgetValue) : null
  const walletAriaLabel = showWallet ? 'Скрыть детали кошелька' : 'Показать детали кошелька'
  const walletHint = showWallet ? 'Скрыть баланс и действия' : 'Баланс скрыт — нажмите, чтобы раскрыть'

  useEffect(() => {
    if (!showWallet) return
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setShowWallet(false)
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [showWallet])

  const handleWalletClick = (event: React.MouseEvent<HTMLDivElement>) => {
    const target = event.target as HTMLElement
    if (target.closest('a, button')) return
    setShowWallet(prev => !prev)
  }

  const handleWalletKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    const target = event.target as HTMLElement
    if (target.closest('a, button')) {
      if (event.key === ' ') {
        event.preventDefault()
      }
      return
    }
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      setShowWallet(prev => !prev)
    }
    if (event.key === 'Escape' && showWallet) {
      event.preventDefault()
      setShowWallet(false)
    }
  }

  return (
    <aside className="profile-sidebar card">
      <div className="profile-sidebar__header">
        <div className="profile-sidebar__user">
          <div className="profile-sidebar__avatar">
            {avatarUrl ? (
              <img src={avatarUrl} alt={displayName} loading="lazy" />
            ) : (
              initials
            )}
          </div>
          <div
            className={`profile-sidebar__identity ${showWallet ? 'is-open' : ''}`}
            role="button"
            tabIndex={0}
            aria-pressed={showWallet}
            aria-expanded={showWallet}
            aria-label={walletAriaLabel}
            aria-describedby={walletHintId}
            onClick={handleWalletClick}
            onKeyDown={handleWalletKeyDown}
          >
            <div className={`profile-sidebar__identity-inner ${showWallet ? 'is-flipped' : ''}`}>
              <div className="profile-sidebar__identity-face profile-sidebar__identity-face--front">
                <div className="profile-sidebar__user-info">
                  <div className="profile-sidebar__username">{displayName}</div>
                  <div className="profile-sidebar__email">{email}</div>
                  {city && <div className="profile-sidebar__email">{city}</div>}
                </div>
                <div className="profile-sidebar__wallet-icons" aria-hidden="true">
                  <span className="profile-sidebar__wallet-icon profile-sidebar__wallet-icon--stars">
                    <TelegramStarIcon className="profile-sidebar__wallet-icon-svg" />
                  </span>
                  <span className="profile-sidebar__wallet-icon profile-sidebar__wallet-icon--calo">
                    <CaloCoinIcon className="profile-sidebar__wallet-icon-svg" />
                  </span>
                </div>
                <div className="profile-sidebar__wallet-tags">
                  <span className="profile-sidebar__wallet-tag">Telegram Stars</span>
                  <span className="profile-sidebar__wallet-tag">CaloCoin</span>
                </div>
                <span id={walletHintId} className="profile-sidebar__wallet-status small">{walletHint}</span>
              </div>
              <div className="profile-sidebar__identity-face profile-sidebar__identity-face--back">
                <div className="profile-sidebar__wallet-balance" aria-live="polite">
                  <div className="profile-sidebar__wallet-balance-row">
                    <div className="profile-sidebar__wallet-balance-info">
                      <TelegramStarIcon className="profile-sidebar__wallet-icon-svg" />
                      <div>
                        <div className="profile-sidebar__wallet-balance-label">Telegram Stars</div>
                        <div className="profile-sidebar__wallet-balance-value">{integerFormatter.format(starsBalance)}</div>
                        <div className="profile-sidebar__wallet-balance-hint small">
                          {hasStarsRate && starsRubEquivalent !== null
                            ? `≈ ${rubRateFormatter.format(starsRubEquivalent)} · ${rubRateFormatter.format(starsRateValue)} за 1`
                            : 'Добавьте курс, чтобы видеть стоимость покупки'}
                        </div>
                      </div>
                    </div>
                    <a
                      className="profile-sidebar__wallet-action"
                      href={hasTelegramLink ? 'https://t.me/wallet?start=star-topup' : 'https://t.me/ai_nutribot'}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Пополнить
                    </a>
                  </div>
                  <div className="profile-sidebar__wallet-balance-row">
                    <div className="profile-sidebar__wallet-balance-info">
                      <CaloCoinIcon className="profile-sidebar__wallet-icon-svg" />
                      <div>
                        <div className="profile-sidebar__wallet-balance-label">CaloCoin</div>
                        <div className="profile-sidebar__wallet-balance-value">{caloBalanceDisplay}</div>
                        <div className="profile-sidebar__wallet-balance-hint small">
                          {hasCaloRate && caloRubEquivalent !== null
                            ? `≈ ${rubRateFormatter.format(caloRubEquivalent)} · ${rubRateFormatter.format(caloRateValue)} за 1`
                            : 'Настройте курс CaloCoin, чтобы видеть рублевый эквивалент'}
                        </div>
                      </div>
                    </div>
                    <a
                      className="profile-sidebar__wallet-action"
                      href="https://t.me/ai_nutribot?start=calopro"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Оформить PRO
                    </a>
                  </div>
                </div>
                <div className="profile-sidebar__wallet-meta small">
                  {hasTelegramLink
                    ? 'Telegram Mini App подключён — пополнения синхронизируются автоматически.'
                    : 'Подключите Telegram Mini App, чтобы пополнять Stars в один тап.'}
                </div>
                <div className="profile-sidebar__wallet-meta small">
                  {dailyBudgetDisplay
                    ? `Рекомендованный дневной бюджет: ${dailyBudgetDisplay}`
                    : 'Добавьте дневной бюджет, чтобы CaloCoin планировал траты.'}
                </div>
                <ul className="profile-sidebar__wallet-perks">
                  {walletPerks.map(perk => (
                    <li key={perk}>{perk}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
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
