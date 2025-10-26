import api from './client'
import type {
  AddProductToCartPayload,
  AddRecipeToPlanPayload,
  MarketCursorResponse,
  MarketProduct,
  MarketRecipe,
  MarketResource,
  MarketStore,
} from '../types/market'

const MARKET_ENDPOINTS: Record<MarketResource, string> = {
  recipes: '/v1/market/recipes/',
  products: '/v1/market/products/',
  stores: '/v1/market/stores/',
}

export type MarketCollectionItemMap = {
  recipes: MarketRecipe
  products: MarketProduct
  stores: MarketStore
}

export type MarketCollectionItem<T extends MarketResource> = MarketCollectionItemMap[T]

export interface FetchMarketCollectionOptions<T extends MarketResource> {
  resource: T
  cursor?: string | null
  filters?: Record<string, string | number | boolean | undefined>
  search?: string
  pageSize?: number
}

function extractCursor(value?: string | null): string | null {
  if (!value) return null
  try {
    const url = new URL(
      value,
      typeof window !== 'undefined' ? window.location.origin : 'http://localhost'
    )
    return url.searchParams.get('cursor')
  } catch (_error) {
    return value
  }
}

export async function fetchMarketCollection<T extends MarketResource>({
  resource,
  cursor,
  filters,
  search,
  pageSize,
}: FetchMarketCollectionOptions<T>): Promise<{
  items: MarketCollectionItem<T>[]
  nextCursor: string | null
  raw: MarketCursorResponse<MarketCollectionItem<T>>
}> {
  const endpoint = MARKET_ENDPOINTS[resource]
  const params: Record<string, unknown> = {}
  if (cursor) params.cursor = cursor
  if (search && search.trim()) {
    params.search = search.trim()
  }
  if (pageSize) {
    params.page_size = pageSize
  }
  if (filters) {
    Object.entries(filters).forEach(([key, value]) => {
      if (value === undefined || value === null) return
      if (typeof value === 'string' && value.trim() === '') return
      params[key] = value
    })
  }
  const { data } = await api.get<MarketCursorResponse<MarketCollectionItem<T>>>(endpoint, { params })
  return {
    items: data.results,
    nextCursor: extractCursor(data.next ?? null),
    raw: data,
  }
}

export async function addProductToCart(payload: AddProductToCartPayload): Promise<void> {
  await api.post('/v1/market/cart/', payload)
}

export async function addRecipeToPlan(payload: AddRecipeToPlanPayload): Promise<void> {
  await api.post('/v1/market/plan/', payload)
}