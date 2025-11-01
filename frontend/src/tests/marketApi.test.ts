import { afterEach, describe, expect, test, vi } from 'vitest'

import { api } from '../api/client'
import { fetchMarketCollection } from '../api/market'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('fetchMarketCollection', () => {
  test('requests explicit page and page_size parameters', async () => {
    const response = {
      count: 24,
      page: 2,
      page_size: 12,
      next: 'https://example.test/v1/market/products/?page=3&page_size=12',
      previous: 'https://example.test/v1/market/products/?page=1&page_size=12',
      results: [],
    }

    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data: response } as any)

    const result = await fetchMarketCollection({
      resource: 'products',
      page: 2,
      pageSize: 12,
      search: 'чай',
    })

    expect(getSpy).toHaveBeenCalledWith('/v1/market/products/', {
      params: {
        page: 2,
        page_size: 12,
        search: 'чай',
      },
    })
    expect(result.nextPage).toBe(3)
    expect(result.raw.page).toBe(2)
    expect(result.raw.page_size).toBe(12)
  })

  test('defaults to the first page when none is provided', async () => {
    const response = {
      count: 6,
      page: 1,
      page_size: 10,
      next: null,
      previous: null,
      results: [],
    }

    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data: response } as any)

    await fetchMarketCollection({
      resource: 'stores',
      pageSize: 10,
    })

    expect(getSpy).toHaveBeenCalledWith('/v1/market/stores/', {
      params: {
        page: 1,
        page_size: 10,
      },
    })
  })
})
