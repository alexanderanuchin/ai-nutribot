export type MarketResource = 'recipes' | 'products' | 'stores'

export interface MarketRecipe {
  id: number
  title: string
  subtitle?: string | null
  description?: string | null
  calories: number
  protein_g: number
  fat_g: number
  carbs_g: number
  cook_time_minutes: number
  price?: number | null
  currency?: string | null
  rating?: number | null
  rating_count?: number | null
  hero_image_url?: string | null
  preview_image_url?: string | null
  tags?: string[] | null
  is_premium?: boolean
  is_in_plan?: boolean
}

export interface MarketProduct {
  id: number
  title: string
  subtitle?: string | null
  description?: string | null
  price: number
  currency: string
  unit?: string | null
  price_original?: number | null
  discount_percent?: number | null
  image_url?: string | null
  brand?: string | null
  badges?: string[] | null
  rating?: number | null
  rating_count?: number | null
  is_in_cart?: boolean
  available?: boolean
}

export interface MarketStore {
  id: number
  name: string
  city: string
  description?: string | null
  rating?: number | null
  rating_count?: number | null
  delivery_eta_minutes?: number | null
  delivery_price?: number | null
  currency?: string | null
  is_online?: boolean
  hero_image_url?: string | null
  logo_url?: string | null
  tags?: string[] | null
  link_url?: string | null
}

export interface MarketPaginatedResponse<TItem> {
  count: number
  page: number
  page_size: number
  next: string | null
  previous: string | null
  results: TItem[]
}

export interface MarketRealtimePayload {
  fresh_count?: number
  highlight_ids?: number[]
  generated_at?: string
}

export interface MarketRealtimeEvent {
  group: `market.${MarketResource}`
  resource: MarketResource
  payload: MarketRealtimePayload
}

export interface MarketCartSubmissionPayload {
  product_id: number
  quantity?: number
}

export interface MarketCartItemSummary {
  id: number
  product_id: number
  quantity: number
  price_snapshot: string
}

export interface MarketCartSubmissionResponse {
  status: "created" | "updated" | "removed"
  cart: {
    id: number
    store_id: number
    currency: string
    items_count: number
    items_quantity: number
  }
  item: MarketCartItemSummary | null
}

export interface MarketPlanSubmissionPayload {
  recipe_id: number
  servings?: number
}

export interface MarketPlanItemSummary {
  id: number
  recipe_id: number
  servings: number
}

export interface MarketPlanSubmissionResponse {
  status: "created" | "updated" | "removed"
  plan: {
    id: number
    title: string
    items_count: number
    total_servings: number
  }
  item: MarketPlanItemSummary | null
}

export interface MarketQuickFilter {
  id: string
  label: string
  param: string
  value: string | number | boolean
  resource: MarketResource
}

export interface MarketSearchResultItem {
  resource: MarketResource
  id: number
  title: string
  subtitle?: string | null
  description?: string | null
  tags?: string[] | null
  metrics?: Record<string, unknown>
  preview?: Record<string, unknown>
}

export interface MarketSearchResponse {
  query: string
  resource: 'all' | MarketResource
  total: number
  results: MarketSearchResultItem[]
  facets: Record<string, Array<Record<string, unknown>>>
  suggestions: {
    quick_filters?: MarketQuickFilter[]
    popular?: string[]
    recent?: string[]
    [key: string]: unknown
  }
}