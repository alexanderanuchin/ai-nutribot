import { z } from 'zod'

import type { MarketCartSubmissionPayload } from '../../../types/market'

export const cartSubmissionSchema = z.object({
  product_id: z.number().int().positive(),
  quantity: z.number().int().min(0).default(1),
})

export type CartSubmissionInput = z.infer<typeof cartSubmissionSchema>

export function createCartSubmissionPayload(
  payload: MarketCartSubmissionPayload,
): CartSubmissionInput {
  return cartSubmissionSchema.parse(payload)
}
