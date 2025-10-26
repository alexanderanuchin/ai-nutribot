import { MemoryRouter } from 'react-router-dom'

import type { NewsFeedItem } from '../../../types/feed'
import { NewsCard } from './NewsCard'

interface StoryMeta<T> {
  title: string
  component: T
}

const baseItem: NewsFeedItem = {
  id: 1,
  source_id: 'ext-story',
  title: 'Польза сезонных овощей',
  lead: 'Эксперты NutriBot подготовили рекомендации по сезонным овощам и фруктам.',
  body: 'Полный текст материала о пользе сезонных овощей и фруктов.',
  title_orig: null,
  lead_orig: null,
  body_orig: null,
  lang: 'ru',
  translated: false,
  translation_provider: '',
  source_name: 'NutriBot',
  source_url: 'https://example.com/story',
  published_at: '2024-12-02T09:00:00Z',
  published_at_msk: '2024-12-02T12:00:00+03:00',
  published_at_localized: '2 дек 2024, 12:00',
  timezone_label: 'MSK',
  preview_image_url: 'https://cdn.example.com/story.jpg',
  tonality: 'neutral',
  source_categories: ['wellness', 'nutrition'],
  toxicity_score: '0.2200',
  clickbait_score: '0.1800',
  is_flagged: false,
  ingested_at: '2024-12-02T09:05:00Z',
  ingestion_source: 'storybook',
  ingestion_rid: 'RID-STORY',
  ingestion_metadata: { moderation: { clickbait: 0.18 } },
  created_at: '2024-12-02T08:59:00Z',
  updated_at: '2024-12-02T09:05:00Z',
  tags: [
    { id: 1, name: 'Витамины', slug: 'vitamins', kind: 'news' },
    { id: 2, name: 'Овощи', slug: 'vegetables', kind: 'news' },
  ],
}

const meta: StoryMeta<typeof NewsCard> = {
  title: 'Feed/NewsCard',
  component: NewsCard,
}

export default meta

export const Default = () => (
  <MemoryRouter initialEntries={['/feed']}>
    <NewsCard item={baseItem} navigationState={{ tab: 'news', scrollY: 0, filters: {} }} />
  </MemoryRouter>
)

export const Flagged = () => (
  <MemoryRouter initialEntries={['/feed']}>
    <NewsCard
      item={{
        ...baseItem,
        id: 2,
        title: 'Фактчекинг сенсационных новостей',
        lead: 'Команда модерации проверяет материалы с повышенным риском.',
        is_flagged: true,
        toxicity_score: '0.7200',
        clickbait_score: '0.9100',
        source_categories: ['fact-check', 'moderation'],
        ingestion_rid: 'RID-FLAGGED',
      }}
      navigationState={{ tab: 'news', scrollY: 0, filters: {} }}
    />
  </MemoryRouter>
)