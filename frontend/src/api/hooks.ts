import { useEffect, useState } from 'react'
import { getProducts } from './products'
import type { Product } from '../types'
import { useCart } from '../context/CartContext'

const PRODUCTS_REQUEST_TIMEOUT_MS = 8_000

export function useProducts() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [version, setVersion] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    let active = true
    const timeoutId = setTimeout(() => {
      controller.abort()
    }, PRODUCTS_REQUEST_TIMEOUT_MS)
    setLoading(true)
    setError(false)
    getProducts(controller.signal)
      .then((result) => { if (active) setProducts(result) })
      .catch(() => { if (active) setError(true) })
      .finally(() => {
        clearTimeout(timeoutId)
        if (active) setLoading(false)
      })
    return () => {
      active = false
      clearTimeout(timeoutId)
      controller.abort()
    }
  }, [version])

  return { products, loading, error, retry: () => setVersion((current) => current + 1) }
}

export function useCartProducts() {
  const { items } = useCart()
  const state = useProducts()
  const byId = new Map(state.products.map((product) => [product.id, product]))
  const lines = items.map((item) => ({ ...item, product: byId.get(item.productId) }))
  const hasUnavailable = lines.some(
    (line) => !line.product || !line.product.active || line.product.stock < line.quantity,
  )
  return { ...state, lines, hasUnavailable }
}
