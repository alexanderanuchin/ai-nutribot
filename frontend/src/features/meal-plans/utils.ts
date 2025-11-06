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
