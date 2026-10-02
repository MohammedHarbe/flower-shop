export type Language = 'ar' | 'en'
export type Governorate = 'Cairo' | 'Giza'
export type DeliverySlot = 'morning' | 'afternoon' | 'evening'
export type PaymentMethod = 'vodafone_cash' | 'cash_on_delivery'
export type PaymentStatus = 'awaiting_payment' | 'unpaid' | 'paid'

export interface DeliveryZone {
  id: number
  governorate: Governorate
  name_en: string
  name_ar: string | null
  fee: string | number
  active: boolean
  sort_order: number
}

export interface PublicConfig {
  whatsapp_number: string
  vodafone_cash_number: string
  supported_payment_methods: PaymentMethod[]
}

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
  payment_method: PaymentMethod
  delivery_zone_id: number | null
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
  payment_status: PaymentStatus
  status: string
  subtotal: string
  delivery_fee: string
  total_price: string
  created_at: string
  notified_at: string | null
  items: OrderItemResponse[]
}

export interface OrderConfirmation {
  id: number
  governorate: Governorate | null
  delivery_area: string
  delivery_date: string
  delivery_slot: string
  payment_method: PaymentMethod
  payment_status: PaymentStatus
  status: string
  subtotal: string
  delivery_fee: string
  total_price: string
}

export function moneyAmount(value: string | number): number {
  const amount = Number(value)
  return Number.isFinite(amount) ? amount : 0
}
