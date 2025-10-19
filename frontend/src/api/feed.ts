import api from './client'
import type { DealFeedItem, FeedCursorResponse, FeedTab, NewsFeedItem, RecipeFeedItem } from '../types/feed'

const FEED_ENDPOINT = '/v1/feed/'

const FEED_TYPE_MAP: Record<FeedTab, string> = {
  news: 'news',
  recipes: 'recipes',
  deals: 'deals',
}

type FeedResultMap = {
  news: NewsFeedItem
  recipes: RecipeFeedItem
  deals: DealFeedItem
}

export interface FetchFeedOptions<T extends FeedTab> {
  type: T
  cursor?: string | null
  filters?: Record<string, string | number | boolean | undefined>
}

function extractCursor(value?: string | null): string | null {
  if (!value) return null
  try {
    const url = new URL(value, typeof window !== 'undefined' ? window.location.origin : 'http://localhost')
    return url.searchParams.get('cursor')
  } catch (_error) {
    return value
  }
}

export async function fetchFeed<T extends FeedTab>({
  type,
  cursor,
  filters,
}: FetchFeedOptions<T>): Promise<{
  items: FeedResultMap[T][]
  nextCursor: string | null
  raw: FeedCursorResponse<FeedResultMap[T]>
}> {
  const params: Record<string, unknown> = { type: FEED_TYPE_MAP[type] }
  if (cursor) params.cursor = cursor
  if (filters) {
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params[key] = value
      }
    })
  }
  const { data } = await api.get<FeedCursorResponse<FeedResultMap[T]>>(FEED_ENDPOINT, { params })
  return {
    items: data.results,
    nextCursor: extractCursor(data.next ?? null),
    raw: data,
  }
}

export async function purchaseRecipe(recipeId: number) {
  const { data } = await api.post(`/recipes/${recipeId}/purchase/`)
  return data
}

export async function fetchPremiumContent(recipeId: number) {
  const { data } = await api.get<{ id: number; premium_content: string }>(`/recipes/${recipeId}/premium/`)
  return data
}