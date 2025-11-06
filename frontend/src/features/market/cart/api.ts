import api from '../../../api/client'
import type {
  MarketCartCheckoutPayload,
  MarketCartCheckoutResponse,
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

export async function checkoutCart(
  cartId: number,
  payload: MarketCartCheckoutPayload = {},
): Promise<MarketCartCheckoutResponse> {
  const normalized: Record<string, unknown> = {}
  if (payload.pay_with_wallet) {
    normalized.pay_with_wallet = true
    if (payload.wallet_currency) {
      normalized.wallet_currency = payload.wallet_currency
    }
  } else if (payload.wallet_currency) {
    normalized.wallet_currency = payload.wallet_currency
  }
  if (payload.metadata) {
    normalized.metadata = payload.metadata
  }
  const { data } = await api.post<MarketCartCheckoutResponse>(
    `/v1/market/carts/${cartId}/checkout/`,
    normalized,
  )
  return data
}
