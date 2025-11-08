import { RecipeCard } from './RecipeCard'
import type { MarketRecipe } from '../../../types/market'

const meta = {
  title: 'Market/RecipeCard',
  component: RecipeCard,
}

export default meta

const sampleRecipe: MarketRecipe = {
  id: 101,
  store: 1,
  store_name: 'Nutri Kitchen',
  store_slug: 'nutri-kitchen',
  store_city: 'Москва',
  store_logo_url: null,
  title: 'Боул с киноа и авокадо',
  slug: 'quinoa-bowl',
  summary: null,
  subtitle: 'Баланс белков и полезных жиров',
  description: 'Идеальный боул для обеда с киноа, нутом и свежими овощами.',
  cooking_time_minutes: 25,
  servings: 2,
  difficulty: 'easy',
  calories: 520,
  protein_g: 28,
  fat_g: 18,
  carbs_g: 55,
  price: 150,
  price_stars: 150,
  currency: 'STARS',
  rating: 4.8,
  rating_count: 87,
  hero_image_url: 'https://images.unsplash.com/photo-1512058564366-c9e3e0464b1b?auto=format&fit=crop&w=700&q=80',
  preview_image_url: null,
  tags: ['vegan', 'gluten-free'],
  is_premium: true,
  is_in_plan: false,
  is_free: false,
  has_access: false,
  is_public: true,
  published_at: '2025-01-01T10:00:00Z',
  metadata: {},
  created_at: '2025-01-01T10:00:00Z',
  updated_at: '2025-01-02T10:00:00Z',
  steps: [],
  ingredients: [],
}

export const Default = () => <RecipeCard item={sampleRecipe} />

export const InPlan = () => (
  <RecipeCard
    item={{
      ...sampleRecipe,
      id: 102,
      title: 'Смузи боул с ягодами',
      rating: 4.5,
      rating_count: 34,
      has_access: true,
    }}
  />
)