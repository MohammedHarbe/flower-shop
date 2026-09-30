import { apiRequest } from './client'
import type { Product } from '../types'

export function getProducts(signal?: AbortSignal): Promise<Product[]> {
  return apiRequest<Product[]>('/products', { signal })
}

export function getProduct(id: number, signal?: AbortSignal): Promise<Product> {
  return apiRequest<Product>(`/products/${id}`, { signal })
}
