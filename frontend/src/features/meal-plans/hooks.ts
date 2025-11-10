import { useMutation, useQuery, useQueryClient, type UseMutationOptions, type UseQueryOptions } from '@tanstack/react-query'

import {
  createMealPlan,
  createMealPlanItem,
  deleteMealPlan,
  deleteMealPlanItem,
  fetchMealPlan,
  fetchMealPlans,
  purchaseMealPlan,
  updateMealPlan,
  updateMealPlanItem,
} from './api'
import type {
  MealPlan,
  MealPlanCreatePayload,
  MealPlanItem,
  MealPlanItemPayload,
  MealPlanListResponse,
  MealPlanPurchaseResponse,
  MealPlanQueryParams,
  MealPlanUpdatePayload,
} from '../../types/meal-plan'

export const mealPlanKeys = {
  all: ['mealPlans'] as const,
  lists: () => [...mealPlanKeys.all, 'list'] as const,
  list: (params: MealPlanQueryParams = {}) => [...mealPlanKeys.lists(), params] as const,
  detail: (planId: number) => [...mealPlanKeys.all, 'detail', planId] as const,
}

type MealPlanListKey = ReturnType<typeof mealPlanKeys.list>
type MealPlanDetailKey = ReturnType<typeof mealPlanKeys.detail>

export function useMealPlansQuery(
  params: MealPlanQueryParams,
  options?: UseQueryOptions<MealPlanListResponse, Error, MealPlanListResponse, MealPlanListKey>,
) {
  return useQuery<MealPlanListResponse, Error>({
    queryKey: mealPlanKeys.list(params),
    queryFn: () => fetchMealPlans(params),
    ...options,
  })
}

export function useMealPlanQuery(
  planId: number | null,
  options?: UseQueryOptions<MealPlan, Error, MealPlan, MealPlanDetailKey>,
) {
  const detailKey = mealPlanKeys.detail(typeof planId === 'number' ? planId : -1)
  return useQuery<MealPlan, Error>({
    queryKey: detailKey,
    queryFn: () => {
      if (!planId) {
        throw new Error('planId is required')
      }
      return fetchMealPlan(planId)
    },
    enabled: Boolean(planId) && (options?.enabled ?? true),
    ...options,
  })
}

export function useCreateMealPlanMutation(
  options?: UseMutationOptions<MealPlan, Error, MealPlanCreatePayload>,
) {
  const queryClient = useQueryClient()
  return useMutation<MealPlan, Error, MealPlanCreatePayload>({
    mutationFn: createMealPlan,
    onSuccess: (plan, variables, context) => {
      queryClient.invalidateQueries({ queryKey: mealPlanKeys.lists() })
      if (options?.onSuccess) {
        options.onSuccess(plan, variables, context)
      }
    },
    ...options,
  })
}

export function useUpdateMealPlanMutation(
  planId: number,
  options?: UseMutationOptions<MealPlan, Error, MealPlanUpdatePayload>,
) {
  const queryClient = useQueryClient()
  return useMutation<MealPlan, Error, MealPlanUpdatePayload>({
    mutationFn: payload => updateMealPlan(planId, payload),
    onSuccess: (plan, variables, context) => {
      queryClient.invalidateQueries({ queryKey: mealPlanKeys.detail(planId) })
      queryClient.invalidateQueries({ queryKey: mealPlanKeys.lists() })
      if (options?.onSuccess) {
        options.onSuccess(plan, variables, context)
      }
    },
    ...options,
  })
}

export function useDeleteMealPlanMutation(
  options?: UseMutationOptions<void, Error, number>,
) {
  const queryClient = useQueryClient()
  return useMutation<void, Error, number>({
    mutationFn: deleteMealPlan,
    onSuccess: (_result, planId, context) => {
      queryClient.invalidateQueries({ queryKey: mealPlanKeys.lists() })
      queryClient.removeQueries({ queryKey: mealPlanKeys.detail(planId) })
      if (options?.onSuccess) {
        options.onSuccess(_result, planId, context)
      }
    },
    ...options,
  })
}

export function usePurchaseMealPlanMutation(
  planId: number,
  options?: UseMutationOptions<MealPlanPurchaseResponse, unknown, void>,
) {
  const queryClient = useQueryClient()
  return useMutation<MealPlanPurchaseResponse, unknown, void>({
    mutationFn: () => purchaseMealPlan(planId),
    onSuccess: (response, variables, context) => {
      // Обновить кэш детали
      queryClient.setQueryData(mealPlanKeys.detail(planId), response.plan)
      // И обновить кэш списков
      queryClient.setQueriesData<MealPlanListResponse>({ queryKey: mealPlanKeys.lists() }, previous => {
        if (!previous) return previous
        return {
          ...previous,
          results: previous.results.map(item => (item.id === response.plan.id ? response.plan : item)),
        }
      })
      options?.onSuccess?.(response, variables, context)
    },
    ...options,
  })
}

export function useCreateMealPlanItemMutation(
  options?: UseMutationOptions<MealPlanItem, Error, MealPlanItemPayload>,
) {
  const queryClient = useQueryClient()
  return useMutation<MealPlanItem, Error, MealPlanItemPayload>({
    mutationFn: createMealPlanItem,
    onSuccess: (item, variables, context) => {
      queryClient.invalidateQueries({ queryKey: mealPlanKeys.detail(variables.meal_plan) })
      if (options?.onSuccess) {
        options.onSuccess(item, variables, context)
      }
    },
    ...options,
  })
}

export function useUpdateMealPlanItemMutation(
  planId: number,
  options?: UseMutationOptions<MealPlanItem, Error, { itemId: number; payload: MealPlanItemPayload }>,
) {
  const queryClient = useQueryClient()
  return useMutation<MealPlanItem, Error, { itemId: number; payload: MealPlanItemPayload }>({
    mutationFn: ({ itemId, payload }) => updateMealPlanItem(itemId, payload),
    onSuccess: (item, variables, context) => {
      queryClient.invalidateQueries({ queryKey: mealPlanKeys.detail(planId) })
      if (options?.onSuccess) {
        options.onSuccess(item, variables, context)
      }
    },
    ...options,
  })
}

export function useDeleteMealPlanItemMutation(
  planId: number,
  options?: UseMutationOptions<void, Error, number>,
) {
  const queryClient = useQueryClient()
  return useMutation<void, Error, number>({
    mutationFn: deleteMealPlanItem,
    onSuccess: (_result, itemId, context) => {
      queryClient.invalidateQueries({ queryKey: mealPlanKeys.detail(planId) })
      if (options?.onSuccess) {
        options.onSuccess(_result, itemId, context)
      }
    },
    ...options,
  })
}
