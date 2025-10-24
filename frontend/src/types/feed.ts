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
  body?: string | null
  title_orig?: string | null
  lead_orig?: string | null
  body_orig?: string | null
  lang?: string | null
  translated?: boolean
  translation_provider?: string | null
  source_name: string
  source_url: string
  published_at: string
  published_at_msk?: string | null
  published_at_localized?: string | null
  timezone_label?: string | null
  preview_image_url: string
  tonality: 'positive' | 'neutral' | 'negative'
  source_categories: string[]
  toxicity_score: string
  clickbait_score: string
  is_flagged: boolean
  ingested_at: string | null
  ingestion_source: string
  ingestion_rid: string
  ingestion_metadata: Record<string, unknown> | null
  created_at: string
  updated_at: string
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

export interface NewsRealtimeEventPayload {
  action: 'created' | 'updated' | 'moderated'
  article: NewsFeedItem
  meta?: {
    rid?: string | null
    source_id?: string | null
    article_id?: number | null
  }
}

export type FeedRealtimeEvent =
  | { group: 'feed.news'; tab: 'news'; payload: NewsRealtimeEventPayload }
  | { group: 'feed.recipes'; tab: 'recipes'; payload: Record<string, unknown> }
  | { group: 'feed.deals'; tab: 'deals'; payload: Record<string, unknown> }