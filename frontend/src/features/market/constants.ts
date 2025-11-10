import type { MarketResource } from '../../types/market'
import type { MarketFiltersMap, MarketFilterDefinition } from './filters/config'
export { MARKET_FILTERS } from './filters/config'
export type { MarketFilterDefinition }

export const MARKET_RESOURCE_LABELS: Record<MarketResource, string> = {
  recipes: 'рецептов',
  products: 'товаров',
  stores: 'магазинов',
}

export const MARKET_RESOURCE_TITLE: Record<MarketResource, string> = {
  recipes: 'Рецепты и готовые блюда',
  products: 'Товары для здорового питания',
  stores: 'Магазины и кухни партнёров',
}

export const MARKET_RESOURCE_DESCRIPTION: Record<MarketResource, string> = {
  recipes: 'Подборка свежих рецептов и рационов с балансом нутриентов и AI-подсказками.',
  products: 'Полка с полезными продуктами, напитками и снек-боксами, проверенными NutriBot.',
  stores: 'Партнёры доставки: dark kitchen, фермерские магазины и healthy-рестораны рядом с вами.',
}

export const MARKET_SECTIONS: Array<{
  id: 'hub' | 'mealplans' | MarketResource
  label: string
  description: string
  to: string
}> = [
  {
    id: 'hub',
    label: 'Маркет',
    description: 'Витрина и подборки',
    to: '/market',
  },
  {
    id: 'mealplans',
    label: 'Программы',
    description: 'Планы от нутрициологов',
    to: '/market/meal-plans',
  },
  {
    id: 'recipes',
    label: 'Рецепты',
    description: 'Готовые блюда и рационы',
    to: '/market/recipes',
  },
  {
    id: 'products',
    label: 'Продукты',
    description: 'Полезные товары',
    to: '/market/products',
  },
  {
    id: 'stores',
    label: 'Магазины',
    description: 'Партнёры доставки',
    to: '/market/stores',
  },
]