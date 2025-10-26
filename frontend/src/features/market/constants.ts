import type { MarketResource } from '../../types/market'

export interface MarketFilterDefinition {
  id: string
  label: string
  description?: string
  param: string
  value: string | number | boolean
}

export type MarketFiltersMap = Record<MarketResource, MarketFilterDefinition[]>

export const MARKET_FILTERS: MarketFiltersMap = {
  recipes: [
    {
      id: 'fast',
      label: 'До 30 мин',
      description: 'Быстрые блюда на каждый день',
      param: 'max_time',
      value: 30,
    },
    {
      id: 'high-protein',
      label: 'Больше белка',
      description: '≥ 25 г белка',
      param: 'min_protein',
      value: 25,
    },
    {
      id: 'budget',
      label: 'До 300 ₽',
      description: 'Экономия бюджета',
      param: 'max_price',
      value: 300,
    },
    {
      id: 'plant-based',
      label: 'Растительные',
      param: 'tag',
      value: 'plant-based',
    },
  ],
  products: [
    {
      id: 'organic',
      label: 'Органика',
      param: 'tag',
      value: 'organic',
    },
    {
      id: 'discount',
      label: 'Со скидкой',
      param: 'discount_only',
      value: true,
    },
    {
      id: 'in-stock',
      label: 'В наличии',
      param: 'available',
      value: true,
    },
    {
      id: 'local',
      label: 'Локальные фермы',
      param: 'origin',
      value: 'local',
    },
  ],
  stores: [
    {
      id: 'express',
      label: 'Экспресс',
      param: 'max_eta',
      value: 45,
    },
    {
      id: 'free-delivery',
      label: 'Бесплатная доставка',
      param: 'free_delivery',
      value: true,
    },
    {
      id: 'online',
      label: 'Онлайн',
      param: 'is_online',
      value: true,
    },
    {
      id: 'premium',
      label: 'Премиум',
      param: 'tag',
      value: 'premium',
    },
  ],
}

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
  id: 'hub' | MarketResource
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