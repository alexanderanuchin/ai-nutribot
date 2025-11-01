import api from '../../../api/client'
import type {
  MarketCartSubmissionPayload,
  MarketCartSubmissionResponse,
} from '../../../types/market'
import { cartSubmissionSchema } from './form'

export async function submitCartItem(
  payload: MarketCartSubmissionPayload,
): Promise<MarketCartSubmissionResponse> {
  const normalized = cartSubmissionSchema.parse(payload)
  const { data } = await api.post<MarketCartSubmissionResponse>(
    '/v1/market/cart/',
    normalized,
  )
  return data
}
