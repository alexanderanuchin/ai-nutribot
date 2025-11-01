import { afterEach, describe, expect, test, vi } from 'vitest'

import api from '../api/client'
import { submitCartItem } from '../features/market/cart/api'
import { createCartSubmissionPayload } from '../features/market/cart/form'
import { submitPlanItem } from '../features/market/plan/api'
import { createPlanSubmissionPayload } from '../features/market/plan/form'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('market cart submission', () => {
  test('sends normalized payload with defaults applied', async () => {
    const serverResponse = {
      status: 'created' as const,
      cart: {
        id: 10,
        store_id: 4,
        currency: 'RUB',
        items_count: 1,
        items_quantity: 1,
      },
      item: {
        id: 15,
        product_id: 42,
        quantity: 1,
        price_snapshot: '320.00',
      },
    }

    const postSpy = vi
      .spyOn(api, 'post')
      .mockResolvedValue({ data: serverResponse } as any)

    const result = await submitCartItem({ product_id: 42 })

    expect(postSpy).toHaveBeenCalledWith('/v1/market/cart/', {
      product_id: 42,
      quantity: 1,
    })
    expect(result).toBe(serverResponse)
  })

  test('rejects negative quantities at the form layer', () => {
    expect(() => createCartSubmissionPayload({ product_id: 7, quantity: -2 })).toThrow()
  })
})

describe('market plan submission', () => {
  test('passes through decimal servings and returns response payload', async () => {
    const serverResponse = {
      status: 'updated' as const,
      plan: {
        id: 3,
        title: 'Мой план питания',
        items_count: 2,
        total_servings: 5.5,
      },
      item: {
        id: 9,
        recipe_id: 101,
        servings: 2.5,
      },
    }

    const postSpy = vi
      .spyOn(api, 'post')
      .mockResolvedValue({ data: serverResponse } as any)

    const result = await submitPlanItem({ recipe_id: 101, servings: 2.5 })

    expect(postSpy).toHaveBeenCalledWith('/v1/market/plan/', {
      recipe_id: 101,
      servings: 2.5,
    })
    expect(result).toBe(serverResponse)
  })

  test('rejects NaN servings input', () => {
    expect(() => createPlanSubmissionPayload({ recipe_id: 11, servings: Number.NaN })).toThrow()
  })
})
