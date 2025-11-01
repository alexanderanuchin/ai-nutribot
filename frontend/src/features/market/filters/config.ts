import type { MarketResource } from '../../../types/market'

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

export interface MarketSortOptionConfig {
  value: string
  label: string
  ordering?: string
}

export type MarketSortConfigMap = Record<MarketResource, MarketSortOptionConfig[]>

export const MARKET_SORT_CONFIG: MarketSortConfigMap = {
  recipes: [
    { value: 'relevance', label: 'Актуальные' },
    { value: 'time_asc', label: 'По времени', ordering: 'time_minutes' },
    { value: 'calories_asc', label: 'Ккал', ordering: 'calories' },
  ],
  products: [
    { value: 'recommended', label: 'Реком.' },
    { value: 'price_asc', label: 'Цена ↑', ordering: 'price' },
    { value: 'price_desc', label: 'Цена ↓', ordering: '-price' },
    { value: 'discount', label: 'Скидки', ordering: '-discount' },
  ],
  stores: [
    { value: 'top_rated', label: 'Лучшие', ordering: '-rating' },
    { value: 'eta_asc', label: 'Доставка', ordering: 'eta' },
    { value: 'fresh', label: 'Новые', ordering: '-freshness' },
  ],
}

export const MARKET_SORT_OPTIONS: Record<MarketResource, Array<{ value: string; label: string }>> = Object.fromEntries(
  Object.entries(MARKET_SORT_CONFIG).map(([resource, options]) => [
    resource,
    options.map(({ value, label }) => ({ value, label })),
  ]),
) as Record<MarketResource, Array<{ value: string; label: string }>>

export const MARKET_ORDERING_MAP: Record<MarketResource, Record<string, string | undefined>> = Object.fromEntries(
  Object.entries(MARKET_SORT_CONFIG).map(([resource, options]) => [
    resource,
    options.reduce<Record<string, string | undefined>>((acc, option) => {
      acc[option.value] = option.ordering
      return acc
    }, {}),
  ]),
) as Record<MarketResource, Record<string, string | undefined>>

export const MARKET_PRICE_LIMITS: Record<MarketResource, [number, number]> = {
  recipes: [0, 1200],
  products: [0, 5000],
  stores: [0, 1000],
}
