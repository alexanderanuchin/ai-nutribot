import type { LucideIcon } from 'lucide-react'
import {
  Wallet2Icon,
  BellIcon,
  FlameKindlingIcon,
  ChefHatIcon,
  ShoppingBagIcon,
  DumbbellIcon,
  HeartPulseIcon,
  BotIcon,
  RadarIcon,
  OrbitIcon,
  CableIcon,
  FileTextIcon,
  NewspaperIcon,
  PlusCircleIcon,
  SearchIcon,
  UserRoundIcon,
  Wallet2Icon,
} from 'lucide-react'

export type FeatureFlag =
  | 'aiAssistant'
  | 'aiCurator'
  | 'nutritionAnalytics'
  | 'mealConstructor'
  | 'marketplace'
  | 'training'
  | 'recovery'
  | 'riskForecast'
  | 'gadgets'
  | 'integrations'
  | 'documents'

export type Role = 'legend' | 'member' | 'coach' | 'admin' | 'guest'

export interface NavItem {
  id: string
  label: string
  description?: string
  path?: string
  icon: LucideIcon
  badge?: string
  featureFlag?: FeatureFlag
  roles?: Role[]
  children?: NavItem[]
  quickActions?: Array<{ id: string; label: string; path?: string; command?: string; description?: string }>
}

export interface NavSection {
  id: string
  label: string
  items: NavItem[]
  roles?: Role[]
  featureFlag?: FeatureFlag
}

export const PRIMARY_NAVIGATION: NavItem[] = [
  {
    id: 'feed',
    label: 'Лента',
    path: '/feed',
    icon: NewspaperIcon,
    description: 'Новости, рецепты и акции',
  },
  {
    id: 'billing',
    label: 'Кошелёк',
    path: '/billing',
    icon: Wallet2Icon,
    description: 'Управление кошельком и подписками',
  },
  {
    id: 'compose',
    label: 'Добавить',
    path: '/compose',
    icon: PlusCircleIcon,
    description: 'Создать рецепт или предложение',
  },
  {
    id: 'notifications',
    label: 'Уведомления',
    path: '/notifications',
    icon: BellIcon,
    description: 'Лента уведомлений и событий',
  },
  {
    id: 'profile',
    label: 'Профиль',
    path: '/profile',
    icon: UserRoundIcon,
    description: 'Настройки и персональные данные',
  },
]

export const SECONDARY_NAVIGATION: NavSection[] = [
  {
    id: 'nutrition',
    label: 'Питание и калории',
    items: [
      {
        id: 'nutrition-analytics',
        label: 'Аналитика',
        path: '/nutrition/analytics',
        icon: FlameKindlingIcon,
        featureFlag: 'nutritionAnalytics',
        description: 'Отслеживание калорийности и нутриентов',
      },
      {
        id: 'meal-builder',
        label: 'Конструктор рационов',
        path: '/nutrition/builder',
        icon: ChefHatIcon,
        featureFlag: 'mealConstructor',
        description: 'Создавайте рацион с AI‑подсказками',
      },
    ],
  },
  {
    id: 'delivery',
    label: 'Заказ и доставка',
    items: [
      {
        id: 'marketplace',
        label: 'Маркетплейс здоровой еды',
        path: '/marketplace',
        icon: ShoppingBagIcon,
        featureFlag: 'marketplace',
        description: 'Выбор и доставка здоровых блюд',
      },
    ],
  },
  {
    id: 'fitness',
    label: 'Фитнес и восстановление',
    items: [
      {
        id: 'training',
        label: 'Программы тренировок',
        path: '/fitness/training',
        icon: DumbbellIcon,
        featureFlag: 'training',
        description: 'План тренировок по режиму «Легенда»',
      },
      {
        id: 'recovery',
        label: 'Мониторинг восстановления',
        path: '/fitness/recovery',
        icon: HeartPulseIcon,
        featureFlag: 'recovery',
        description: 'HRV, сон и прогресс восстановления',
      },
    ],
  },
  {
    id: 'intelligence',
    label: 'Интеллект и автоматизация',
    items: [
      {
        id: 'ai-curator',
        label: 'AI‑куратор',
        path: '/intelligence/curator',
        icon: BotIcon,
        featureFlag: 'aiCurator',
        description: 'Персональные подсказки и ассистент',
      },
      {
        id: 'risk-forecast',
        label: 'Прогноз рисков',
        path: '/intelligence/risk',
        icon: RadarIcon,
        featureFlag: 'riskForecast',
        description: 'Прогнозы рисков и рекомендации',
      },
    ],
  },
  {
    id: 'ecosystem',
    label: 'Экосистема',
    items: [
      {
        id: 'gadgets',
        label: 'Гаджеты',
        path: '/ecosystem/gadgets',
        icon: OrbitIcon,
        featureFlag: 'gadgets',
        description: 'Подключённые устройства и сенсоры',
      },
      {
        id: 'integrations',
        label: 'Интеграции',
        path: '/ecosystem/integrations',
        icon: CableIcon,
        featureFlag: 'integrations',
        description: 'Свяжите CaloIQ с другими сервисами',
      },
    ],
  },
  {
    id: 'documents',
    label: 'Документы и политики',
    items: [
      {
        id: 'documents-policies',
        label: 'Документы',
        path: '/documents',
        icon: FileTextIcon,
        featureFlag: 'documents',
        description: 'Политики обработки данных и оферты',
      },
    ],
  },
]

export const COMMAND_ACTIONS = [
  {
    id: 'generate-plan',
    label: 'Сгенерировать план',
    path: '/plan/generate',
    description: 'AI предложит план на неделю',
  },
  {
    id: 'open-builder',
    label: 'Открыть конструктор',
    path: '/nutrition/builder',
    description: 'Соберите рацион из каталога блюд',
  },
  {
    id: 'topup-wallet',
    label: 'Пополнить кошелёк',
    path: '/billing/topup',
    description: 'Добавьте Stars или Calo на баланс',
  },
  {
    id: 'connect-telegram',
    label: 'Подключить Telegram',
    path: '/profile/integrations/telegram',
    description: 'Синхронизация с Telegram Stars',
  },
] as const

export type CommandAction = typeof COMMAND_ACTIONS[number]