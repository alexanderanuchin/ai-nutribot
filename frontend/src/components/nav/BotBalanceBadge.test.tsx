import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, cleanup, act, type RenderResult } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import { ThemeProvider } from '../../hooks/useTheme'
import { tokenStore } from '../../utils/storage'
import BotBalanceBadge from './BotBalanceBadge'
import { createMockAuthContextValue } from '../../test/mocks/auth'

vi.mock('../../providers/AuthProvider', async () => {
  const { createContext, useContext } = await import('react')
  const { createMockAuthContextValue } = await import('../../test/mocks/auth')
  const state = { current: createMockAuthContextValue() }
  const AuthContext = createContext(state.current)
  const AuthProvider = ({ children }: { children: any }) => (
    <AuthContext.Provider value={state.current}>{children}</AuthContext.Provider>
  )

  return {
    AuthProvider,
    useAuthContext: () => useContext(AuthContext),
    __setMockAuthValue: (value: ReturnType<typeof createMockAuthContextValue>) => {
      state.current = value
    },
  }
})

import * as AuthModule from '../../providers/AuthProvider'

const AuthProvider = (AuthModule as any).AuthProvider as typeof import('../../providers/AuthProvider').AuthProvider
const setMockAuthValue = (AuthModule as any).__setMockAuthValue as (
  value: ReturnType<typeof createMockAuthContextValue>,
) => void

vi.mock('../../api/api', () => ({
  fetchCurrentUser: vi.fn(),
  fetchBotStarsBalance: vi.fn(),
}))

import * as api from '../../api/api'

async function renderWithProviders(children: ReactNode): Promise<RenderResult> {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  })

  tokenStore.access = 'test-access-token'
  tokenStore.refresh = 'test-refresh-token'

  const result = render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <AuthProvider>{children}</AuthProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  )

  await act(async () => {
    await Promise.resolve()
  })

  return result
}

describe('BotBalanceBadge', () => {
  beforeEach(() => {
    setMockAuthValue(createMockAuthContextValue())
    vi.clearAllMocks()
  })

  afterEach(() => {
    tokenStore.clear()
    cleanup()
  })

  it('shows bot balance for staff users', async () => {
    setMockAuthValue(
      createMockAuthContextValue({
        user: {
          id: 1,
          fullName: 'Staff User',
          email: 'staff@example.com',
          isStaff: true,
        },
      }),
    )
    ;(api.fetchBotStarsBalance as vi.Mock).mockResolvedValue({
      amount: 2048,
      currency: 'XTR',
      updatedAt: '2024-11-01T10:00:00Z',
    })

    await renderWithProviders(<BotBalanceBadge />)

    const badge = await screen.findByLabelText(/баланс бота/i)
    await waitFor(() => {
      expect(badge).toHaveTextContent(/XTR/)
    })
  })

  it('renders nothing for non-staff users', async () => {
    setMockAuthValue(
      createMockAuthContextValue({
        user: {
          id: 2,
          fullName: 'Regular User',
          email: 'user@example.com',
          isStaff: false,
        },
      }),
    )
    ;(api.fetchBotStarsBalance as vi.Mock).mockResolvedValue({
      amount: 0,
      currency: 'XTR',
      updatedAt: '2024-11-01T10:00:00Z',
    })

    await renderWithProviders(<BotBalanceBadge />)

    await waitFor(() => {
      expect(screen.queryByLabelText(/баланс бота/i)).not.toBeInTheDocument()
    })
  })
})