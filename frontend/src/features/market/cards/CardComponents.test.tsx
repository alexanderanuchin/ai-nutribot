import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'

import { ToastProvider } from '../../../components/ui/Toast'
import type { MarketProduct, MarketRecipe, MarketStore } from '../../../types/market'
import { useMarketCartStore } from '../stores/cartStore'
import { useMarketPlanStore } from '../stores/planStore'
import ProductCard from './ProductCard'
import RecipeCard from './RecipeCard'
import StoreCard from './StoreCard'

vi.mock('../../../hooks/useAuth', () => ({
  useAuth: () => ({
    ready: true,
    bootstrapping: false,
    authReady: true,
    refreshing: false,
    authenticated: true,
    profile: { calocoin_rate_rub: 100 },
  }),
}))

const activeClients: QueryClient[] = []

function renderWithProviders(children: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, cacheTime: 0 },
      mutations: { retry: false },
    },
  })

  activeClients.push(queryClient)

  const result = render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>{children}</ToastProvider>
    </QueryClientProvider>,
  )

  return result
}

const initialCartState = useMarketCartStore.getState()
const initialPlanState = useMarketPlanStore.getState()

describe('Market cards', () => {
  beforeEach(() => {
    useMarketCartStore.setState({ items: {}, hydrated: true })
    useMarketPlanStore.setState({ items: {}, hydrated: true })
  })

  afterEach(() => {
    cleanup()
    while (activeClients.length) {
      const client = activeClients.pop()
      client?.clear()
    }
    useMarketCartStore.setState(initialCartState, true)
    useMarketPlanStore.setState(initialPlanState, true)
  })

  it('renders product card without NaN values', () => {
    const product: MarketProduct = {
      id: 1,
      store: 10,
      store_name: 'Demo Store',
      store_slug: 'demo-store',
      store_city: 'Москва',
      store_logo_url: null,
      store_is_verified: true,
      store_owner_id: 2,
      title: 'Протеиновая гранола',
      slug: 'protein-granola',
      subtitle: null,
      description: 'Полезный завтрак',
      price: 390,
      currency: 'RUB',
      weight_grams: null,
      unit: null,
      price_original: undefined,
      discount_percent: undefined,
      image_url: null,
      brand: null,
      badges: ['хит'],
      rating: undefined,
      rating_count: undefined,
      is_in_cart: false,
      available: true,
      is_published: true,
      published_at: null,
      available_from: null,
      available_until: null,
      created_at: '2025-01-01T10:00:00Z',
      updated_at: '2025-01-02T10:00:00Z',
      inventory_available: 12,
      inventory_quantity: 12,
      inventory_reserved: 0,
      inventory: null,
      metadata: {},
      tags: ['granola'],
      nutrition: {},
    }

    const { container } = renderWithProviders(<ProductCard item={product} />)
    expect(container.textContent?.includes('NaN')).toBe(false)
    const addButton = screen.getByRole('button', { name: 'В корзину' })
    expect(addButton).toBeEnabled()
  })

  it('renders recipe card with safe macro values', () => {
    const recipe: MarketRecipe = {
      id: 5,
      store: 10,
      store_name: 'Demo Store',
      store_slug: 'demo-store',
      store_city: 'Москва',
      store_logo_url: null,
      title: 'Боул с гранолой',
      slug: 'granola-bowl',
      summary: null,
      subtitle: null,
      description: 'Быстрый завтрак',
      calories: Number.NaN,
      protein_g: Number.NaN,
      fat_g: Number.NaN,
      carbs_g: Number.NaN,
      cooking_time_minutes: 5,
      servings: 2,
      difficulty: 'easy',
      price: undefined,
      price_stars: null,
      currency: 'RUB',
      rating: undefined,
      rating_count: undefined,
      hero_image_url: null,
      preview_image_url: null,
      tags: [],
      is_premium: false,
      is_free: true,
      is_in_plan: false,
      has_access: true,
      is_public: true,
      published_at: null,
      metadata: {},
      created_at: '2025-01-01T10:00:00Z',
      updated_at: '2025-01-02T10:00:00Z',
      steps: [],
      ingredients: [],
    }

    const { container } = renderWithProviders(<RecipeCard item={recipe} />)
    expect(container.textContent?.includes('NaN')).toBe(false)
    const macroValues = screen.getAllByText('0 г')
    expect(macroValues.length).toBeGreaterThanOrEqual(3)
  })

  it('renders store card without NaN artifacts', () => {
    const store: MarketStore = {
      id: 7,
      slug: 'demo-store',
      owner: 2,
      owner_username: 'vendor',
      owner_full_name: 'Demo Vendor',
      name: 'Demo Market Store',
      city: 'Москва',
      description: 'Ремесленная лавка',
      is_active: true,
      is_verified: true,
      rating: Number.NaN,
      rating_count: Number.NaN,
      delivery_eta_minutes: Number.NaN,
      delivery_price: Number.NaN,
      currency: 'RUB',
      is_online: true,
      hero_image_url: null,
      logo_url: null,
      tags: ['premium'],
      link_url: null,
      metadata: {},
      created_at: '2025-01-01T10:00:00Z',
      updated_at: '2025-01-02T10:00:00Z',
    }

    const { container } = renderWithProviders(<StoreCard item={store} />)
    expect(container.textContent?.includes('NaN')).toBe(false)
  })
})
