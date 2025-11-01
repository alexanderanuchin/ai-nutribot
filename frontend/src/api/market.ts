import api from './client'
import type {
  MarketPaginatedResponse,
  MarketProduct,
  MarketRecipe,
  MarketResource,
  MarketSearchResponse,
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
  page?: number
  filters?: Record<string, string | number | boolean | undefined>
  search?: string
  pageSize?: number
}

function extractPage(value?: string | null): number | null {
  if (!value) return null
  try {
    const url = new URL(
      value,
      typeof window !== 'undefined' ? window.location.origin : 'http://localhost'
    )
    const pageParam = url.searchParams.get('page')
    if (!pageParam) return null
    const parsed = Number.parseInt(pageParam, 10)
    return Number.isNaN(parsed) ? null : parsed
  } catch (_error) {
    const fallback = Number.parseInt(value, 10)
    return Number.isNaN(fallback) ? null : fallback
  }
}

export async function fetchMarketCollection<T extends MarketResource>({
  resource,
  page,
  filters,
  search,
  pageSize,
}: FetchMarketCollectionOptions<T>): Promise<{
  items: MarketCollectionItem<T>[]
  nextPage: number | null
  raw: MarketPaginatedResponse<MarketCollectionItem<T>>
}> {
  const endpoint = MARKET_ENDPOINTS[resource]
  const params: Record<string, unknown> = {}
  const currentPage = typeof page === 'number' && page > 0 ? page : 1
  params.page = currentPage
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
  const { data } = await api.get<MarketPaginatedResponse<MarketCollectionItem<T>>>(endpoint, {
    params,
  })
  return {
    items: data.results,
    nextPage: extractPage(data.next ?? null),
    raw: data,
  }
}

export interface MarketSearchOptions {
  query?: string
  resource?: 'all' | MarketResource
  limit?: number
  filters?: Record<string, string | number | boolean | Array<string | number | boolean>>
}

export async function searchMarket(options: MarketSearchOptions): Promise<MarketSearchResponse> {
  const params: Record<string, unknown> = {}
  if (options.query && options.query.trim()) {
    params.q = options.query.trim()
  }
  if (options.resource) {
    params.resource = options.resource
  }
  if (options.limit) {
    params.limit = options.limit
  }
  if (options.filters) {
    Object.entries(options.filters).forEach(([key, value]) => {
      if (value === undefined || value === null) return
      if (Array.isArray(value)) {
        params[key] = value.join(',')
        return
      }
      params[key] = value
    })
  }
  const { data } = await api.get<MarketSearchResponse>('/v1/market/search/', { params })
  return data
}