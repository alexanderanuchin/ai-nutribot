import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useBotStarsBalance } from './useBotStarsBalance'
import * as api from '../api/api'

describe('useBotStarsBalance', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('fetches bot balance when enabled', async () => {
    vi.spyOn(api, 'fetchBotStarsBalance').mockResolvedValue({
      amount: 512,
      currency: 'XTR',
      updatedAt: '2024-11-01T10:00:00Z',
    })

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useBotStarsBalance(true), { wrapper })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(api.fetchBotStarsBalance).toHaveBeenCalledTimes(1)
    expect(result.current.data?.amount).toBe(512)
    expect(result.current.data?.currency).toBe('XTR')
  })
})