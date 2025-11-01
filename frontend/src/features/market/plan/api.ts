import api from '../../../api/client'
import type {
  MarketPlanSubmissionPayload,
  MarketPlanSubmissionResponse,
} from '../../../types/market'
import { planSubmissionSchema } from './form'

export async function submitPlanItem(
  payload: MarketPlanSubmissionPayload,
): Promise<MarketPlanSubmissionResponse> {
  const normalized = planSubmissionSchema.parse(payload)
  const { data } = await api.post<MarketPlanSubmissionResponse>(
    '/v1/market/plan/',
    normalized,
  )
  return data
}
