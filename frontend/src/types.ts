export type Language = 'ar' | 'en'
export type Governorate = 'Cairo' | 'Giza'

export interface Product {
  id: number
  name: string
  name_ar: string | null
  description: string | null
  description_ar: string | null
  price: string | number
  stock: number
  active: boolean
  image_url: string | null
  category: string | null
  occasion: string | null
  featured: boolean
  best_seller: boolean
}

export interface CartItem {
  productId: number
  quantity: number
}

export interface OrderItemInput {
  product_id: number
  quantity: number
}

export interface OrderCreatePayload {
  customer_name: string
  customer_phone: string
  customer_email: string | null
  receiver_name: string
  receiver_phone: string
  governorate: Governorate
  delivery_area: string
  delivery_address: string
  delivery_date: string
  delivery_slot: string
  card_message: string | null
  sender_name_on_card: string | null
  customer_note: string | null
  items: OrderItemInput[]
}

export interface OrderItemResponse extends OrderItemInput {
  unit_price: string
  subtotal: string
}

export interface OrderResponse extends Omit<OrderCreatePayload, 'items'> {
  id: number
  status: string
  total_price: string
  created_at: string
  items: OrderItemResponse[]
}

export function moneyAmount(value: string | number): number {
  const amount = Number(value)
  return Number.isFinite(amount) ? amount : 0
}
