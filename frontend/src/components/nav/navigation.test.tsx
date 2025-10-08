import type { ReactNode } from 'react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AppNavbar from './AppNavbar'
import MobileTabBar from './MobileTabBar'
import NavDrawer from './NavDrawer'
import CommandPanel from './CommandPanel'
import { ThemeProvider } from '../../hooks/useTheme'
import { AuthProvider } from '../../providers/AuthProvider'
import { CommandPaletteProvider } from '../../hooks/useCommandPalette'

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
  })),
  fetchBotStarsBalance: vi.fn(async () => ({
    amount: 9999,
    currency: 'XTR',
    updatedAt: new Date('2024-11-01T10:00:00Z').toISOString(),
  })),
}))

function renderWithProviders(ui: ReactNode, { route = '/plan' }: { route?: string } = {}) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
      },
    },
  })

  return render(
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
}

describe('navigation system', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders AppNavbar with wallet badge', async () => {
    renderWithProviders(<AppNavbar onMenuClick={() => {}} onOpenCommand={() => {}} />)

    expect(await screen.findByLabelText(/открыть кошелёк/i)).toBeInTheDocument()
    expect(await screen.findByLabelText(/баланс бота/i)).toBeInTheDocument()
  })

  it('highlights active tab in MobileTabBar', async () => {
    renderWithProviders(<MobileTabBar onOpenCommand={() => {}} />, { route: '/profile' })
    const profileLink = await screen.findByRole('link', { name: /профиль/i })
    expect(profileLink).toHaveAttribute('aria-current', 'page')
  })

  it('shows sections inside NavDrawer', async () => {
    renderWithProviders(<NavDrawer open onOpenChange={() => {}} />)
    expect(await screen.findByRole('button', { name: /выйти/i })).toBeInTheDocument()
    expect(screen.getByText(/Питание и калории/i)).toBeInTheDocument()
  })

  it('opens command palette on Cmd+K', async () => {
    renderWithProviders(<CommandPanel />)
    fireEvent.keyDown(window, { key: 'k', ctrlKey: true })
    expect(await screen.findByRole('dialog', { name: /командная палитра/i })).toBeInTheDocument()
  })
})