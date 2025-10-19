import type { FeedRealtimeEvent, FeedTab } from '../../types/feed'

export const FEED_TABS: Array<{ id: FeedTab; label: string; subtitle: string }> = [
  { id: 'news', label: 'Новости', subtitle: 'Мир здорового питания' },
  { id: 'recipes', label: 'Рецепты', subtitle: 'Свежие блюда и планы' },
  { id: 'deals', label: 'Акции', subtitle: 'Скидки в магазинах' },
]

export const GROUP_TO_TAB: Record<FeedRealtimeEvent['group'], FeedTab> = {
  'feed.news': 'news',
  'feed.recipes': 'recipes',
  'feed.deals': 'deals',
}