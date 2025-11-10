import type { MarketPaginatedResponse } from './market'

export type MealTypeId =
  | 'breakfast'
  | 'second_breakfast'
  | 'brunch'
  | 'lunch'
  | 'snack'
  | 'dinner'
  | 'supper'

export interface MealPlanNutritionTotals {
  calories: number
  protein_g: number
  fat_g: number
  carbs_g: number
}

export interface MealPlanRecipeSnapshot extends MealPlanNutritionTotals {
  id: number
  title: string
  slug: string
  store_id: number
  store_name?: string | null
  store_slug?: string | null
  hero_image_url?: string | null
  preview_image_url?: string | null
  servings: number
  cooking_time_minutes: number
  price?: number | null
  price_stars?: number | null
  currency?: string | null
}

export interface MealPlanProductSnapshot extends MealPlanNutritionTotals {
  id: number
  title: string
  slug: string
  store_id: number
  store_name?: string | null
  store_slug?: string | null
  price: number
  currency: string
  image_url?: string | null
}

export interface MealPlanItemTotals {
  nutrition: MealPlanNutritionTotals
  total_nutrition: MealPlanNutritionTotals
}

export interface MealPlanItem extends MealPlanItemTotals {
  id: number
  meal_plan: number
  recipe?: number | null
  product?: number | null
  recipe_snapshot?: MealPlanRecipeSnapshot | null
  product_snapshot?: MealPlanProductSnapshot | null
  servings: number
  scheduled_for?: string | null
  meal_type?: string
  notes?: string | null
}

export interface MealPlanDailyTotals {
  date: string | null
  is_unscheduled: boolean
  totals: MealPlanNutritionTotals
}

export interface MealPlan {
  id: number
  user: number
  title: string
  description?: string | null
  start_date: string
  end_date?: string | null
  goal?: string | null
  tags?: string[] | null
  duration_days?: number | null
  is_published: boolean
  published_at?: string | null
  price_amount?: string | null
  price_currency: string
  price_stars?: number | null
  is_free?: boolean
  has_access?: boolean
  total_calories?: number | null
  calories_per_day?: number | null
  metadata: Record<string, any>
  created_at: string
  updated_at: string
  items: MealPlanItem[]
  nutrition_totals: MealPlanNutritionTotals
  daily_breakdown: MealPlanDailyTotals[]
}

export type MealPlanListResponse = MarketPaginatedResponse<MealPlan>

export interface MealPlanPurchaseResponse {
  plan: MealPlan
  wallet_transaction_id: number | null
  price_stars: string
}

export interface MealPlanQueryParams {
  scope?: 'owned' | 'public'
  from?: string
  to?: string
  published?: boolean
  page?: number
  page_size?: number
  search?: string
  goal?: string
  tag?: string
  tags?: string
  duration?: string
  duration_days?: string
  calories_min?: number
  calories_max?: number
  calories_per_day_min?: number
  calories_per_day_max?: number
  ordering?: string
}

export interface MealPlanCreatePayload {
  title: string
  description?: string
  start_date?: string
  end_date?: string | null
  is_published?: boolean
  price_amount?: number | null
  price_currency?: string
  metadata?: Record<string, any>
}

export interface MealPlanUpdatePayload extends MealPlanCreatePayload {}

export interface MealPlanItemPayload {
  meal_plan: number
  recipe?: number | null
  product?: number | null
  servings?: number
  scheduled_for?: string | null
  meal_type?: string | null
  notes?: string | null
}
