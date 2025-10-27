import React, { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import type { ExperienceLevel, Profile as ProfileT, User, WalletSummary, WalletTransactionRecord } from '../types'
import type { ProfileUpdatePayload } from '../api/profile'
import { formatPhoneInput } from '../utils/phone'
import {
  AVATAR_PRESETS,
  deriveAvatarState,
  getAvatarImageSrc,
  getAvatarPreset,
  type AvatarState,
} from '../utils/avatar'

const useIsomorphicLayoutEffect = typeof window !== 'undefined' ? useLayoutEffect : useEffect

type ProfilePreferencesUpdatePayload = Pick<ProfileUpdatePayload, 'avatar_preferences' | 'wallet_settings'>

interface ProfileSidebarProps {
  user: User | null
  profile: ProfileT
  age: number | null
  bmi: number | null
  bmiStatus: string | null
  tdee: number | null
  recommendedCalories: number | null
  onEditProfile?: () => void
  profileUpdateNotice?: string | null
  onPreferencesUpdate?: (payload: ProfilePreferencesUpdatePayload) => Promise<unknown>
  walletSummary?: WalletSummary | null
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

const experienceLevelMeta: Record<ExperienceLevel, {
  title: string
  summary: string
  course: string
  temperature: number
  humidity: number
  water: string
  micronutrients: string
  uv: string
  extra: string
}> = {
  newbie: {
    title: 'Новичок',
    summary: 'Спокойный старт: фиксируем базовые привычки и наблюдаем динамику.',
    course: 'Курс адаптации · 62%',
    temperature: 22,
    humidity: 47,
    water: 'Вода средней минерализации · ~240 мг/л',
    micronutrients: 'Фокус: витамин D, магний и лёгкий комплекс группы B.',
    uv: 'УФ-индекс низкий (2/11) — прогулки до полудня комфортны.',
    extra: 'Совет дня: добавьте ещё 2 стакана воды и короткую прогулку.'
  },
  enthusiast: {
    title: 'Энтузиаст',
    summary: 'Вы на ускоренной траектории — поддерживаем тонус без перегрузок.',
    course: 'Курс прогресса · 74%',
    temperature: 21,
    humidity: 44,
    water: 'Вода: баланс Ca/Mg 3:1 — идеальна для восстановления.',
    micronutrients: 'Проверьте омега-3 и коэнзим Q10 для выносливости.',
    uv: 'УФ-индекс умеренный (4/11) — SPF для прогулок после 14:00.',
    extra: 'Добавьте растяжку на 10 минут — снизит мышечное напряжение.'
  },
  pro: {
    title: 'Профи',
    summary: 'Тонкая настройка нагрузок и питания: данные обновляются каждые 4 часа.',
    course: 'Курс мастерства · 88%',
    temperature: 20,
    humidity: 42,
    water: 'Минерализация повышенная · 320 мг/л, следим за натрием.',
    micronutrients: 'Актуальны цинк, селен и адаптогены для когнитивной ясности.',
    uv: 'УФ-индекс высокий (6/11) — добавьте SPF 30 и очки.',
    extra: 'Интегрируйте дыхательные практики — HRV откликнет ростом.'
  },
  legend: {
    title: 'Легенда',
    summary: 'Максимальный контроль: AI синхронизирует экспертов и гаджеты в реальном времени.',
    course: 'Курс прорыва · 95%',
    temperature: 19,
    humidity: 40,
    water: 'Артезианская вода ~380 мг/л, подключим анализ минералов.',
    micronutrients: 'Слежение за железом, витамином K2 и персональными добавками.',
    uv: 'УФ-индекс интенсивный (7/11) — планируйте тренировки до 11:00.',
    extra: 'Сценарий дня: чередуйте силовые блоки с холодовым протоколом.'
  }
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

const decimalFormatter = new Intl.NumberFormat('ru-RU', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2
})

const transactionDateFormatter = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit'
})

const parseNumber = (value: unknown): number | null => {
  if (value === null || value === undefined || value === '') return null
  const numeric = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(numeric) ? numeric : null
}

const applyTemplate = (template: string | null | undefined, fallback: string, replacements: Record<string, string>): string => {
  const source = (template ?? '').trim() || fallback
  return source.replace(/\{(\w+)\}/g, (_match, key: string) => {
    return Object.prototype.hasOwnProperty.call(replacements, key) ? replacements[key] : ''
  })
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

const DEFAULT_WALLET_PERKS = [
  'Эксклюзивные планы питания с адаптацией под ваши тренировки',
  'Доступ к мини-курсам и лайв-сессиям нутрициологов каждую неделю',
  'Экспериментальные фичи AI-куратора без ограничений'
]

const DEFAULT_STARS_REWARD_TARGET = 500
const DEFAULT_CALO_REWARD_TARGET = 1200

const DEFAULT_STARS_TARGET_LABEL = 'До клубной консультации'
const DEFAULT_STARS_PROGRESS_TEMPLATE = 'Ещё {left} Stars — и куратор свяжется с вами.'
const DEFAULT_STARS_COMPLETED_TEMPLATE = 'Доступ к консультациям открыт — напишите куратору в @CaloIQ_bot.'
const DEFAULT_CALO_TARGET_LABEL = 'До PRO-доступа'
const DEFAULT_CALO_PROGRESS_TEMPLATE = 'Накопите ещё {left} CaloCoin для полного PRO.'
const DEFAULT_CALO_COMPLETED_TEMPLATE = 'Баланс позволяет активировать PRO прямо сейчас.'
const MAX_AVATAR_SIZE = 2 * 1024 * 1024

const isSameAvatarState = (a: AvatarState, b: AvatarState): boolean => {
  if (a.kind !== b.kind) return false
  switch (a.kind) {
    case 'initials':
      return true
    case 'external':
      return a.url === (b as typeof a).url
    case 'preset':
      return a.id === (b as typeof a).id
    case 'upload':
      return a.dataUrl === (b as typeof a).dataUrl
    default:
      return false
  }
}

const avatarStateToPreferencesPayload = (
  state: AvatarState
): ProfilePreferencesUpdatePayload | null => {
  switch (state.kind) {
    case 'preset':
      return { avatar_preferences: { kind: 'preset', preset_id: state.id } }
    case 'upload':
      return { avatar_preferences: { kind: 'upload', data_url: state.dataUrl } }
    case 'external':
    case 'initials':
      return { avatar_preferences: { kind: 'initials' } }
    default:
      return null
  }
}

function TelegramStarIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 40 40"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      <defs>
        <linearGradient id="starGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="var(--badge-telegram-stop-start)" />
          <stop offset="50%" stopColor="var(--badge-telegram-stop-mid)" />
          <stop offset="100%" stopColor="var(--badge-telegram-stop-end)" />
        </linearGradient>
      </defs>
      <circle
        cx="20"
        cy="20"
        r="19"
        fill="var(--badge-telegram-fill)"
        stroke="var(--badge-telegram-stroke)"
        strokeWidth="1.5"
      />
      <path
        d="M20 8l3.18 6.82 7.52 1.06-5.44 5.25 1.28 7.43L20 25.9l-6.54 3.44 1.28-7.43-5.44-5.25 7.52-1.06z"
        fill="url(#starGradient)"
        stroke="var(--badge-outline)"
        strokeWidth="0.8"
      />
    </svg>
  )
}

function CaloCoinIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 40 40"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      <defs>
        <radialGradient id="caloGradient" cx="50%" cy="40%" r="70%">
          <stop offset="0%" stopColor="var(--badge-coin-stop-start)" />
          <stop offset="45%" stopColor="var(--badge-coin-stop-mid)" />
          <stop offset="100%" stopColor="var(--badge-coin-stop-end)" />
        </radialGradient>
      </defs>
      <circle
        cx="20"
        cy="20"
        r="19"
        fill="var(--badge-coin-fill)"
        stroke="var(--badge-coin-stroke)"
        strokeWidth="1.5"
      />
      <path
        d="M20 9.5c5.8 0 10.5 4.7 10.5 10.5S25.8 30.5 20 30.5 9.5 25.8 9.5 20 14.2 9.5 20 9.5zm0 4c-3.6 0-6.5 2.9-6.5 6.5s2.9 6.5 6.5 6.5c1.7 0 3.3-.7 4.5-1.8l-2.2-2.2c-.6.6-1.4 1-2.3 1-1.8 0-3.2-1.4-3.2-3.2 0-1.8 1.4-3.2 3.2-3.2.9 0 1.7.4 2.3 1l2.2-2.2c-1.2-1.1-2.8-1.8-4.5-1.8z"
        fill="url(#caloGradient)"
        stroke="var(--badge-outline)"
        strokeWidth="0.8"
      />
    </svg>
  )
}

function EditAvatarIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      <path
        d="M3.8 13.7V16.8H6.9L15.9 7.8 12.8 4.7 3.8 13.7Z"
        fill="var(--avatar-edit-fill)"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
      <path
        d="m12.9 5.1 2.6 2.6"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
      <path
        d="M3.2 16.8h3.9"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
    </svg>
  )
}

const IDENTITY_FACE_MIN_HEIGHT = 140

export default function ProfileSidebar({
  user,
  profile,
  age,
  bmi,
  bmiStatus,
  tdee,
  recommendedCalories,
  onEditProfile,
  profileUpdateNotice,
  onPreferencesUpdate,
  walletSummary
}: ProfileSidebarProps) {
  const sidebarMeta = profile.sidebar_meta ?? null
  const walletMeta = sidebarMeta?.wallet ?? null
  const walletLinks = walletMeta?.links ?? null
  const walletOnboardingMessages = walletMeta?.onboarding?.messages ?? []
  const starsPurchaseBlocked =
    walletSummary?.flags?.stars_purchase_blocked ?? walletMeta?.flags?.stars_purchase_blocked ?? false
  const summaryTargets = walletSummary?.targets ?? walletMeta?.targets ?? null
  const walletPerksList = (walletSummary?.perks && walletSummary.perks.length > 0)
    ? walletSummary.perks
    : (walletMeta?.perks && walletMeta.perks.length > 0)
      ? walletMeta.perks
      : DEFAULT_WALLET_PERKS
  const recentTransactions = (walletSummary?.recent_transactions ?? walletMeta?.recent_transactions ?? []).slice(0, 3)
  const recentOrders = walletSummary?.recent_orders ?? walletMeta?.recent_orders ?? []
  const latestOrder = recentOrders.length > 0 ? recentOrders[0] : null
  const [showWallet, setShowWallet] = useState(() => Boolean(profile.wallet_settings?.show_wallet ?? walletMeta?.show_wallet));
  const walletHintId = useId();
  const avatarPickerId = useId();
  const profileUser = (profile as ProfileT & { user?: User | null }).user ?? null;
  const fallbackDisplay = (user?.username || profileUser?.username || '').trim() || 'Профиль';
  const firstName = (user?.first_name ?? profileUser?.first_name ?? '').trim();
  const lastName = (user?.last_name ?? profileUser?.last_name ?? '').trim();
  const middleName = profile.middle_name?.trim() ?? '';
  const fullNameParts = [lastName, firstName, middleName].filter(Boolean);
  const fullName = fullNameParts.length
    ? fullNameParts.join(' ')
    : [firstName, middleName, lastName].filter(Boolean).join(' ') || fallbackDisplay;
  const email = (user?.email ?? profileUser?.email ?? '').trim();
  const emailDisplay = email || 'Email не указан';
  const avatarUrl = user?.avatar_url ?? profileUser?.avatar_url ?? null;
  const initialsSource = fullName || fallbackDisplay;
  const initials = initialsSource.slice(0, 2).toUpperCase();
  const city = profile.city?.trim() || profileUser?.city?.trim() || user?.city?.trim() || '';
  const phoneRaw = user?.username || profileUser?.username || '';
  const phoneDisplay = phoneRaw ? formatPhoneInput(phoneRaw) : null;
  const experienceLevelKey = (profile.experience_level ?? 'newbie') as ExperienceLevel;
  const experienceDetails = experienceLevelMeta[experienceLevelKey] ?? experienceLevelMeta.newbie;
  const experienceLabel = profile.experience_level_display || experienceDetails.title;
  const metricsAgeDisplay = profile.metrics?.age_display ?? null;
  const sidebarAgeDisplay = metricsAgeDisplay ?? (age !== null ? `${age} лет` : null);
  const friendlyName = firstName || fullName || 'Вы';
  const [avatarState, setAvatarState] = useState<AvatarState>(() =>
    deriveAvatarState(profile.avatar_preferences ?? null, avatarUrl)
  )
  const [avatarPickerOpen, setAvatarPickerOpen] = useState(false)
  const [avatarError, setAvatarError] = useState<string | null>(null)
  const avatarPickerRef = useRef<HTMLDivElement | null>(null)
  const avatarButtonRef = useRef<HTMLButtonElement | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const identityInnerRef = useRef<HTMLDivElement | null>(null)
  const frontFaceRef = useRef<HTMLDivElement | null>(null)
  const backFaceRef = useRef<HTMLDivElement | null>(null)
  const [identityHeight, setIdentityHeight] = useState<number | null>(null)
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
  const starsTargetConfig = summaryTargets?.stars ?? null
  const caloTargetConfig = summaryTargets?.calo ?? null
  const starsTargetValue = starsTargetConfig?.target ?? DEFAULT_STARS_REWARD_TARGET
  const caloTargetValue = caloTargetConfig?.target ?? DEFAULT_CALO_REWARD_TARGET
  const starsTargetBalance = typeof starsTargetConfig?.balance === 'number'
    ? Math.max(0, starsTargetConfig.balance)
    : starsBalance
  const caloTargetBalance = typeof caloTargetConfig?.balance === 'number'
    ? Math.max(0, caloTargetConfig.balance)
    : Math.max(0, caloBalanceValue)
  const currentPreset = avatarState.kind === 'preset' ? getAvatarPreset(avatarState.id) ?? null : null
  const avatarImageSrc = getAvatarImageSrc(avatarState)
  const avatarClassName = `profile-sidebar__avatar${avatarImageSrc ? ' profile-sidebar__avatar--with-image' : ''}`
  const hasTelegramLink = Boolean(profile.telegram_id || user?.telegram_id)
  const starsRubEquivalent = hasStarsRate ? starsBalance * starsRateValue : null
  const caloRubEquivalent = hasCaloRate ? caloBalanceValue * caloRateValue : null
  const dailyBudgetDisplay = hasDailyBudget ? rubFormatter.format(dailyBudgetValue) : null
  const highlightMessages = Array.from(
    new Set(
      [
        profileUpdateNotice?.trim() || null,
        `${friendlyName}, режим «${experienceLabel}» активирован — двигаемся в комфортном темпе.`,
        experienceDetails.extra,
        'AI-ассистент мягко подскажет, когда сделать паузу и пополнить воду.',
        ...walletOnboardingMessages
      ].filter(Boolean) as string[]
    )
  )

  useEffect(() => {
    const preferred = Boolean(
      profile.wallet_settings?.show_wallet ?? walletMeta?.show_wallet
    )
    setShowWallet(prev => (prev === preferred ? prev : preferred))
  }, [profile.wallet_settings?.show_wallet, walletMeta?.show_wallet])

  useEffect(() => {
    const derived = deriveAvatarState(profile.avatar_preferences ?? null, avatarUrl)
    setAvatarState(prev => (isSameAvatarState(prev, derived) ? prev : derived))
  }, [profile.avatar_preferences, avatarUrl])

  const persistWalletState = useCallback(
    (next: boolean, previous: boolean) => {
      if (!onPreferencesUpdate) return
      onPreferencesUpdate({ wallet_settings: { show_wallet: next } }).catch(error => {
        console.error('Не удалось сохранить настройки кошелька', error)
        setShowWallet(previous)
      })
    },
    [onPreferencesUpdate]
  )

  const persistAvatarState = useCallback(
    (nextState: AvatarState, previousState: AvatarState) => {
      if (!onPreferencesUpdate) return
      const payload = avatarStateToPreferencesPayload(nextState)
      if (!payload) return
      onPreferencesUpdate(payload)
        .then(() => {
          setAvatarError(null)
        })
        .catch(error => {
          console.error('Не удалось сохранить образ', error)
          setAvatarError('Не удалось сохранить образ. Попробуйте ещё раз.')
          setAvatarState(previousState)
        })
    },
    [onPreferencesUpdate]
  )

  const basicIdentityItems: Array<{ label: string; value: string }> = [
    { label: 'Имя', value: firstName || '—' },
    { label: 'Фамилия', value: lastName || '—' }
  ]

  const contactInfoItems = [
    { label: 'Email', value: emailDisplay },
    phoneDisplay ? { label: 'Телефон', value: phoneDisplay } : null,
    city ? { label: 'Город', value: city } : null
  ].filter((item): item is { label: string; value: string } => Boolean(item))


  const climateItems = [
    {
      label: 'Курс',
      value: experienceDetails.course,
      hint: 'Обновляем по целям и дневнику. Вскоре подключим автоматические данные из API.'
    },
    {
      label: 'Температура',
      value: `~${experienceDetails.temperature}°C`,
      hint: city
        ? `Оценка для города ${city}. При подключении погодного API данные станут точными.`
        : 'Укажите город или подключите погодный API, чтобы видеть актуальную температуру.'
    },
    {
      label: 'Влажность',
      value: `${experienceDetails.humidity}%`,
      hint: 'Используем в расчётах гидратации — синхронизация с метеоданными уже в бэклоге.'
    },
    {
      label: 'Вода',
      value: experienceDetails.water,
      hint: 'В дальнейшем подключим API качества воды по регионам для более точных рекомендаций.'
    },
    {
      label: 'Микро/макро элементы',
      value: experienceDetails.micronutrients,
      hint: 'Добавим лабораторные данные и интеграции, чтобы формировать персональные наборы.'
    },
    {
      label: 'УФ влияние',
      value: experienceDetails.uv,
      hint: 'Планируем получать индекс УФ в реальном времени и строить защитные сценарии.'
    }
  ]

  const assistantMeta = sidebarMeta?.assistants ?? []
  type ServiceCard = {
    key: string
    state: 'active' | 'inactive'
    badge: string
    title: string
    description: string
    action: string
    href: string
    statusLabel?: string | null
    rawState?: string
  }

  const services: ServiceCard[] = assistantMeta.length
    ? assistantMeta.map(item => {
        const normalizedState = item.state === 'active' ? 'active' : 'inactive'
        return {
          key: item.key,
          state: normalizedState,
          rawState: item.state,
          badge: item.badge ?? item.status_label ?? (item.state === 'active' ? 'активно' : 'доступно'),
          title: item.title,
          description: item.description,
          action: item.action_label ?? (item.state === 'active' ? 'Открыть' : 'Подключить'),
          href: item.href ?? 'https://t.me/CaloIQ_bot',
          statusLabel: item.status_label
        }
      })
    : (() => {
        const aiConsultantActive = Boolean(profile.telegram_id || user?.telegram_id)
        const personalTrainerConnected = experienceLevelKey === 'pro' || experienceLevelKey === 'legend'
        return [
          {
            key: 'ai',
            state: aiConsultantActive ? 'active' : 'inactive',
            rawState: aiConsultantActive ? 'active' : 'inactive',
            badge: aiConsultantActive ? 'активно' : 'доступно',
            title: aiConsultantActive ? 'AI консультант подключён' : 'AI консультант ещё не активирован',
            description: aiConsultantActive
              ? 'Алгоритм обновляет меню и гидратацию каждые 6 часов и пишет ненавязчивые сообщения в @CaloIQ_bot.'
              : 'Оформите AI-консультанта — он будет подсказывать мягко и без спама, синхронизируясь с вашим расписанием.',
            action: aiConsultantActive ? 'Открыть сценарии' : 'Подключить AI-консультанта',
            href: 'https://t.me/CaloIQ_bot',
            statusLabel: aiConsultantActive ? 'Активен' : 'Подключите'
          },
          {
            key: 'trainer',
            state: personalTrainerConnected ? 'active' : 'inactive',
            rawState: personalTrainerConnected ? 'active' : 'inactive',
            badge: personalTrainerConnected ? 'подключено' : 'маркетплейс',
            title: personalTrainerConnected ? 'Личный тренер синхронизирован' : 'Личный тренер не выбран',
            description: personalTrainerConnected
              ? 'Ваш тренер недели: Полина Хак — рейтинг 4.9 из 5 (128 отзывов). План тренировок уже учтён в рекомендациях.'
              : 'Выберите тренера в маркетплейсе — покажем ТОП экспертов с рейтингами и отзывами, чтобы старт был комфортным.',
            action: personalTrainerConnected ? 'Перейти к программе' : 'Подобрать тренера',
            href: 'https://t.me/CaloIQ_bot?start=market',
            statusLabel: personalTrainerConnected ? 'Подключено' : 'Доступно'
          }
        ]
      })()

  const walletAriaLabel = showWallet ? 'Скрыть финансовую панель' : 'Показать финансовую панель'
  const walletHint = showWallet
    ? 'Скрыть финансовый блок и бонусы'
    : 'Разверните панель, чтобы увидеть бонусы, подписки и оплату'
  const starsTargetLeft = typeof starsTargetConfig?.left === 'number'
    ? Math.max(0, starsTargetConfig.left)
    : Math.max(starsTargetValue - starsTargetBalance, 0)
  const starProgress = typeof starsTargetConfig?.progress === 'number'
    ? Math.max(0, Math.min(100, starsTargetConfig.progress))
    : Math.min(
        100,
        starsTargetValue > 0 ? Math.round((starsTargetBalance / starsTargetValue) * 100) : 0
      )
  const caloTargetLeft = typeof caloTargetConfig?.left === 'number'
    ? Math.max(0, caloTargetConfig.left)
    : Math.max(caloTargetValue - caloTargetBalance, 0)
  const caloProgress = typeof caloTargetConfig?.progress === 'number'
    ? Math.max(0, Math.min(100, caloTargetConfig.progress))
    : Math.min(
        100,
        caloTargetValue > 0 ? Math.round((caloTargetBalance / caloTargetValue) * 100) : 0
      )
  const starsTargetTitle = (starsTargetConfig?.label?.trim() || DEFAULT_STARS_TARGET_LABEL)
  const caloTargetTitle = (caloTargetConfig?.label?.trim() || DEFAULT_CALO_TARGET_LABEL)
  const starTemplateReplacements = {
    left: integerFormatter.format(Math.max(0, Math.round(starsTargetLeft))),
    target: integerFormatter.format(Math.max(0, Math.round(starsTargetValue))),
    balance: integerFormatter.format(Math.max(0, Math.round(starsTargetBalance))),
    progress: starProgress.toString()
  }
  const caloTemplateReplacements = {
    left: decimalFormatter.format(Math.max(0, caloTargetLeft)),
    target: decimalFormatter.format(Math.max(0, caloTargetValue)),
    balance: decimalFormatter.format(Math.max(0, caloTargetBalance)),
    progress: caloProgress.toString()
  }
  const starProgressMessage = starsTargetLeft > 0
    ? applyTemplate(starsTargetConfig?.progress_message ?? null, DEFAULT_STARS_PROGRESS_TEMPLATE, starTemplateReplacements)
    : applyTemplate(starsTargetConfig?.completed_message ?? null, DEFAULT_STARS_COMPLETED_TEMPLATE, starTemplateReplacements)
  const caloProgressMessage = caloTargetLeft > 0
    ? applyTemplate(caloTargetConfig?.progress_message ?? null, DEFAULT_CALO_PROGRESS_TEMPLATE, caloTemplateReplacements)
    : applyTemplate(caloTargetConfig?.completed_message ?? null, DEFAULT_CALO_COMPLETED_TEMPLATE, caloTemplateReplacements)

  useEffect(() => {
    if (!showWallet) return
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        const previous = true
        setShowWallet(false)
        persistWalletState(false, previous)
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [showWallet, persistWalletState])

  useEffect(() => {
    if (!avatarPickerOpen) return
    const handleOutsideClick = (event: MouseEvent) => {
      const target = event.target as Node
      if (avatarPickerRef.current?.contains(target)) return
      if (avatarButtonRef.current?.contains(target)) return
      setAvatarPickerOpen(false)
    }
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setAvatarPickerOpen(false)
      }
    }
    document.addEventListener('mousedown', handleOutsideClick)
    window.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick)
      window.removeEventListener('keydown', handleEscape)
    }
  }, [avatarPickerOpen])

  useEffect(() => {
    if (showWallet) {
      setAvatarPickerOpen(false)
    }
  }, [showWallet])

  useIsomorphicLayoutEffect(() => {
    const frontEl = frontFaceRef.current
    const backEl = backFaceRef.current
    const containerEl = identityInnerRef.current

    if (!frontEl || !backEl) {
      return
    }

    const readHeight = (element: HTMLElement) => {
      const measured = element.scrollHeight
      return Math.max(Math.round(measured), IDENTITY_FACE_MIN_HEIGHT)
    }

    const syncFrontHeight = () => {
      const next = readHeight(frontEl)
      setIdentityHeight(prev => {
        if (showWallet) {
          return prev
        }
        return prev === next ? prev : next
      })
    }

    const syncBackHeight = () => {
      const next = readHeight(backEl)
      setIdentityHeight(prev => {
        if (!showWallet) {
          return prev
        }
        return prev === next ? prev : next
      })
    }

    if (containerEl) {
      const previousTransition = containerEl.style.transition
      containerEl.style.transition = 'none'
      containerEl.getBoundingClientRect()
      containerEl.style.transition = previousTransition
    }


    syncFrontHeight()
    syncBackHeight()

    if (typeof ResizeObserver === 'undefined') {
      return
    }

    const observer = new ResizeObserver(entries => {
      for (const entry of entries) {
        if (entry.target === frontEl) {
          syncFrontHeight()
        } else if (entry.target === backEl) {
          syncBackHeight()
        }
      }
    })

    observer.observe(frontEl)
    observer.observe(backEl)

    return () => {
      observer.disconnect()
    }
  }, [
    showWallet,
    avatarPickerOpen,
    emailDisplay,
    phoneDisplay,
    city,
    firstName,
    lastName,
    middleName,
    experienceLevelKey
  ])


  const handleWalletClick = (event: React.MouseEvent<HTMLDivElement>) => {
    const target = event.target as HTMLElement
    if (target.closest('a, button')) return
    const previous = showWallet
    const next = !previous
    setShowWallet(next)
    persistWalletState(next, previous)
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
      const previous = showWallet
      const next = !previous
      setShowWallet(next)
      persistWalletState(next, previous)
    }
    if (event.key === 'Escape' && showWallet) {
      event.preventDefault()
      const previous = showWallet
      setShowWallet(false)
      persistWalletState(false, previous)
    }
  }

  const handleAvatarButtonClick = () => {
    setAvatarPickerOpen(prev => !prev)
    setAvatarError(null)
  }

  const handlePresetClick = (presetId: string) => (event: React.MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation()
    const previous = avatarState
    const nextState: AvatarState = { kind: 'preset', id: presetId }
    setAvatarState(nextState)
    setAvatarPickerOpen(false)
    setAvatarError(null)
    persistAvatarState(nextState, previous)
  }

  const handleAvatarUploadClick = () => {
    setAvatarError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
      fileInputRef.current.click()
    }
  }

  const handleAvatarFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      setAvatarError('Можно загрузить только изображение')
      event.target.value = ''
      return
    }

    if (file.size > MAX_AVATAR_SIZE) {
      setAvatarError('Размер файла не должен превышать 2 МБ')
      event.target.value = ''
      return
    }

    const reader = new FileReader()
    const previous = avatarState
    reader.onload = () => {
      const result = reader.result
      if (typeof result === 'string') {
        const nextState: AvatarState = { kind: 'upload', dataUrl: result }
        setAvatarState(nextState)
        setAvatarPickerOpen(false)
        setAvatarError(null)
        persistAvatarState(nextState, previous)
      } else {
        setAvatarError('Не удалось прочитать файл изображения')
      }
    }
    reader.onerror = () => {
      setAvatarError('Не удалось загрузить файл изображения')
    }
    reader.readAsDataURL(file)
  }

  const handleAvatarReset = () => {
    const previous = avatarState
    const nextState: AvatarState = avatarUrl ? { kind: 'external', url: avatarUrl } : { kind: 'initials' }
    setAvatarState(nextState)
    setAvatarPickerOpen(false)
    setAvatarError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
    persistAvatarState(nextState, previous)
  }


  return (
    <aside className="profile-sidebar card">
      <div className="profile-sidebar__header">
        <div className="profile-sidebar__user">
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
            <div
              className={`profile-sidebar__identity-inner ${showWallet ? 'is-flipped' : ''}`}
              ref={identityInnerRef}
              style={showWallet && identityHeight !== null ? { height: `${identityHeight}px` } : undefined}
            >
              <div
                className="profile-sidebar__identity-face profile-sidebar__identity-face--front"
                ref={frontFaceRef}
              >
                <div className="profile-sidebar__identity-main">
                  <div className="profile-sidebar__avatar-wrapper" onClick={event => event.stopPropagation()}>
                    <div
                      className={avatarClassName}
                      style={avatarState.kind === 'preset' && currentPreset ? { background: currentPreset.gradient } : undefined}
                    >
                      {avatarImageSrc ? (
                        <img src={avatarImageSrc} alt={fullName} loading="lazy" />
                      ) : avatarState.kind === 'preset' && currentPreset ? (
                        <span className="profile-sidebar__avatar-emoji" aria-hidden="true">{currentPreset.emoji}</span>
                      ) : (
                        initials
                      )}
                      <span className="sr-only">Аватар профиля</span>
                    </div>
                    <button
                      type="button"
                      className="profile-sidebar__avatar-edit"
                      aria-controls={avatarPickerId}
                      aria-expanded={avatarPickerOpen}
                      aria-label="Сменить аватар"
                      onClick={handleAvatarButtonClick}
                      ref={avatarButtonRef}
                    >
                      <EditAvatarIcon className="profile-sidebar__avatar-edit-icon" />
                    </button>
                    {avatarPickerOpen && (
                      <div
                        id={avatarPickerId}
                        className="profile-sidebar__avatar-picker"
                        ref={avatarPickerRef}
                        role="dialog"
                        aria-modal="false"
                        onClick={event => event.stopPropagation()}
                      >
                        <div className="profile-sidebar__avatar-picker-header">Выберите образ</div>
                        <div className="profile-sidebar__avatar-options">
                          {AVATAR_PRESETS.map(preset => (
                            <button
                              key={preset.id}
                              type="button"
                              className={`profile-sidebar__avatar-option ${avatarState.kind === 'preset' && avatarState.id === preset.id ? 'is-active' : ''
                                }`}
                              style={{ background: preset.gradient }}
                              onClick={handlePresetClick(preset.id)}
                            >
                              <span className="profile-sidebar__avatar-option-emoji" aria-hidden="true">{preset.emoji}</span>
                              <span className="profile-sidebar__avatar-option-label">{preset.label}</span>
                            </button>
                          ))}
                        </div>
                        <div className="profile-sidebar__avatar-upload">
                          <button
                            type="button"
                            className="profile-sidebar__avatar-upload-button"
                            onClick={handleAvatarUploadClick}
                          >
                            Загрузить своё фото
                          </button>
                          <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/*"
                            className="sr-only"
                            onChange={handleAvatarFileChange}
                          />
                          {avatarError && <div className="profile-sidebar__avatar-error small">{avatarError}</div>}
                        </div>
                        <button type="button" className="profile-sidebar__avatar-reset" onClick={handleAvatarReset}>
                          Сбросить до стандартного вида
                        </button>
                      </div>
                    )}
                  </div>
                  <div className="profile-sidebar__user-info">
                    <div className="profile-sidebar__identity-header">
                      <div className="profile-sidebar__identity-name">{fullName}</div>
                      {onEditProfile && (
                        <button
                          type="button"
                          className="profile-sidebar__edit-link"
                          onClick={event => {
                            event.stopPropagation()
                            onEditProfile()
                          }}
                        >
                          Редактировать профиль
                        </button>
                      )}
                    </div>
                    <div className="profile-sidebar__identity-level">
                      <span className="profile-sidebar__identity-level-chip">{experienceLabel}</span>
                      <span className="profile-sidebar__identity-level-hint">{experienceDetails.summary}</span>
                    </div>
                  </div>
                </div>
                <div className="profile-sidebar__identity-status">
                  {highlightMessages.length > 0 && (
                    <ul className="profile-sidebar__identity-messages">
                      {highlightMessages.map(message => (
                        <li key={message} className="profile-sidebar__identity-message">{message}</li>
                      ))}
                    </ul>
                  )}
                  <div className="profile-sidebar__identity-services">
                    {services.map(service => (
                      <div
                        key={service.key}
                        className={`profile-sidebar__service-card ${service.state === 'active' ? 'is-active' : 'is-inactive'}`}
                      >
                        <div className="profile-sidebar__service-header">
                          <span className="profile-sidebar__service-badge">{service.badge}</span>
                          <span className="profile-sidebar__service-title">{service.title}</span>
                          {service.statusLabel && (
                            <span
                              className={`profile-sidebar__service-status profile-sidebar__service-status--${service.rawState ?? service.state}`}
                            >
                              {service.statusLabel}
                            </span>
                          )}
                        </div>
                        <p className="profile-sidebar__service-description">{service.description}</p>
                        <a
                          className="profile-sidebar__service-action"
                          href={service.href}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={event => event.stopPropagation()}
                        >
                          {service.action}
                        </a>
                      </div>
                    ))}
                  </div>
                  <span id={walletHintId} className="profile-sidebar__wallet-status small">{walletHint}</span>
                </div>
              </div>
              <div
                className="profile-sidebar__identity-face profile-sidebar__identity-face--back"
                ref={backFaceRef}
              >
                <div className="profile-sidebar__identity-back-overview">
                  <div className="profile-sidebar__identity-basics">
                    {basicIdentityItems.map(item => (
                      <div key={item.label} className="profile-sidebar__identity-basic">
                        <span className="profile-sidebar__identity-basic-label">{item.label}</span>
                        <span className="profile-sidebar__identity-basic-value">{item.value}</span>
                      </div>
                    ))}
                  </div>
                  <div className="profile-sidebar__identity-contacts profile-sidebar__identity-contacts--back">
                    {contactInfoItems.map(item => (
                      <div key={item.label} className="profile-sidebar__identity-contact">
                        <span className="profile-sidebar__identity-contact-label">{item.label}</span>
                        <span className="profile-sidebar__identity-contact-value">{item.value}</span>
                      </div>
                    ))}
                  </div>
                  <div className="profile-sidebar__identity-climate profile-sidebar__identity-climate--back">
                    {climateItems.map(item => (
                      <div key={item.label} className="profile-sidebar__climate-item">
                        <div className="profile-sidebar__climate-label">{item.label}</div>
                        <div className="profile-sidebar__climate-value">{item.value}</div>
                        <div className="profile-sidebar__climate-hint small">{item.hint}</div>
                      </div>
                    ))}
                  </div>
                </div>
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
                      href={hasTelegramLink
                        ? walletLinks?.topup ?? 'https://t.me/wallet?start=star-topup'
                        : walletLinks?.topup_onboarding ?? 'https://t.me/CaloIQ_bot'}
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
                      href={walletLinks?.pro ?? 'https://t.me/CaloIQ_bot?start=calopro'}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Оформить PRO
                    </a>
                  </div>
                </div>
                <div className="profile-sidebar__wallet-progress" aria-live="polite">
                  <div className="profile-sidebar__wallet-progress-item">
                    <div className="profile-sidebar__wallet-progress-header">
                      <span className="profile-sidebar__wallet-progress-title">{starsTargetTitle}</span>
                      <span className="profile-sidebar__wallet-progress-value">{starProgress}%</span>
                    </div>
                    <div className="profile-sidebar__wallet-progress-bar" aria-hidden="true">
                      <span style={{ width: `${starProgress}%` }} />
                    </div>
                    <p className="profile-sidebar__wallet-progress-hint small">{starProgressMessage}</p>
                  </div>
                  <div className="profile-sidebar__wallet-progress-item">
                    <div className="profile-sidebar__wallet-progress-header">
                      <span className="profile-sidebar__wallet-progress-title">{caloTargetTitle}</span>
                      <span className="profile-sidebar__wallet-progress-value">{caloProgress}%</span>
                    </div>
                    <div className="profile-sidebar__wallet-progress-bar" aria-hidden="true">
                      <span style={{ width: `${caloProgress}%` }} />
                    </div>
                    <p className="profile-sidebar__wallet-progress-hint small">{caloProgressMessage}</p>
                  </div>
                </div>
                {recentTransactions.length > 0 && (
                  <div className="profile-sidebar__wallet-history" aria-live="polite">
                    <div className="profile-sidebar__wallet-history-title">Последние операции</div>
                    <ul className="profile-sidebar__wallet-history-list">
                      {recentTransactions.map((tx: WalletTransactionRecord) => {
                        const isCredit = tx.direction === 'in'
                        const amountFormatter = tx.currency === 'stars' ? integerFormatter : decimalFormatter
                        const amountValue = Math.abs(Number(tx.amount) || 0)
                        const amountDisplay = `${isCredit ? '+' : '−'} ${amountFormatter.format(amountValue)} ${tx.currency === 'stars' ? 'Stars' : 'CaloCoin'}`
                        const created = new Date(tx.created_at)
                        const dateDisplay = Number.isNaN(created.getTime())
                          ? ''
                          : transactionDateFormatter.format(created)
                        const description = tx.description?.trim() || (isCredit ? 'Пополнение кошелька' : 'Списание средств')
                        return (
                          <li key={tx.id} className="profile-sidebar__wallet-history-item">
                            <div>
                              <div className="profile-sidebar__wallet-history-description">{description}</div>
                              <div className="profile-sidebar__wallet-history-date small">{dateDisplay}</div>
                            </div>
                            <div className={`profile-sidebar__wallet-history-amount ${isCredit ? 'is-credit' : 'is-debit'}`}>
                              {amountDisplay}
                            </div>
                          </li>
                        )
                      })}
                    </ul>
                  </div>
                )}
                {latestOrder && (
                  <div className="profile-sidebar__wallet-order small">
                    Последний заказ: <strong>{latestOrder.title}</strong> — {latestOrder.status_display}
                    {(() => {
                      const created = new Date(latestOrder.created_at)
                      if (Number.isNaN(created.getTime())) return null
                      return ` · ${transactionDateFormatter.format(created)}`
                    })()}
                  </div>
                )}

                <div className="profile-sidebar__wallet-meta small">
                  {starsPurchaseBlocked
                    ? 'Пополнение Stars недоступно: Telegram временно отключил покупки в вашем регионе.'
                    : hasTelegramLink
                      ? 'Telegram Mini App подключён — пополнения синхронизируются автоматически.'
                      : 'Подключите Telegram Mini App, чтобы пополнять Stars в один тап.'}
                </div>
                <div className="profile-sidebar__wallet-meta small">
                  {dailyBudgetDisplay
                    ? `Рекомендованный дневной бюджет: ${dailyBudgetDisplay}`
                    : 'Добавьте дневной бюджет, чтобы CaloCoin планировал траты.'}
                </div>
                <ul className="profile-sidebar__wallet-perks">
                  {walletPerksList.map(perk => (
                    <li key={perk}>{perk}</li>
                  ))}
                </ul>
                <div className="profile-sidebar__wallet-follow">
                  <a
                    className="profile-sidebar__wallet-action"
                    href={walletLinks?.bot ?? 'https://t.me/CaloIQ_bot'}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Открыть @CaloIQ_bot
                  </a>
                  <a
                    className="profile-sidebar__wallet-link"
                    href={walletLinks?.autopay ?? 'https://t.me/CaloIQ_bot?start=autopay'}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Настроить автопополнение и напоминания
                  </a>
                </div>
                <div className="profile-sidebar__wallet-insights small">
                  Переходите к ежедневным сценариям в <strong>@CaloIQ_bot</strong> и держите баланс в плюсе —
                  бот синхронизирует задачи и рекомендации с вашим профилем.
                </div>
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
          <div className="profile-sidebar__metric-value">{sidebarAgeDisplay ?? 'Укажите'}</div>
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
