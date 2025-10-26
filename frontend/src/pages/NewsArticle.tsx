import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useQuery, useQueryClient, type InfiniteData } from '@tanstack/react-query'
import clsx from 'clsx'
import { isAxiosError } from 'axios'
import { AlertTriangle, ArrowLeft, ExternalLinkIcon, RefreshCw, Share2, WifiOff } from 'lucide-react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'

import { fetchNewsArticle } from '../api/feed'
import type { FeedTab, NewsArticleDetail, NewsFeedItem } from '../types/feed'

const MOSCOW_TIMEZONE = 'Europe/Moscow'
const MOSCOW_LABEL = 'МСК'

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

function resolveTimezoneLabel(label: string | null | undefined): string {
  if (!label) return MOSCOW_LABEL
  if (label.toUpperCase() === 'MSK') return MOSCOW_LABEL
  return label
}

function formatMoscowDate(primary?: string | null, fallback?: string | null, label?: string | null): string {
  const timezoneLabel = resolveTimezoneLabel(label)
  const isoValue = primary ?? fallback
  if (!isoValue) return '—'
  try {
    const formatter = new Intl.DateTimeFormat('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: MOSCOW_TIMEZONE,
    })
    return `${formatter.format(new Date(isoValue))} (${timezoneLabel})`
  } catch (_error) {
    return `${isoValue} (${timezoneLabel})`
  }
}

function formatScore(score?: string | null): string | null {
  if (!score) return null
  const numeric = Number(score)
  if (Number.isFinite(numeric)) {
    return numeric.toFixed(2)
  }
  return score
}

type FeedLocationState = {
  from?: { pathname?: string; search?: string; hash?: string }
  tab?: FeedTab
  scrollY?: number
  filters?: Record<string, string | boolean>
}

type ShareFeedback = 'idle' | 'copied' | 'error'

type FeedQueryPage = {
  items: NewsFeedItem[]
}

type FeedInfiniteData = InfiniteData<FeedQueryPage>

function usePrefetchedArticle(id: string | undefined): NewsArticleDetail | undefined {
  const queryClient = useQueryClient()
  return useMemo(() => {
    if (!id) return undefined
    const queries = queryClient.getQueriesData<FeedInfiniteData>({ queryKey: ['feed', 'news'] })
    for (const [, data] of queries) {
      if (!data) continue
      for (const page of data.pages ?? []) {
        const match = page.items?.find(article => String(article.id) === id)
        if (match) {
          return match as NewsArticleDetail
        }
      }
    }
    return undefined
  }, [id, queryClient])
}

function NewsArticleSkeleton() {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6" aria-hidden="true">
      <div className="h-48 w-full animate-pulse rounded-3xl bg-muted" />
      <div className="space-y-4">
        <div className="h-6 w-32 animate-pulse rounded-full bg-muted" />
        <div className="h-10 w-3/4 animate-pulse rounded-full bg-muted" />
        <div className="h-4 w-2/3 animate-pulse rounded-full bg-muted" />
      </div>
      <div className="space-y-3">
        <div className="h-4 w-full animate-pulse rounded-full bg-muted" />
        <div className="h-4 w-11/12 animate-pulse rounded-full bg-muted" />
        <div className="h-4 w-10/12 animate-pulse rounded-full bg-muted" />
        <div className="h-4 w-9/12 animate-pulse rounded-full bg-muted" />
      </div>
    </div>
  )
}

interface EmptyStateProps {
  title: string
  description: string
  actionLabel: string
  onAction: () => void
  icon?: ReactNode
}

function EmptyState({ title, description, actionLabel, onAction, icon }: EmptyStateProps) {
  return (
    <div className="mx-auto flex w-full max-w-md flex-col items-center gap-4 rounded-3xl border border-border/60 bg-background/90 p-6 text-center shadow-sm">
      {icon}
      <h2 className="text-lg font-semibold text-foreground">{title}</h2>
      <p className="text-sm text-muted-foreground">{description}</p>
      <button
        type="button"
        onClick={onAction}
        className="inline-flex items-center justify-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      >
        {actionLabel}
      </button>
    </div>
  )
}

export default function NewsArticle() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const locationState = (location.state as FeedLocationState | null) ?? null
  const [isOnline, setIsOnline] = useState(() => (typeof navigator !== 'undefined' ? navigator.onLine : true))
  const [shareFeedback, setShareFeedback] = useState<ShareFeedback>('idle')
  const [translationMode, setTranslationMode] = useState<'translated' | 'original'>('translated')
  const [imageFailed, setImageFailed] = useState(false)

  const prefetchedArticle = usePrefetchedArticle(id)

  const {
    data: article,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['feed', 'news', 'detail', id],
    queryFn: () => fetchNewsArticle(id as string),
    enabled: Boolean(id),
    initialData: prefetchedArticle,
    staleTime: 60_000,
  })

  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  useEffect(() => {
    if (!article) return
    const hasTranslation = Boolean(article.title_ru || article.lead_ru || article.body_ru)
    setTranslationMode(hasTranslation ? 'translated' : 'original')
    setImageFailed(false)
  }, [article?.id])

  useEffect(() => {
    if (shareFeedback === 'idle') return
    const timer = window.setTimeout(() => setShareFeedback('idle'), 2400)
    return () => window.clearTimeout(timer)
  }, [shareFeedback])

  const handleBack = useCallback(() => {
    const cameFromFeed = Boolean(
      locationState?.from && typeof locationState.from.pathname === 'string' && locationState.from.pathname.startsWith('/feed')
    )
    if (cameFromFeed) {
      navigate(-1)
      return
    }
    const tab = locationState?.tab ?? 'news'
    const search = tab ? `?tab=${tab}` : ''
    navigate(`/feed${search}`, {
      replace: true,
      state: {
        tab,
        scrollY: locationState?.scrollY ?? 0,
        filters: locationState?.filters ?? {},
      },
    })
  }, [locationState, navigate])

  const handleRetry = useCallback(() => {
    void refetch()
  }, [refetch])

  const handleShare = useCallback(async () => {
    if (!article) return
    const shareUrl = (() => {
      if (typeof window === 'undefined') return ''
      try {
        const origin = window.location.origin
        return new URL(`/feed/news/${article.id}`, origin).toString()
      } catch (_error) {
        return ''
      }
    })()
    const shareTitle = article.title_ru || article.title || 'Новость'
    const shareText = article.lead_ru || article.lead || ''
    try {
      if (navigator.share) {
        await navigator.share({ title: shareTitle, text: shareText, url: shareUrl })
        return
      }
      if (navigator.clipboard && shareUrl) {
        await navigator.clipboard.writeText(shareUrl)
        setShareFeedback('copied')
        return
      }
      setShareFeedback('error')
    } catch (_error) {
      setShareFeedback('error')
    }
  }, [article])

  useEffect(() => {
    if (!article) return
    if (typeof document === 'undefined') return
    const translatedTitle = article.title_ru || (article.lang === 'ru' ? article.title : '')
    const originalTitle = article.title_orig || article.title || ''
    const resolvedTitle = translationMode === 'translated' && translatedTitle ? translatedTitle : originalTitle
    if (resolvedTitle) {
      document.title = `${resolvedTitle} — NutriBot`
    }
    const description =
      translationMode === 'translated'
        ? article.lead_ru || article.lead || ''
        : article.lead_orig || article.lead || ''
    if (description) {
      let meta = document.querySelector("meta[name='description']")
      if (!meta) {
        meta = document.createElement('meta')
        meta.setAttribute('name', 'description')
        document.head.appendChild(meta)
      }
      meta.setAttribute('content', description)
    }
  }, [article, translationMode])

  const translatedTitle = article?.title_ru || (article?.lang === 'ru' ? article?.title : '')
  const originalTitle = article?.title_orig || article?.title || ''
  const translatedLead = article?.lead_ru || (article?.lang === 'ru' ? article?.lead : '')
  const originalLead = article?.lead_orig || article?.lead || ''
  const translatedBody = article?.body_ru || (article?.lang === 'ru' ? article?.body : '')
  const originalBody = article?.body_orig || article?.body || ''

  const shouldShowTranslationToggle = Boolean(article && (article.title_ru || article.lead_ru || article.body_ru))
  const showTranslated = translationMode === 'translated' && shouldShowTranslationToggle
  const displayTitle = showTranslated && translatedTitle ? translatedTitle : originalTitle
  const displayLead = showTranslated && translatedLead ? translatedLead : originalLead
  const displayBody = showTranslated && translatedBody ? translatedBody : originalBody

  const publishedLabel = article
    ? formatMoscowDate(article.published_at_msk, article.published_at, article.timezone_label)
    : '—'
  const ingestedLabel = article ? formatMoscowDate(article.ingested_at, article.updated_at, article.timezone_label) : null
  const toxicityScore = formatScore(article?.toxicity_score)
  const clickbaitScore = formatScore(article?.clickbait_score)
  const categories = useMemo(
    () => (Array.isArray(article?.source_categories) ? article!.source_categories.filter(Boolean) : []),
    [article?.source_categories]
  )
  const tags = article?.tags ?? []
  const tonalityMeta = article ? TONALITY_META[article.tonality] ?? TONALITY_META.neutral : TONALITY_META.neutral

  const isNotFound = isError && isAxiosError(error) && error.response?.status === 404
  const showGenericError = isError && !isNotFound

  const safeAreaTop = 'calc(env(safe-area-inset-top, 0px) + 0.75rem)'
  const safeAreaBottom = 'calc(env(safe-area-inset-bottom, 0px) + 4rem)'

  const shareFeedbackLabel = shareFeedback === 'copied' ? 'Ссылка скопирована' : shareFeedback === 'error' ? 'Не удалось поделиться' : null

  return (
    <section className="relative flex h-full min-h-0 flex-1 flex-col">
      <header
        className="sticky top-0 z-40 flex items-center justify-between gap-3 border-b border-border/60 bg-background/95 px-4 pb-3 pt-4 backdrop-blur sm:px-6"
        style={{ paddingTop: safeAreaTop }}
      >
        <button
          type="button"
          onClick={handleBack}
          className="inline-flex items-center gap-2 rounded-full bg-muted/60 px-4 py-2 text-sm font-semibold text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Назад к ленте
        </button>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleShare}
            className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            <Share2 className="h-4 w-4" aria-hidden="true" /> Поделиться
          </button>
        </div>
      </header>

      {!isOnline ? (
        <div className="flex items-center justify-center gap-2 border-b border-amber-300 bg-amber-100 px-4 py-2 text-sm font-semibold text-amber-900 dark:border-amber-500 dark:bg-amber-500/20 dark:text-amber-100" role="status" aria-live="polite">
          <WifiOff className="h-4 w-4" aria-hidden="true" />
          Офлайн режим: показаны кэшированные данные
        </div>
      ) : null}

      <div
        className="relative flex-1 overflow-y-auto overscroll-contain bg-background px-4 pb-10 pt-6 [touch-action:pan-y] sm:px-6 lg:px-10"
        style={{ paddingBottom: safeAreaBottom }}
        aria-live={isFetching ? 'polite' : 'off'}
      >
        {isLoading && !article ? (
          <NewsArticleSkeleton />
        ) : isNotFound ? (
          <EmptyState
            title="Новость не найдена"
            description="Эта новость могла быть удалена или недоступна."
            actionLabel="К ленте"
            onAction={() =>
              navigate('/feed?tab=news', {
                replace: true,
                state: {
                  tab: locationState?.tab ?? 'news',
                  scrollY: locationState?.scrollY ?? 0,
                  filters: locationState?.filters ?? {},
                },
              })
            }
            icon={<AlertTriangle className="h-10 w-10 text-amber-500" aria-hidden="true" />}
          />
        ) : showGenericError ? (
          <EmptyState
            title="Не удалось загрузить новость"
            description="Проверьте подключение к интернету и попробуйте снова."
            actionLabel="Повторить"
            onAction={handleRetry}
            icon={<RefreshCw className="h-10 w-10 text-primary" aria-hidden="true" />}
          />
        ) : article ? (
          <article className="mx-auto flex w-full max-w-3xl flex-col gap-6">
            <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              <span className="font-semibold uppercase tracking-wide text-primary">{article.source_name}</span>
              <span className="hidden h-1 w-1 rounded-full bg-border/70 sm:inline-flex" aria-hidden="true" />
              <time dateTime={article.published_at}>{publishedLabel}</time>
              <span
                className={clsx(
                  'inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold',
                  tonalityMeta.className
                )}
              >
                {tonalityMeta.label}
              </span>
              {toxicityScore ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-muted px-3 py-1 text-xs font-semibold text-muted-foreground">
                  Токсичность {toxicityScore}
                </span>
              ) : null}
              {clickbaitScore ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-muted px-3 py-1 text-xs font-semibold text-muted-foreground">
                  Кликбейт {clickbaitScore}
                </span>
              ) : null}
              {article.is_flagged ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900 dark:bg-amber-500/30 dark:text-amber-100">
                  <AlertTriangle className="h-3 w-3" aria-hidden="true" /> Требует проверки
                </span>
              ) : null}
            </div>

            <h1 className="text-3xl font-bold leading-snug text-foreground [overflow-wrap:anywhere] sm:text-4xl">
              {displayTitle || 'Новость'}
            </h1>

            {displayLead ? <p className="text-lg text-muted-foreground [overflow-wrap:anywhere]">{displayLead}</p> : null}

            {shouldShowTranslationToggle ? (
              <div className="inline-flex rounded-full bg-muted/60 p-1">
                <button
                  type="button"
                  onClick={() => setTranslationMode('translated')}
                  className={clsx(
                    'rounded-full px-4 py-1 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background',
                    translationMode === 'translated'
                      ? 'bg-background text-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground'
                  )}
                >
                  Перевод
                </button>
                <button
                  type="button"
                  onClick={() => setTranslationMode('original')}
                  className={clsx(
                    'rounded-full px-4 py-1 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background',
                    translationMode === 'original'
                      ? 'bg-background text-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground'
                  )}
                >
                  Оригинал
                </button>
              </div>
            ) : null}

            {categories.length ? (
              <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                {categories.map(category => (
                  <span key={`${article.id}-${category}`} className="rounded-full bg-muted px-3 py-1 text-xs font-semibold">
                    {category}
                  </span>
                ))}
              </div>
            ) : null}

            {article.preview_image_url && !imageFailed ? (
              <div className="overflow-hidden rounded-3xl bg-muted/60">
                <img
                  src={article.preview_image_url}
                  alt={displayTitle || article.title}
                  className="h-auto w-full object-cover"
                  onError={() => setImageFailed(true)}
                />
              </div>
            ) : (
              <div className="flex h-48 items-center justify-center rounded-3xl bg-muted text-sm font-medium text-muted-foreground">
                Обложка недоступна
              </div>
            )}

            <div className="prose prose-slate max-w-none text-base leading-relaxed text-foreground dark:prose-invert">
              {displayBody ? (
                <div dangerouslySetInnerHTML={{ __html: displayBody }} />
              ) : (
                <p className="text-muted-foreground">Полный текст пока недоступен.</p>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              <span>Источник:</span>
              <a
                href={article.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background"
              >
                Читать на источнике <ExternalLinkIcon className="h-4 w-4" aria-hidden="true" />
              </a>
              {shareFeedbackLabel ? <span className="text-xs text-primary">{shareFeedbackLabel}</span> : null}
            </div>

            <dl className="grid gap-3 rounded-3xl bg-muted/40 p-4 text-sm text-muted-foreground sm:grid-cols-2">
              <div>
                <dt className="text-xs uppercase tracking-wide text-muted-foreground/80">Опубликовано</dt>
                <dd className="font-semibold text-foreground">{publishedLabel}</dd>
              </div>
              {ingestedLabel ? (
                <div>
                  <dt className="text-xs uppercase tracking-wide text-muted-foreground/80">Обновлено</dt>
                  <dd className="font-semibold text-foreground">{ingestedLabel}</dd>
                </div>
              ) : null}
              <div>
                <dt className="text-xs uppercase tracking-wide text-muted-foreground/80">RID</dt>
                <dd className="font-mono text-sm text-muted-foreground/90">{article.ingestion_rid || '—'}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-muted-foreground/80">Перевод</dt>
                <dd className="font-semibold text-foreground">
                  {article.translated ? article.translation_provider || 'Активирован' : 'Нет'}
                </dd>
              </div>
            </dl>

            {tags.length ? (
              <div className="flex flex-wrap gap-2">
                {tags.map(tag => (
                  <span key={tag.id} className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
                    #{tag.slug}
                  </span>
                ))}
              </div>
            ) : null}
          </article>
        ) : null}
      </div>
    </section>
  )
}