import { differenceInCalendarDays } from 'date-fns'

import type { MealPlan, MealPlanNutritionTotals } from '../../types/meal-plan'

export const EMPTY_NUTRITION: MealPlanNutritionTotals = {
  calories: 0,
  protein_g: 0,
  fat_g: 0,
  carbs_g: 0,
}

export function formatNutritionValue(value: number, precision = 0): string {
  return value.toLocaleString('ru-RU', {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  })
}

export function sumNutrition(a: MealPlanNutritionTotals, b: MealPlanNutritionTotals): MealPlanNutritionTotals {
  return {
    calories: a.calories + b.calories,
    protein_g: a.protein_g + b.protein_g,
    fat_g: a.fat_g + b.fat_g,
    carbs_g: a.carbs_g + b.carbs_g,
  }
}

export function computeCoverage(
  totals: MealPlanNutritionTotals,
  target: MealPlanNutritionTotals,
): MealPlanNutritionTotals {
  return {
    calories: target.calories ? (totals.calories / target.calories) * 100 : 0,
    protein_g: target.protein_g ? (totals.protein_g / target.protein_g) * 100 : 0,
    fat_g: target.fat_g ? (totals.fat_g / target.fat_g) * 100 : 0,
    carbs_g: target.carbs_g ? (totals.carbs_g / target.carbs_g) * 100 : 0,
  }
}

export function extractPlanTargets(plan?: MealPlan | null): MealPlanNutritionTotals {
  if (!plan) return EMPTY_NUTRITION
  const targets = plan.metadata?.targets || {}
  return {
    calories: Number(targets.calories) || 0,
    protein_g: Number(targets.protein_g) || 0,
    fat_g: Number(targets.fat_g) || 0,
    carbs_g: Number(targets.carbs_g) || 0,
  }
}

export function calculateMacroShare(value: number, total: number): number {
  if (!total) return 0
  return Math.max(0, Math.min(100, (value / total) * 100))
}

export function getPlanDurationDays(plan: MealPlan): number {
  if (!plan) return 0
  const scheduledDays = plan.daily_breakdown?.filter(day => !day.is_unscheduled) ?? []
  if (scheduledDays.length > 0) {
    return scheduledDays.length
  }

  if (plan.start_date && plan.end_date) {
    const start = new Date(plan.start_date)
    const end = new Date(plan.end_date)
    const diff = differenceInCalendarDays(end, start) + 1
    if (Number.isFinite(diff) && diff > 0) {
      return diff
    }
  }

  return plan.items?.length ? 1 : 0
}

export function computeDailyAverageNutrition(plan: MealPlan): MealPlanNutritionTotals {
  if (!plan) return EMPTY_NUTRITION

  const scheduledDays = plan.daily_breakdown?.filter(day => !day.is_unscheduled) ?? []

  if (scheduledDays.length > 0) {
    const totals = scheduledDays.reduce<MealPlanNutritionTotals>(
      (acc, day) => sumNutrition(acc, day.totals),
      { ...EMPTY_NUTRITION },
    )

    return {
      calories: totals.calories / scheduledDays.length,
      protein_g: totals.protein_g / scheduledDays.length,
      fat_g: totals.fat_g / scheduledDays.length,
      carbs_g: totals.carbs_g / scheduledDays.length,
    }
  }

  const duration = getPlanDurationDays(plan)
  if (!duration) {
    return { ...EMPTY_NUTRITION }
  }

  return {
    calories: plan.nutrition_totals.calories / duration,
    protein_g: plan.nutrition_totals.protein_g / duration,
    fat_g: plan.nutrition_totals.fat_g / duration,
    carbs_g: plan.nutrition_totals.carbs_g / duration,
  }
}
