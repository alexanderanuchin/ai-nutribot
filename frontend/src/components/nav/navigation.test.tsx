import type { ReactNode } from 'react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, act, type RenderResult } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AppNavbar from './AppNavbar'
import MobileTabBar from './MobileTabBar'
import NavDrawer from './NavDrawer'
import CommandPanel from './CommandPanel'
import { ThemeProvider } from '../../hooks/useTheme'
import { CommandPaletteProvider } from '../../hooks/useCommandPalette'
import { tokenStore } from '../../utils/storage'
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
    __setMockAuthValue: (value: unknown) => {
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
  fetchCurrentUser: vi.fn(async () => ({
    id: 101,
    fullName: 'Anuchin Alexander',
    email: 'alexander.anuchin@example.com',
    avatarUrl: undefined,
    role: 'legend',
    locale: 'ru',
    mode: 'Легенда',
    featureFlags: {
      aiAssistant: true,
      aiCurator: true,
      marketplace: true,
      training: true,
      recovery: true,
      gadgets: true,
      integrations: true,
      riskForecast: true,
      documents: true,
      nutritionAnalytics: true,
      mealConstructor: true,
    },
    isStaff: true,
    profile: {
      sex: 'm',
      height_cm: 180,
      weight_kg: 82,
      activity_level: 'athlete',
      goal: 'maintain',
      allergies: [],
      exclusions: [],
    },
  })),
  fetchWallet: vi.fn(async () => ({
    balance: {
      stars: 4200,
      calo: 12000,
      updatedAt: new Date('2024-11-01T10:00:00Z').toISOString(),
    },
    transactions: [
      {
        id: '1',
        title: 'Пополнение кошелька',
        amount: 500,
        currency: 'stars' as const,
        direction: 'in' as const,
        timestamp: new Date('2024-11-01T09:50:00Z').toISOString(),
      },
    ],
    starsPurchaseBlocked: false,
  })),
  fetchBotStarsBalance: vi.fn(async () => ({
    amount: 9999,
    currency: 'XTR',
    updatedAt: new Date('2024-11-01T10:00:00Z').toISOString(),
  })),
}))

async function renderWithProviders(
  ui: ReactNode,
  { route = '/plan' }: { route?: string } = {},
): Promise<RenderResult> {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
      },
    },
  })

  tokenStore.access = 'test-access-token'
  tokenStore.refresh = 'test-refresh-token'

  const result = render(
    <MemoryRouter initialEntries={[route]}>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <AuthProvider>
            <CommandPaletteProvider>{ui}</CommandPaletteProvider>
          </AuthProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  )

  await act(async () => {
    await Promise.resolve()
  })

  return result
}

describe('navigation system', () => {
  beforeEach(() => {
    setMockAuthValue(createMockAuthContextValue())
    vi.clearAllMocks()
  })

  afterEach(() => {
    tokenStore.clear()
  })

  it('renders AppNavbar with wallet badge', async () => {
    await renderWithProviders(<AppNavbar onMenuClick={() => {}} onOpenCommand={() => {}} />)

    expect(await screen.findByLabelText(/открыть кошелёк/i)).toBeInTheDocument()
    expect(await screen.findByLabelText(/баланс бота/i)).toBeInTheDocument()
  })

  it('highlights active tab in MobileTabBar', async () => {
    await renderWithProviders(<MobileTabBar onOpenCommand={() => {}} />, { route: '/profile' })
    const profileLink = await screen.findByRole('link', { name: /профиль/i })
    expect(profileLink).toHaveAttribute('aria-current', 'page')
  })

  it('shows sections inside NavDrawer', async () => {
    await renderWithProviders(<NavDrawer open onOpenChange={() => {}} />)
    expect(await screen.findByRole('button', { name: /выйти/i })).toBeInTheDocument()
    expect(screen.getByText(/Питание и калории/i)).toBeInTheDocument()
  })

  it('opens command palette on Cmd+K', async () => {
    await renderWithProviders(<CommandPanel />)

    const isMac = navigator.platform?.toLowerCase().includes('mac') ?? false
    await act(async () => {
      fireEvent.keyDown(window, { key: 'k', ctrlKey: !isMac, metaKey: isMac })
    })
    expect(await screen.findByRole('dialog', { name: /командная палитра/i })).toBeInTheDocument()
  })
})