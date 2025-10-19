import { ExternalLinkIcon } from 'lucide-react'
import type { NewsFeedItem } from '../../../types/feed'

export interface NewsCardProps {
  item: NewsFeedItem
}

function formatPublished(date: string): string {
  try {
    return new Intl.DateTimeFormat('ru-RU', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(date))
  } catch (_error) {
    return date
  }
}

export function NewsCard({ item }: NewsCardProps) {
  return (
    <article className="group flex gap-4 rounded-3xl border border-border/60 bg-background/90 p-4 shadow-soft transition hover:-translate-y-0.5 hover:shadow-lg">
      {item.preview_image_url ? (
        <div className="hidden h-24 w-24 shrink-0 overflow-hidden rounded-2xl sm:block">
          <img
            src={item.preview_image_url}
            alt={item.title}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        </div>
      ) : null}
      <div className="flex flex-1 flex-col gap-2">
        <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
          <span className="font-medium uppercase tracking-wide">{item.source_name}</span>
          <time dateTime={item.published_at}>{formatPublished(item.published_at)}</time>
        </div>
        <h3 className="text-base font-semibold text-foreground">{item.title}</h3>
        <p className="line-clamp-3 text-sm text-muted-foreground">{item.lead}</p>
        <div className="mt-auto flex flex-wrap items-center gap-2 pt-2">
          {item.tags.slice(0, 3).map(tag => (
            <span
              key={tag.id}
              className="rounded-full bg-primary/10 px-2 py-1 text-[11px] font-semibold text-primary"
            >
              #{tag.slug}
            </span>
          ))}
          <a
            href={item.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-auto inline-flex items-center gap-1 rounded-full bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground transition hover:bg-primary/90"
          >
            Источник <ExternalLinkIcon className="h-3 w-3" aria-hidden="true" />
          </a>
        </div>
      </div>
    </article>
  )
}

export default NewsCard