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
  isStaff: boolean
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
    is_staff: false,
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
    isStaff: Boolean((response.user as any).is_staff),
    profile,
  }
}

export async function fetchWallet(): Promise<WalletSheetData> {
  const profilePromise = fetchProfileFromApi()
  let starsAmount = 0
  let updatedAt = new Date().toISOString()
  let starsTransactions: WalletTransactionStub[] = []

  try {
    const { data } = await api.get<{
      balance: { amount: number; currency: string; updated_at?: string }
      transactions: Array<{
        id: number
        amount: number
        direction: 'in' | 'out'
        occurred_at: string
        description?: string | null
        source?: string | null
      }>
    }>('/me/stars/')

    starsAmount = data.balance?.amount ?? 0
    updatedAt = data.balance?.updated_at ?? updatedAt
    starsTransactions = (data.transactions ?? []).map(tx => ({
      id: String(tx.id),
      title: tx.description?.trim() || (tx.direction === 'in' ? 'Зачисление Stars' : 'Списание Stars'),
      amount: tx.amount,
      currency: 'stars' as const,
      direction: tx.direction,
      timestamp: tx.occurred_at,
      description: tx.source ?? undefined,
    }))
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      throw error
    }
    starsTransactions = []
  }

  const profileResponse = await profilePromise
  const calo = profileResponse.profile.calocoin_balance ?? 0

  return {
    balance: {
      stars: starsAmount,
      calo,
      updatedAt,
    },
    transactions: starsTransactions,
  }
}

export interface BotStarsBalance {
  amount: number
  currency: string
  updatedAt: string
}

export async function fetchBotStarsBalance(): Promise<BotStarsBalance> {
  const { data } = await api.get<{ balance: { amount: number; currency: string; updated_at?: string } }>(
    '/admin/stars/bot-balance/',
  )
  const updatedAt = data.balance?.updated_at ?? new Date().toISOString()
  return {
    amount: data.balance?.amount ?? 0,
    currency: data.balance?.currency ?? 'XTR',
    updatedAt,
  }
}