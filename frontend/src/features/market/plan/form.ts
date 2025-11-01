import { z } from 'zod'

import type { MarketPlanSubmissionPayload } from '../../../types/market'

export const planSubmissionSchema = z.object({
  recipe_id: z.number().int().positive(),
  servings: z
    .number()
    .min(0)
    .refine(value => Number.isFinite(value), { message: 'Некорректное значение порций' })
    .default(1),
})

export type PlanSubmissionInput = z.infer<typeof planSubmissionSchema>

export function createPlanSubmissionPayload(
  payload: MarketPlanSubmissionPayload,
): PlanSubmissionInput {
  return planSubmissionSchema.parse(payload)
}
