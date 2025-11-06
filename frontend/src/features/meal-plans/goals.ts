import type { Goal, Profile } from '../../types'
import type { MealPlanNutritionTotals } from '../../types/meal-plan'

export interface PlanGoalPreset {
  value: Goal
  label: string
  description: string
  calorieMultiplier: number
  proteinRatio: number
  fatRatio: number
  proteinPerKg: number
}

const DEFAULT_FALLBACK_CALORIES = 2000
const PROTEIN_CAL_PER_GRAM = 4
const CARB_CAL_PER_GRAM = 4
const FAT_CAL_PER_GRAM = 9

export const PLAN_GOAL_PRESETS: Record<Goal, PlanGoalPreset> = {
  lose: {
    value: 'lose',
    label: 'Снижение веса',
    description: 'Умеренный дефицит ~20% с повышенным белком для сохранения мышц.',
    calorieMultiplier: 0.8,
    proteinRatio: 0.3,
    fatRatio: 0.28,
    proteinPerKg: 1.9,
  },
  maintain: {
    value: 'maintain',
    label: 'Поддержание',
    description: 'Баланс калорий на уровне поддержания и умеренный белок.',
    calorieMultiplier: 1,
    proteinRatio: 0.26,
    fatRatio: 0.27,
    proteinPerKg: 1.6,
  },
  gain: {
    value: 'gain',
    label: 'Набор массы',
    description: 'Профицит ~15% с упором на углеводы для роста.',
    calorieMultiplier: 1.15,
    proteinRatio: 0.24,
    fatRatio: 0.27,
    proteinPerKg: 1.6,
  },
  recomp: {
    value: 'recomp',
    label: 'Рекомпозиция',
    description: 'Небольшой дефицит ~10% и высокий белок для одновременного жиросжигания и роста.',
    calorieMultiplier: 0.9,
    proteinRatio: 0.32,
    fatRatio: 0.26,
    proteinPerKg: 2,
  },
}

export const PLAN_GOAL_OPTIONS = Object.values(PLAN_GOAL_PRESETS)

export function getPlanGoalPreset(goal: Goal | undefined | null): PlanGoalPreset {
  if (!goal || !PLAN_GOAL_PRESETS[goal]) {
    return PLAN_GOAL_PRESETS.maintain
  }
  return PLAN_GOAL_PRESETS[goal]
}

export function formatCalorieDelta(multiplier: number): string {
  if (multiplier === 1) {
    return '0%'
  }
  const delta = Math.round(Math.abs(multiplier - 1) * 100)
  return multiplier > 1 ? `+${delta}%` : `-${delta}%`
}

export function recommendTargetsForGoal({
  goal,
  profile,
  fallback,
}: {
  goal: Goal
  profile?: Profile
  fallback?: MealPlanNutritionTotals
}): MealPlanNutritionTotals {
  const preset = getPlanGoalPreset(goal)

  const baseCalories = (() => {
    const recommended = profile?.metrics?.recommended_calories
    if (recommended && recommended > 0) return recommended
    const tdee = profile?.metrics?.tdee
    if (tdee && tdee > 0) return tdee
    if (fallback?.calories && fallback.calories > 0) return fallback.calories
    return DEFAULT_FALLBACK_CALORIES
  })()

  const totalCalories = Math.round(baseCalories * preset.calorieMultiplier)
  const weight = profile?.weight_kg ?? null

  const proteinByRatio = (totalCalories * preset.proteinRatio) / PROTEIN_CAL_PER_GRAM
  const proteinByWeight = weight ? weight * preset.proteinPerKg : 0
  const proteinGrams = Math.max(Math.round(proteinByRatio), Math.round(proteinByWeight))

  const fatGrams = Math.max(0, Math.round((totalCalories * preset.fatRatio) / FAT_CAL_PER_GRAM))
  const proteinCalories = proteinGrams * PROTEIN_CAL_PER_GRAM
  const fatCalories = fatGrams * FAT_CAL_PER_GRAM
  const remainingCalories = Math.max(totalCalories - proteinCalories - fatCalories, 0)
  const carbsGrams = Math.max(0, Math.round(remainingCalories / CARB_CAL_PER_GRAM))

  return {
    calories: totalCalories,
    protein_g: proteinGrams,
    fat_g: fatGrams,
    carbs_g: carbsGrams,
  }
}
