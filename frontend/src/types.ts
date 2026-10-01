export type Language = 'ar' | 'en'
export type Governorate = 'Cairo' | 'Giza'
export type DeliverySlot = 'morning' | 'afternoon' | 'evening'

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
  idempotency_key: string
  customer_name: string
  customer_phone: string
  customer_email: string | null
  receiver_name: string
  receiver_phone: string
  governorate: Governorate
  delivery_area: string
  delivery_address: string
  delivery_date: string
  delivery_slot: DeliverySlot
  card_message: string | null
  sender_name_on_card: string | null
  customer_note: string | null
  items: OrderItemInput[]
}

export interface OrderItemResponse extends OrderItemInput {
  unit_price: string
  subtotal: string
}

export interface OrderResponse extends Omit<OrderCreatePayload, 'items' | 'idempotency_key' | 'delivery_slot'> {
  id: number
  idempotency_key: string | null
  delivery_slot: string
  status: string
  total_price: string
  created_at: string
  notified_at: string | null
  items: OrderItemResponse[]
}

export function moneyAmount(value: string | number): number {
  const amount = Number(value)
  return Number.isFinite(amount) ? amount : 0
}
