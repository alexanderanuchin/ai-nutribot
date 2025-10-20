+49
-0

import { render, screen } from '@testing-library/react'

import type { NewsFeedItem } from '../../../types/feed'
import { NewsCard } from './NewsCard'

const baseItem: NewsFeedItem = {
  id: 1,
  source_id: 'ext-1',
  title: 'ЗОЖ тренды 2025',
  lead: 'Исследователи рассказали о новых подходах к питанию.',
  source_name: 'Health News',
  source_url: 'https://example.com/news',
  published_at: '2024-12-02T08:00:00Z',
  published_at_localized: '2 дек 2024, 11:00',
  preview_image_url: 'https://cdn.example.com/image.jpg',
  tonality: 'positive',
  source_categories: ['wellness', 'analysis'],
  toxicity_score: '0.1200',
  clickbait_score: '0.1800',
  is_flagged: true,
  ingested_at: '2024-12-02T08:05:00Z',
  ingestion_source: 'crawler',
  ingestion_rid: 'RID-1234567890abcdef',
  ingestion_metadata: { moderation: { toxicity: 0.12 } },
  created_at: '2024-12-02T07:59:00Z',
  updated_at: '2024-12-02T08:05:00Z',
  tags: [
    { id: 1, name: 'Wellness', slug: 'wellness', kind: 'news' },
    { id: 2, name: 'Здоровье', slug: 'health', kind: 'news' },
  ],
}

describe('NewsCard', () => {
  it('renders tonality, moderation badge and metrics', () => {
    render(<NewsCard item={baseItem} />)

    expect(screen.getByText('Позитив')).toBeInTheDocument()
    expect(screen.getByText('Требует проверки')).toBeInTheDocument()
    expect(screen.getByText('0.12')).toBeInTheDocument()
    expect(screen.getByText('0.18')).toBeInTheDocument()
    expect(screen.getByText(/Обновлено/)).toBeInTheDocument()
  })

  it('truncates long RID values for readability', () => {
    render(<NewsCard item={baseItem} />)

    expect(screen.getByText('RID-1234567890ab…')).toBeInTheDocument()
  })
})
