export type Sex = 'm' | 'f'
export type Activity = 'sedentary'|'light'|'moderate'|'high'|'athlete'
export type Goal = 'lose'|'maintain'|'gain'|'recomp'
export type ExperienceLevel = 'newbie'|'enthusiast'|'pro'|'legend'
export interface MacroBreakdown {
  label: string
  grams: number
  ratio: number
  color?: string | null
}

export interface ProfileMetrics {
  age: number | null
  age_display: string | null
  bmi: number | null
  bmi_status: string | null
  bmr: number | null
  tdee: number | null
  recommended_calories: number | null
  macros: MacroBreakdown[]
}

export type AvatarPreferenceKind = 'initials' | 'preset' | 'upload'

export interface AvatarPreferences {
  kind: AvatarPreferenceKind
  preset_id?: string | null
  data_url?: string | null
}

export type AvatarPreferenceInput =
  | { kind: 'initials' }
  | { kind: 'preset'; preset_id: string }
  | { kind: 'upload'; data_url: string }

export interface WalletSettings {
  show_wallet: boolean
}

export interface WalletSettingsInput {
  show_wallet?: boolean
}
export type FeatureState = 'active' | 'inactive' | 'onboarding'

export interface ProfileSidebarFeature {
  key: string
  title: string
  description: string
  href?: string | null
  state: FeatureState
  status_label: string
  action_label?: string | null
  badge?: string | null
}

export interface ProfileWalletLinks {
  bot: string
  topup: string
  topup_onboarding: string
  autopay: string
  pro: string
}

export interface ProfileWalletOnboarding {
  needs_balance: boolean
  needs_city: boolean
  messages: string[]
}

export interface ProfileSidebarWalletMeta {
  show_wallet: boolean
  links: ProfileWalletLinks
  onboarding: ProfileWalletOnboarding
}

export interface ProfileSidebarMeta {
  wallet: ProfileSidebarWalletMeta
  assistants: ProfileSidebarFeature[]
  services: ProfileSidebarFeature[]
}

export interface Profile {
  id?: number
  sex: Sex
  birth_date?: string | null
  height_cm: number
  weight_kg: number
  body_fat_pct?: number | null
  activity_level: Activity
  goal: Goal
  allergies: string[]
  exclusions: string[]
  daily_budget?: number | null
  telegram_id?: number | null
  city?: string
  telegram_stars_balance?: number
  telegram_stars_rate_rub?: number | null
  calocoin_balance?: number | null
  calocoin_rate_rub?: number | null
  middle_name?: string
  experience_level?: ExperienceLevel
  experience_level_display?: string
  metrics?: ProfileMetrics | null
  avatar_preferences?: AvatarPreferences | null
  wallet_settings?: WalletSettings | null
  sidebar_meta?: ProfileSidebarMeta | null
}

export interface User {
  id: number
  username: string
  email: string
  first_name?: string
  last_name?: string
  avatar_url?: string | null
  city?: string
  telegram_id?: number | null
  profile?: Profile
}
export interface MeResponse {
  user: User
  profile: Profile
  metrics: ProfileMetrics | null
}
export interface Targets {
  calories: number
  protein_g: number
  fat_g: number
  carbs_g: number
}
export interface MealNutrients {
  calories: number
  protein: number
  fat: number
  carbs: number
}

export type PlanStatus = 'generated' | 'accepted' | 'rejected' | 'recalculated' | 'processing'

export interface PlanMeal {
  id: number
  item_id: number
  title?: string
  qty: number
  time_hint: string
  price?: number
  tags?: string[]
  nutrients?: MealNutrients
  user_note?: string
}

export interface MenuPlanResponse {
  id: number
  plan_id: number
  date: string
  created_at: string
  status: PlanStatus
  status_display: string
  provider?: string
  targets: Targets
  plan: PlanMeal[]
}
