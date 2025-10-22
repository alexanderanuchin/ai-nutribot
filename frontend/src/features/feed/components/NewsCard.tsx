import { useMemo, useState } from 'react'

import clsx from 'clsx'
import { AlertTriangle, ExternalLinkIcon, ImageOff } from 'lucide-react'

import type { NewsFeedItem } from '../../../types/feed'

export interface NewsCardProps {
  item: NewsFeedItem
}

const TONALITY_META: Record<NewsFeedItem['tonality'], { label: string; className: string }> = {
  positive: {
    label: 'Позитив',
    className: 'bg-emerald-100 text-emerald-900 dark:bg-emerald-400/20 dark:text-emerald-200',
  },
  neutral: {
    label: 'Нейтрально',
    className: 'bg-slate-200 text-slate-800 dark:bg-slate-500/30 dark:text-slate-200',
  },
  negative: {
    label: 'Негатив',
    className: 'bg-rose-100 text-rose-900 dark:bg-rose-400/20 dark:text-rose-200',
  },
}

function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  try {
    return new Intl.DateTimeFormat('ru-RU', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(value))
  } catch (_error) {
    return value
  }
}

function formatScore(score: string | null | undefined): string {
  if (!score) return '—'
  const numeric = Number(score)
  if (Number.isFinite(numeric)) {
    return numeric.toFixed(2)
  }
  return score
}

function truncateRid(rid: string | null | undefined): string {
  if (!rid) return '—'
  return rid.length > 16 ? `${rid.slice(0, 16)}…` : rid
}

export function NewsCard({ item }: NewsCardProps) {
  const [previewFailed, setPreviewFailed] = useState(false)
  const publishedLabel = item.published_at_localized ?? formatDate(item.published_at)
  const tonalityMeta = TONALITY_META[item.tonality] ?? TONALITY_META.neutral
  const updatedLabel = formatDate(item.ingested_at ?? item.updated_at ?? item.published_at)
  const categories = Array.isArray(item.source_categories) ? item.source_categories.filter(Boolean) : []
  const shouldShowPreview = Boolean(item.preview_image_url) && !previewFailed
  const mediaNode = useMemo(() => {
    if (shouldShowPreview) {
      return (
        <img
          src={item.preview_image_url}
          alt={item.title}
          className="h-full w-full object-cover"
          loading="lazy"
          onError={() => setPreviewFailed(true)}
        />
      )
    }
    return (
      <div className="flex h-full w-full flex-col items-center justify-center gap-2 text-xs font-medium text-muted-foreground">
        <ImageOff className="h-6 w-6" aria-hidden="true" />
        <span className="truncate">Нет превью</span>
      </div>
    )
  }, [item.preview_image_url, item.title, shouldShowPreview])

  return (
    <article
      className={clsx(
        'group flex flex-col gap-4 overflow-hidden rounded-3xl border bg-background/90 p-4 shadow-soft transition hover:-translate-y-0.5 hover:shadow-lg sm:flex-row',
        item.is_flagged
          ? 'border-amber-400/70 ring-2 ring-amber-200/60 dark:border-amber-300/50 dark:ring-amber-500/40'
          : 'border-border/60'
      )}
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
        <div className="overflow-hidden rounded-2xl bg-muted/60 sm:w-40 sm:flex-shrink-0">
          <div className="aspect-[4/3] w-full">{mediaNode}</div>
        </div>
        <div className="flex min-w-0 flex-1 flex-col gap-3">
          <div className="flex min-w-0 flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span className="min-w-0 truncate font-medium uppercase tracking-wide text-foreground/80">{item.source_name}</span>
            <span className="hidden h-1 w-1 rounded-full bg-border/80 sm:inline-flex" aria-hidden="true" />
            <time className="truncate" dateTime={item.published_at}>
              {publishedLabel}
            </time>
            <span
              className={clsx(
                'inline-flex items-center gap-1 rounded-full px-2 py-1 text-[11px] font-semibold',
                tonalityMeta.className
              )}
            >
              {tonalityMeta.label}
            </span>
            {item.is_flagged ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-1 text-[11px] font-semibold text-amber-900 dark:bg-amber-400/20 dark:text-amber-100">
                <AlertTriangle className="h-3 w-3" aria-hidden="true" />
                Требует проверки
              </span>
            ) : null}
          </div>
          <h3 className="line-clamp-2 text-base font-semibold text-foreground [overflow-wrap:anywhere]">{item.title}</h3>
          {categories.length ? (
            <div className="flex flex-wrap gap-2 text-[11px] text-muted-foreground">
              {categories.map(category => (
                <span
                  key={`${item.id}-${category}`}
                  className="rounded-full bg-muted/60 px-2 py-1 text-[11px] font-medium text-muted-foreground"
                >
                  {category}
                </span>
              ))}
            </div>
          ) : null}
          <p className="line-clamp-3 text-sm text-muted-foreground [overflow-wrap:anywhere]">{item.lead}</p>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-[11px] text-muted-foreground sm:grid-cols-3">
            <div className="space-y-0.5">
              <dt className="uppercase tracking-wide text-[10px] text-muted-foreground/80">Токсичность</dt>
              <dd className="text-sm font-semibold text-foreground">{formatScore(item.toxicity_score)}</dd>
            </div>
            <div className="space-y-0.5">
              <dt className="uppercase tracking-wide text-[10px] text-muted-foreground/80">Кликбейтность</dt>
              <dd className="text-sm font-semibold text-foreground">{formatScore(item.clickbait_score)}</dd>
            </div>
            <div className="space-y-0.5">
              <dt className="uppercase tracking-wide text-[10px] text-muted-foreground/80">RID</dt>
              <dd className="truncate font-mono text-xs text-muted-foreground/90">{truncateRid(item.ingestion_rid)}</dd>
            </div>
          </dl>
          <div className="mt-auto flex flex-wrap items-center gap-2 pt-2">
            {item.tags.slice(0, 4).map(tag => (
              <span
                key={tag.id}
                className="rounded-full bg-primary/10 px-2 py-1 text-[11px] font-semibold text-primary"
              >
                #{tag.slug}
              </span>
            ))}
            <span className="text-[11px] text-muted-foreground">Обновлено {updatedLabel}</span>
            <a
              href={item.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex min-h-[2.75rem] w-full items-center justify-center gap-1 rounded-full bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground transition hover:bg-primary/90 sm:w-auto sm:justify-center sm:ml-auto"
            >
              Источник <ExternalLinkIcon className="h-3 w-3" aria-hidden="true" />
            </a>
          </div>
        </div>
      </div>
    </article>
  )
}

export default NewsCard