import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, cleanup } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import { ThemeProvider } from '../../hooks/useTheme'
import { AuthProvider } from '../../providers/AuthProvider'
import BotBalanceBadge from './BotBalanceBadge'

vi.mock('../../api/api', () => ({
  fetchCurrentUser: vi.fn(),
  fetchBotStarsBalance: vi.fn(),
}))

import * as api from '../../api/api'

function renderWithProviders(children: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  })

  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <AuthProvider>{children}</AuthProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('BotBalanceBadge', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
  })

  it('shows bot balance for staff users', async () => {
    ;(api.fetchCurrentUser as vi.Mock).mockResolvedValue({
      id: 1,
      fullName: 'Staff User',
      email: 'staff@example.com',
      avatarUrl: undefined,
      role: 'legend',
      locale: 'ru',
      mode: 'Легенда',
      featureFlags: {},
      isStaff: true,
      profile: {
        sex: 'm',
        height_cm: 180,
        weight_kg: 80,
        activity_level: 'moderate',
        goal: 'maintain',
        allergies: [],
        exclusions: [],
      },
    })
    ;(api.fetchBotStarsBalance as vi.Mock).mockResolvedValue({
      amount: 2048,
      currency: 'XTR',
      updatedAt: '2024-11-01T10:00:00Z',
    })

    renderWithProviders(<BotBalanceBadge />)

    const badge = await screen.findByLabelText(/баланс бота/i)
    await waitFor(() => {
      expect(badge).toHaveTextContent(/XTR/)
    })
  })

  it('renders nothing for non-staff users', async () => {
    ;(api.fetchCurrentUser as vi.Mock).mockResolvedValue({
      id: 2,
      fullName: 'Regular User',
      email: 'user@example.com',
      avatarUrl: undefined,
      role: 'legend',
      locale: 'ru',
      mode: 'Легенда',
      featureFlags: {},
      isStaff: false,
      profile: {
        sex: 'm',
        height_cm: 175,
        weight_kg: 78,
        activity_level: 'moderate',
        goal: 'maintain',
        allergies: [],
        exclusions: [],
      },
    })
    ;(api.fetchBotStarsBalance as vi.Mock).mockResolvedValue({
      amount: 0,
      currency: 'XTR',
      updatedAt: '2024-11-01T10:00:00Z',
    })

    renderWithProviders(<BotBalanceBadge />)

    await waitFor(() => {
      expect(screen.queryByLabelText(/баланс бота/i)).not.toBeInTheDocument()
    })
  })
})