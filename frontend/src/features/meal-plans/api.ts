import api from '../../api/client'
import type {
  MealPlan,
  MealPlanCreatePayload,
  MealPlanItem,
  MealPlanItemPayload,
  MealPlanListResponse,
  MealPlanQueryParams,
  MealPlanUpdatePayload,
} from '../../types/meal-plan'

function normalizePlanPayload(payload: MealPlanCreatePayload | MealPlanUpdatePayload) {
  const next: Record<string, unknown> = { ...payload }
  if (typeof payload.price_amount === 'number') {
    next.price_amount = payload.price_amount.toFixed(2)
  } else if (payload.price_amount === null) {
    next.price_amount = null
  }
  if (payload.price_currency) {
    next.price_currency = payload.price_currency.toUpperCase()
  }
  return next
}

export async function fetchMealPlans(params: MealPlanQueryParams = {}): Promise<MealPlanListResponse> {
  const query: Record<string, unknown> = { ...params }
  if (typeof params.published === 'boolean') {
    query.published = params.published ? 'true' : 'false'
  }
  if (params.scope) {
    query.scope = params.scope
  }
  const { data } = await api.get<MealPlanListResponse>('/v1/market/meal-plans/', {
    params: query,
  })
  return data
}

export async function fetchMealPlan(planId: number): Promise<MealPlan> {
  const { data } = await api.get<MealPlan>(`/v1/market/meal-plans/${planId}/`)
  return data
}

export async function createMealPlan(payload: MealPlanCreatePayload): Promise<MealPlan> {
  const body = normalizePlanPayload(payload)
  const { data } = await api.post<MealPlan>('/v1/market/meal-plans/', body)
  return data
}

export async function updateMealPlan(planId: number, payload: MealPlanUpdatePayload): Promise<MealPlan> {
  const body = normalizePlanPayload(payload)
  const { data } = await api.patch<MealPlan>(`/v1/market/meal-plans/${planId}/`, body)
  return data
}

export async function deleteMealPlan(planId: number): Promise<void> {
  await api.delete(`/v1/market/meal-plans/${planId}/`)
}

function normalizeItemPayload(payload: MealPlanItemPayload) {
  const body: Record<string, unknown> = { ...payload }
  if (typeof payload.servings === 'number') {
    body.servings = payload.servings
  }
  return body
}

export async function createMealPlanItem(payload: MealPlanItemPayload): Promise<MealPlanItem> {
  const body = normalizeItemPayload(payload)
  const { data } = await api.post<MealPlanItem>('/v1/market/meal-plan-items/', body)
  return data
}

export async function updateMealPlanItem(itemId: number, payload: MealPlanItemPayload): Promise<MealPlanItem> {
  const body = normalizeItemPayload(payload)
  const { data } = await api.patch<MealPlanItem>(`/v1/market/meal-plan-items/${itemId}/`, body)
  return data
}

export async function deleteMealPlanItem(itemId: number): Promise<void> {
  await api.delete(`/v1/market/meal-plan-items/${itemId}/`)
}
