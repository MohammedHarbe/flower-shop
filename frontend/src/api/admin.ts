import { apiRequest } from './client'
import type { DeliveryZone, OrderResponse, Product } from '../types'

type AdminLogin = { email: string; password: string }
type ProductInput = Omit<Product, 'id'>

function adminRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  return apiRequest<T>(path, {
    ...options,
    credentials: 'include',
    headers: {
      'X-Requested-With': 'ToneFlowersAdmin',
      ...options.headers,
    },
  })
}

export function adminLogin(payload: AdminLogin): Promise<{ email: string }> {
  return adminRequest('/admin/login', { method: 'POST', body: JSON.stringify(payload) })
}

export function adminLogout(): Promise<{ ok: boolean }> {
  return adminRequest('/admin/logout', { method: 'POST', body: '{}' })
}

export function adminMe(): Promise<{ email: string }> {
  return adminRequest('/admin/me')
}

export function adminProducts(): Promise<Product[]> {
  return adminRequest('/admin/products')
}

export function saveProduct(payload: ProductInput, id?: number): Promise<Product> {
  return adminRequest(id ? `/products/${id}` : '/products', {
    method: id ? 'PATCH' : 'POST',
    body: JSON.stringify(payload),
  })
}

export function adminOrders(): Promise<OrderResponse[]> {
  return adminRequest('/orders')
}

export function updateOrderStatus(orderId: number, status: string): Promise<OrderResponse> {
  return adminRequest(`/orders/${orderId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
}

export function updatePaymentStatus(orderId: number, status: string): Promise<OrderResponse> {
  return adminRequest(`/orders/${orderId}/payment-status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
}

export function adminDeliveryZones(): Promise<DeliveryZone[]> {
  return adminRequest('/delivery-zones/admin')
}

export function updateDeliveryZone(zoneId: number, payload: Pick<DeliveryZone, 'name_en' | 'name_ar' | 'fee' | 'active' | 'sort_order'>): Promise<DeliveryZone> {
  return adminRequest(`/delivery-zones/${zoneId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}