export type MarketResource = 'recipes' | 'products' | 'stores'

export interface MarketRecipe {
  id: number
  store: number
  store_name: string
  store_slug: string
  store_city: string
  store_logo_url?: string | null
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
  metadata?: Record<string, unknown>
}

export interface MarketProduct {
  id: number
  store: number
  store_name: string
  store_slug: string
  store_city: string
  store_logo_url?: string | null
  store_is_verified: boolean
  store_owner_id: number
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
  inventory_available: number
  inventory_quantity: number
  inventory_reserved: number
  metadata?: Record<string, unknown>
  tags?: string[] | null
  nutrition?: Record<string, unknown>
}

export interface MarketStore {
  id: number
  slug: string
  owner: number
  owner_username: string
  owner_full_name?: string | null
  name: string
  city: string
  description?: string | null
  is_active: boolean
  is_verified: boolean
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
  metadata?: Record<string, unknown>
}

export interface MarketPaginatedResponse<TItem> {
  count: number
  page: number
  page_size: number
  next: string | null
  previous: string | null
  results: TItem[]
}

export type MarketRealtimeAction =
  | 'created'
  | 'updated'
  | 'published'
  | 'verified'
  | 'status_changed'
  | string

export interface MarketRealtimePayloadBase {
  action?: MarketRealtimeAction
  fresh_count?: number
  highlight_ids?: number[]
  generated_at?: string
  meta?: Record<string, unknown>
}

export interface MarketProductRealtimePayload extends MarketRealtimePayloadBase {
  product?: MarketProduct
}

export interface MarketRecipeRealtimePayload extends MarketRealtimePayloadBase {
  recipe?: MarketRecipe
}

export interface MarketStoreRealtimePayload extends MarketRealtimePayloadBase {
  store?: MarketStore
}

export interface MarketRealtimePayloadMap {
  products: MarketProductRealtimePayload
  recipes: MarketRecipeRealtimePayload
  stores: MarketStoreRealtimePayload
}

export type MarketRealtimeEvent<T extends MarketResource = MarketResource> = {
  group: `market.${T}`
  resource: T
  payload: MarketRealtimePayloadMap[T]
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