import { useEffect, useState } from 'react'
import { getProducts } from './products'
import type { Product } from '../types'
import { useCart } from '../context/CartContext'

export function useProducts() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [version, setVersion] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(false)
    getProducts(controller.signal)
      .then(setProducts)
      .catch(() => { if (!controller.signal.aborted) setError(true) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
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
