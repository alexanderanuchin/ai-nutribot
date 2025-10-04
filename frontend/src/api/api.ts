import axios from 'axios'
import api from './client'
import type { MeResponse, Profile } from '../types'

export interface WalletBalance {
  stars: number
  calo: number
  updatedAt: string
}

export interface WalletTransactionStub {
  id: string
  title: string
  amount: number
  currency: 'stars' | 'calo'
  direction: 'in' | 'out'
  timestamp: string
  description?: string
}

export interface WalletSheetData {
  balance: WalletBalance
  transactions: WalletTransactionStub[]
}

export interface CurrentUserProfile {
  id: number
  fullName: string
  email: string
  avatarUrl?: string
  role: string
  locale: string
  mode: string
  featureFlags: Record<string, boolean>
  profile: Profile
}

const FALLBACK_RESPONSE: MeResponse = {
  user: {
    id: 101,
    username: 'a.legend',
    email: 'alexander.anuchin@example.com',
    first_name: 'Alexander',
    last_name: 'Anuchin',
    avatar_url: 'https://avatars.dicebear.com/api/initials/AA.svg',
    city: 'Moscow',
    profile: undefined,
  },
  profile: {
    sex: 'm',
    height_cm: 184,
    weight_kg: 86,
    activity_level: 'athlete',
    goal: 'recomp',
    allergies: [],
    exclusions: ['sugar'],
    telegram_stars_balance: 4280,
    calocoin_balance: 17650,
    experience_level: 'legend',
    experience_level_display: 'Легенда',
    metrics: {
      age: 36,
      age_display: '36',
      bmi: 24.3,
      bmi_status: 'Норма',
      bmr: 1900,
      tdee: 2750,
      recommended_calories: 2500,
      macros: [
        { label: 'Белки', grams: 180, ratio: 30, color: '#38bdf8' },
        { label: 'Жиры', grams: 90, ratio: 25, color: '#f97316' },
        { label: 'Углеводы', grams: 320, ratio: 45, color: '#facc15' },
      ],
    },
    wallet_settings: { show_wallet: true },
    sidebar_meta: null,
  },
  metrics: null,
}

async function fetchProfileFromApi(): Promise<MeResponse> {
  try {
    const { data } = await api.get<MeResponse>('/users/me/profile/')
    return data
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      throw error
    }
    return FALLBACK_RESPONSE
  }
}

export async function fetchCurrentUser(): Promise<CurrentUserProfile> {
  const response = await fetchProfileFromApi()
  const fullName = [response.user.first_name, response.user.last_name].filter(Boolean).join(' ').trim() || response.user.username

  const profile: Profile = {
    ...response.profile,
    experience_level_display:
      response.profile.experience_level_display ||
      (response.profile.experience_level === 'legend' ? 'Легенда' : response.profile.experience_level ?? ''),
  }

  return {
    id: response.user.id,
    fullName,
    email: response.user.email,
    avatarUrl: response.user.avatar_url ?? undefined,
    role: profile.experience_level ?? 'legend',
    locale: 'ru',
    mode: profile.experience_level_display ?? 'Легенда',
    featureFlags: {
      aiAssistant: true,
      aiCurator: true,
      marketplace: true,
      training: true,
      recovery: true,
      gadgets: true,
      integrations: true,
      riskForecast: true,
      documents: true,
    },
    profile,
  }
}

export async function fetchWallet(): Promise<WalletSheetData> {
  const response = await fetchProfileFromApi()
  const now = new Date().toISOString()
  const stars = response.profile.telegram_stars_balance ?? 0
  const calo = response.profile.calocoin_balance ?? 0

  const transactions: WalletTransactionStub[] = [
    {
      id: 'tx-1',
      title: 'AI-куратор',
      amount: 320,
      currency: 'stars',
      direction: 'out',
      timestamp: now,
      description: 'Оплата ассистента за неделю',
    },
    {
      id: 'tx-2',
      title: 'Пополнение кошелька',
      amount: 5000,
      currency: 'calo',
      direction: 'in',
      timestamp: now,
      description: 'Перевод из CaloBank',
    },
  ]

  return {
    balance: {
      stars,
      calo,
      updatedAt: now,
    },
    transactions,
  }
}