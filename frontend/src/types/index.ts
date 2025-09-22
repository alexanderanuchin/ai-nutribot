export type Sex = 'm' | 'f'
export type Activity = 'sedentary'|'light'|'moderate'|'high'|'athlete'
export type Goal = 'lose'|'maintain'|'gain'|'recomp'
export type ExperienceLevel = 'newbie'|'enthusiast'|'pro'|'legend'

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

export interface Targets {
  calories: number
  protein_g: number
  fat_g: number
  carbs_g: number
}

export interface PlanMeal {
  item_id: number
  title?: string
  qty: number
  time_hint: string
}

export interface MenuPlanResponse {
  targets: Targets
  plan: PlanMeal[]
}
