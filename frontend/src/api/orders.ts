import { apiRequest } from './client'
import type { DeliveryZone, OrderConfirmation, OrderCreatePayload, PublicConfig } from '../types'

let publicConfigRequest: Promise<PublicConfig> | null = null

export function getDeliveryZones(): Promise<DeliveryZone[]> {
  return apiRequest<DeliveryZone[]>('/delivery-zones')
}

export function getPublicConfig(): Promise<PublicConfig> {
  if (!publicConfigRequest) {
    publicConfigRequest = apiRequest<PublicConfig>('/public-config').catch((error: unknown) => {
      publicConfigRequest = null
      throw error
    })
  }
  return publicConfigRequest
}

export function createOrder(payload: OrderCreatePayload): Promise<OrderConfirmation> {
  return apiRequest<OrderConfirmation>('/orders', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
