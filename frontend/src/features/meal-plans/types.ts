import type { MealTypeId } from '../../types/meal-plan'

export interface PlanSlot {
  date: string | null
  mealType: MealTypeId | null
}
