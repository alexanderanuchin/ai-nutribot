import type { FeedRealtimeEvent, FeedTab } from '../../types/feed'

export const FEED_TABS: Array<{ id: FeedTab; label: string; subtitle: string }> = [
  { id: 'news', label: 'Новости', subtitle: 'про питание и ЗОЖ' },
  { id: 'recipes', label: 'Рецепты', subtitle: 'Меню на день и вечер' },
  { id: 'deals', label: 'Акции', subtitle: 'Акции рядом с вами' },
]

export const GROUP_TO_TAB: Record<FeedRealtimeEvent['group'], FeedTab> = {
  'feed.news': 'news',
  'feed.recipes': 'recipes',
  'feed.deals': 'deals',
}