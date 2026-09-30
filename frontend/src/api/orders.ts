import { apiRequest } from './client'
import type { OrderCreatePayload, OrderResponse } from '../types'

export function createOrder(payload: OrderCreatePayload): Promise<OrderResponse> {
  return apiRequest<OrderResponse>('/orders', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
