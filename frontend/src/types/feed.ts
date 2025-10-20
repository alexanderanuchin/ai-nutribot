export type FeedTab = 'news' | 'recipes' | 'deals'

export interface FeedTag {
  id: number
  name: string
  slug: string
  kind: 'generic' | 'news' | 'recipe' | 'deal'
}

export interface FeedCursorResponse<T> {
  next?: string | null
  previous?: string | null
  results: T[]
}

export interface NewsFeedItem {
  id: number
  source_id: string
  title: string
  lead: string
  source_name: string
  source_url: string
  published_at: string
  preview_image_url: string
  tags: FeedTag[]
}

export interface RecipeFeedItem {
  id: number
  slug: string
  status: 'draft' | 'moderation' | 'published' | 'hidden'
  title: string
  short_description: string
  description: string
  hero_image: string
  gallery: string[]
  cook_time_minutes: number
  difficulty: 'easy' | 'medium' | 'hard'
  calories: string
  protein: string
  fat: string
  carbs: string
  allergens: string[]
  diet_tags: string[]
  base_content: string
  is_premium: boolean
  price: string
  currency: string
  rating: string
  rating_count: number
  purchases_count: number
  tags: FeedTag[]
  steps: Array<{ id: number; order: number; text: string; media_url: string }>
  reaction_summary: Record<string, number>
  is_purchased: boolean
}

export interface DealFeedItem {
  id: number
  external_id: string
  title: string
  product_name: string
  network: string
  city: string
  address: string
  is_online: boolean
  price_before: string
  price_after: string
  discount_percent: string
  valid_until: string
  offer_url: string
  image_url: string
  tags: FeedTag[]
}

export type FeedItem = NewsFeedItem | RecipeFeedItem | DealFeedItem

export interface FeedRealtimeEvent {
  group: 'feed.news' | 'feed.recipes' | 'feed.deals'
  tab: FeedTab
  payload: Record<string, unknown>
}