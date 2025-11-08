import { api } from './client'

export type ReviewTargetType = 'store' | 'product' | 'recipe' | 'plan'

export interface ReviewAuthor {
  id: number
  username: string
  first_name?: string | null
  last_name?: string | null
}

export interface Review {
  id: number
  author: ReviewAuthor
  rating: number
  text: string
  created_at: string
  updated_at: string
}

export interface ReviewListParams {
  targetType: ReviewTargetType
  targetId: number
}

export interface CreateReviewPayload {
  targetType: ReviewTargetType
  targetId: number
  rating: number
  text?: string
}

function normalizeTargetType(value: ReviewTargetType): string {
  switch (value) {
    case 'store':
    case 'product':
    case 'recipe':
      return value
    case 'plan':
      return 'plan'
    default:
      return value
  }
}

export async function fetchReviews(params: ReviewListParams): Promise<Review[]> {
  const targetType = normalizeTargetType(params.targetType)
  const { data } = await api.get<Review[]>('/reviews/', {
    params: { target_type: targetType, target_id: params.targetId },
  })
  return data
}

export async function createReview(payload: CreateReviewPayload): Promise<Review> {
  const targetType = normalizeTargetType(payload.targetType)
  const { data } = await api.post<Review>('/reviews/', {
    target_type: targetType,
    target_id: payload.targetId,
    rating: payload.rating,
    text: payload.text,
  })
  return data
}
