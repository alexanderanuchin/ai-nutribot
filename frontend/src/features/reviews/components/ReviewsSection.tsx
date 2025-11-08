import { useState } from 'react'
import { isAxiosError } from 'axios'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'

import { createReview, fetchReviews, type Review, type ReviewTargetType } from '../../../api/reviews'
import { Button, Card, Rating, Skeleton, useToast } from '../../../components/ui'

interface ReviewsSectionProps {
  targetType: ReviewTargetType
  targetId: number
  className?: string
}

const queryKey = (targetType: ReviewTargetType, targetId: number) => ['reviews', targetType, targetId] as const

const STARS = [1, 2, 3, 4, 5]

export function ReviewsSection({ targetType, targetId, className }: ReviewsSectionProps) {
  const [open, setOpen] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [ratingValue, setRatingValue] = useState<number>(5)
  const [textValue, setTextValue] = useState<string>('')
  const { notify } = useToast()
  const queryClient = useQueryClient()

  const reviewsQuery = useQuery({
    queryKey: queryKey(targetType, targetId),
    queryFn: () => fetchReviews({ targetType, targetId }),
    enabled: open,
    staleTime: 60_000,
  })

  const mutation = useMutation({
    mutationFn: () =>
      createReview({
        targetType,
        targetId,
        rating: ratingValue,
        text: textValue.trim() || undefined,
      }),
    onSuccess: review => {
      setFormOpen(false)
      setTextValue('')
      queryClient.setQueryData<Review[]>(queryKey(targetType, targetId), previous =>
        previous ? [review, ...previous] : [review],
      )
      notify({
        title: 'Спасибо за отзыв!',
        description: 'Мы учтём вашу оценку и улучшим рекомендации.',
        tone: 'success',
      })
    },
    onError: (error: unknown) => {
      let message = 'Не удалось сохранить отзыв'
      if (isAxiosError(error)) {
        const detail = (error.response?.data as any)?.detail
        if (typeof detail === 'string') {
          message = detail
        }
      } else if (error instanceof Error) {
        message = error.message
      }
      notify({ title: 'Ошибка', description: message, tone: 'destructive' })
    },
  })

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (mutation.isPending) return
    mutation.mutate()
  }

  const renderReviews = () => {
    if (reviewsQuery.isLoading) {
      return (
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      )
    }
    if (reviewsQuery.isError) {
      return (
        <Card elevation={1} className="border-destructive/50 bg-destructive/10 text-sm text-destructive">
          Не удалось загрузить отзывы. Попробуйте позже.
        </Card>
      )
    }
    const reviews = reviewsQuery.data ?? []
    if (reviews.length === 0) {
      return <div className="text-sm text-muted-foreground">Пока нет отзывов — станьте первым!</div>
    }
    return (
      <div className="space-y-3">
        {reviews.map(review => (
          <Card key={review.id} elevation={1} className="border-border/70 bg-background/70 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="text-sm font-semibold text-foreground">
                {review.author.first_name || review.author.last_name
                  ? `${review.author.first_name ?? ''} ${review.author.last_name ?? ''}`.trim()
                  : review.author.username}
              </div>
              <Rating value={review.rating} size="sm" />
            </div>
            {review.text ? (
              <p className="mt-2 text-sm text-muted-foreground whitespace-pre-wrap">{review.text}</p>
            ) : null}
            <div className="mt-2 text-xs text-muted-foreground">
              {new Date(review.created_at).toLocaleString('ru-RU', {
                day: 'numeric',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </div>
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className={clsx('space-y-3', className)}>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="w-full justify-between rounded-2xl border border-border/60 bg-muted/20"
        onClick={() => setOpen(value => !value)}
      >
        <span className="text-sm font-semibold">Отзывы</span>
        <span className="text-xs text-muted-foreground">{open ? 'Скрыть' : 'Показать'}</span>
      </Button>

      {open ? (
        <div className="space-y-4 rounded-2xl border border-border/40 bg-muted/10 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-sm font-semibold text-foreground">Впечатления клиентов</div>
            <Button
              type="button"
              variant={formOpen ? 'secondary' : 'primary'}
              size="sm"
              onClick={() => setFormOpen(value => !value)}
            >
              {formOpen ? 'Отменить' : 'Оставить отзыв'}
            </Button>
          </div>

          {formOpen ? (
            <form onSubmit={handleSubmit} className="space-y-3 rounded-xl border border-border/50 bg-background/80 p-4">
              <div className="text-sm font-semibold text-foreground">Как вы оцениваете опыт?</div>
              <div className="flex items-center gap-1">
                {STARS.map(star => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setRatingValue(star)}
                    className={clsx(
                      'flex h-9 w-9 items-center justify-center rounded-full border transition',
                      ratingValue >= star
                        ? 'border-warning bg-warning/20 text-warning'
                        : 'border-border/70 bg-muted/30 text-muted-foreground',
                    )}
                    aria-label={`Оценка ${star}`}
                  >
                    {star}
                  </button>
                ))}
              </div>
              <label className="flex flex-col gap-2 text-xs font-medium text-muted-foreground">
                Комментарий (по желанию)
                <textarea
                  value={textValue}
                  onChange={event => setTextValue(event.target.value)}
                  rows={3}
                  className="w-full rounded-xl border border-border/60 bg-background/80 px-3 py-2 text-sm text-foreground shadow-sm focus:border-primary focus:outline-none"
                  maxLength={800}
                  placeholder="Расскажите, что понравилось и что можно улучшить"
                />
              </label>
              <div className="flex items-center justify-end gap-2">
                <Button type="button" variant="ghost" size="sm" onClick={() => setFormOpen(false)}>
                  Закрыть
                </Button>
                <Button type="submit" variant="primary" size="sm" loading={mutation.isPending}>
                  Отправить
                </Button>
              </div>
            </form>
          ) : null}

          {renderReviews()}
        </div>
      ) : null}
    </div>
  )
}

export default ReviewsSection
