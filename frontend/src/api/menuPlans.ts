import api from './client'
import type { MenuPlanResponse, PlanStatus } from '../types'

export interface PlanListParams {
  limit?: number
  date?: string
}

export async function fetchPlans(params: PlanListParams = {}): Promise<MenuPlanResponse[]> {
  const { data } = await api.get<MenuPlanResponse[]>('/nutrition/plans/', { params })
  return data
}

export async function fetchPlan(planId: number): Promise<MenuPlanResponse> {
  const { data } = await api.get<MenuPlanResponse>(`/nutrition/plans/${planId}/`)
  return data
}

export async function updatePlanStatus(planId: number, status: PlanStatus) {
  const { data } = await api.patch<MenuPlanResponse>(`/nutrition/plans/${planId}/`, { status })
  return data
}

export interface MealUpdatePayload {
  qty?: number
  time_hint?: string
  item_id?: number
  user_note?: string | null
}

export async function updatePlanMeal(planId: number, mealId: number, payload: MealUpdatePayload) {
  const { data } = await api.patch<MenuPlanResponse>(`/nutrition/plans/${planId}/meals/${mealId}/`, payload)
  return data
}

export interface MenuItemSearchResult {
  id: number
  title: string
  price?: number | null
  tags?: string[] | null
}

export async function searchMenuItems(query: string, limit = 8): Promise<MenuItemSearchResult[]> {
  const { data } = await api.get<MenuItemSearchResult[]>(`/catalog/items/`, {
    params: { search: query, limit },
  })
  return data
}