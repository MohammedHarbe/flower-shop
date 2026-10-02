import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { PropsWithChildren } from 'react'
import type { CartItem, Product } from '../types'

const CART_KEY = 'toneflowers-cart-v1'

function quantityInteger(value: number): number {
  return Number.isFinite(value) ? Math.max(1, Math.min(99, Math.trunc(value))) : 1
}

function readStoredCart(): CartItem[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(CART_KEY) || '[]')
    if (!Array.isArray(value)) return []
    const merged = new Map<number, number>()
    for (const item of value) {
      if (
        typeof item === 'object' && item !== null &&
        Number.isInteger(item.productId) && item.productId > 0 &&
        Number.isInteger(item.quantity) && item.quantity > 0
      ) {
        merged.set(item.productId, Math.min(99, (merged.get(item.productId) || 0) + item.quantity))
      }
    }
    return Array.from(merged, ([productId, quantity]) => ({ productId, quantity }))
  } catch {
    return []
  }
}

type CartContextValue = {
  items: CartItem[]
  count: number
  addItem: (product: Product, quantity: number) => void
  updateQuantity: (productId: number, quantity: number) => void
  removeItem: (productId: number) => void
  clearCart: () => void
}

const CartContext = createContext<CartContextValue | null>(null)

export function CartProvider({ children }: PropsWithChildren) {
  const [items, setItems] = useState<CartItem[]>(readStoredCart)

  useEffect(() => {
    try { localStorage.setItem(CART_KEY, JSON.stringify(items)) } catch { /* Cart still works in memory. */ }
  }, [items])

  const value = useMemo<CartContextValue>(
    () => ({
      items,
      count: items.reduce((sum, item) => sum + item.quantity, 0),
      addItem(product, quantity) {
        if (!product.active || quantity <= 0) return
        setItems((current) => {
          const existing = current.find((item) => item.productId === product.id)
          const nextQuantity = (existing?.quantity || 0) + quantityInteger(quantity)
          if (existing) {
            return current.map((item) =>
              item.productId === product.id ? { ...item, quantity: nextQuantity } : item,
            )
          }
          return [...current, { productId: product.id, quantity: nextQuantity }]
        })
      },
      updateQuantity(productId, quantity) {
        setItems((current) =>
          current.map((item) =>
            item.productId === productId ? { ...item, quantity: quantityInteger(quantity) } : item,
          ),
        )
      },
      removeItem(productId) {
        setItems((current) => current.filter((item) => item.productId !== productId))
      },
      clearCart() {
        setItems([])
      },
    }),
    [items],
  )

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>
}

export function useCart(): CartContextValue {
  const context = useContext(CartContext)
  if (!context) throw new Error('useCart must be used inside CartProvider')
  return context
}
