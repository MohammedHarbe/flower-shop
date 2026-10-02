import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useCartProducts } from '../api/hooks'
import { ApiError } from '../api/client'
import { createOrder, getDeliveryZones, getPublicConfig } from '../api/orders'
import { getProducts } from '../api/products'
import { ProductImage } from '../components/ProductCard'
import { useCart } from '../context/CartContext'
import { useLanguage } from '../context/LanguageContext'
import type { DeliverySlot, DeliveryZone, Governorate, OrderCreatePayload, PaymentMethod, PublicConfig } from '../types'
import { moneyAmount } from '../types'
import { formatMoney, normalizeEgyptianPhone, productName, todayLocal } from '../utils'

type Fields = {
  customer_name: string
  customer_phone: string
  customer_email: string
  receiver_name: string
  receiver_phone: string
  governorate: '' | Governorate
  delivery_area: string
  delivery_address: string
  delivery_date: string
  delivery_slot: '' | DeliverySlot
  card_message: string
  sender_name_on_card: string
  customer_note: string
}

const emptyFields: Fields = {
  customer_name: '', customer_phone: '', customer_email: '', receiver_name: '', receiver_phone: '',
  governorate: '', delivery_area: '', delivery_address: '', delivery_date: '', delivery_slot: '',
  card_message: '', sender_name_on_card: '', customer_note: '',
}

const CHECKOUT_KEY = 'toneflowers-checkout-idempotency-v1'
function newKey(): string {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 0x0f) | 0x40
  bytes[8] = (bytes[8] & 0x3f) | 0x80
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

function keyForCart(signature: string): string {
  try {
    const stored = JSON.parse(sessionStorage.getItem(CHECKOUT_KEY) || 'null') as { key?: string; signature?: string } | null
    if (stored?.signature === signature && stored.key && /^[0-9a-f-]{36}$/i.test(stored.key)) return stored.key
  } catch { /* Session storage may be unavailable. */ }
  const key = newKey()
  try { sessionStorage.setItem(CHECKOUT_KEY, JSON.stringify({ key, signature })) } catch { /* Keep the in-memory key. */ }
  return key
}

function deliveryZoneName(zone: DeliveryZone, language: string): string {
  return language === 'ar' ? zone.name_ar || zone.name_en : zone.name_en
}

export function CheckoutPage() {
  const { t, language } = useLanguage()
  const { items, clearCart } = useCart()
  const { lines, loading, error, retry, hasUnavailable } = useCartProducts()
  const navigate = useNavigate()
  const submittingRef = useRef(false)
  const idempotencyRef = useRef<{ key: string; signature: string } | null>(null)
  const [fields, setFields] = useState<Fields>(emptyFields)
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState('')
  const [zones, setZones] = useState<DeliveryZone[]>([])
  const [zonesLoading, setZonesLoading] = useState(true)
  const [zonesUnavailable, setZonesUnavailable] = useState(false)
  const [publicConfig, setPublicConfig] = useState<PublicConfig | null>(null)
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod | ''>('')
  const [selectedZoneId, setSelectedZoneId] = useState<number | ''>('')
  const availableZones = zones.filter((zone) => zone.governorate === fields.governorate)
  const selectedZone = zones.find((zone) => zone.id === selectedZoneId)
  const subtotal = lines.reduce((sum, line) => sum + (line.product ? moneyAmount(line.product.price) * line.quantity : 0), 0)
  const deliveryFee = selectedZone ? moneyAmount(selectedZone.fee) : 0
  const total = selectedZone ? subtotal + deliveryFee : null

  useEffect(() => {
    let active = true
    loadZones()
    getPublicConfig().then((result) => { if (active) setPublicConfig(result) }).catch(() => undefined)
    return () => { active = false }
  }, [])

  async function loadZones() {
    setZonesLoading(true)
    setZonesUnavailable(false)
    try {
      const result = await getDeliveryZones()
      setZones(result.filter((zone) => zone.active))
    } catch {
      setZonesUnavailable(true)
    } finally {
      setZonesLoading(false)
    }
  }

  function setField<K extends keyof Fields>(key: K, value: Fields[K]) {
    setFields((current) => ({ ...current, [key]: value }))
    setMessage('')
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (submittingRef.current) return
    if (!items.length || hasUnavailable) { setMessage(t.checkout.cartChanged); return }
    if ([fields.customer_name, fields.receiver_name, fields.delivery_area, fields.delivery_address, fields.delivery_slot].some((value) => !value.trim())) {
      setMessage(t.checkout.validation)
      return
    }
    const customerPhone = normalizeEgyptianPhone(fields.customer_phone)
    const receiverPhone = normalizeEgyptianPhone(fields.receiver_phone)
    if (!customerPhone || !receiverPhone) { setMessage(t.checkout.invalidPhone); return }
    if (!fields.governorate || !['Cairo', 'Giza'].includes(fields.governorate) || !fields.delivery_slot || fields.delivery_date < todayLocal()) {
      setMessage(t.checkout.validation)
      return
    }
    if (!paymentMethod) { setMessage(t.checkout.choosePaymentMethod); return }
    if (zonesUnavailable) { setMessage(t.checkout.zonesUnavailable); return }
    if (!availableZones.length) { setMessage(t.checkout.noZones); return }
    if (!selectedZone) { setMessage(t.checkout.chooseDeliveryZone); return }

    submittingRef.current = true
    setSubmitting(true)
    setMessage('')
    try {
      const currentProducts = await getProducts()
      const byId = new Map(currentProducts.map((product) => [product.id, product]))
      if (items.some((item) => {
        const product = byId.get(item.productId)
        return !product || !product.active || product.stock < item.quantity
      })) {
        setMessage(t.checkout.cartChanged)
        return
      }

      const signature = items.slice().sort((a, b) => a.productId - b.productId).map((item) => `${item.productId}:${item.quantity}`).join(',')
      const idempotencyKey = idempotencyRef.current?.signature === signature
        ? idempotencyRef.current.key
        : keyForCart(signature)
      idempotencyRef.current = { key: idempotencyKey, signature }
      const payload: OrderCreatePayload = {
        idempotency_key: idempotencyKey,
        customer_name: fields.customer_name.trim(),
        customer_phone: customerPhone,
        customer_email: fields.customer_email.trim() || null,
        receiver_name: fields.receiver_name.trim(),
        receiver_phone: receiverPhone,
        governorate: fields.governorate,
        delivery_area: fields.delivery_area.trim(),
        delivery_address: fields.delivery_address.trim(),
        delivery_date: fields.delivery_date,
        delivery_slot: fields.delivery_slot,
        payment_method: paymentMethod,
        delivery_zone_id: selectedZone.id,
        delivery_latitude: null,
        delivery_longitude: null,
        google_place_id: null,
        card_message: fields.card_message.trim() || null,
        sender_name_on_card: fields.sender_name_on_card.trim() || null,
        customer_note: fields.customer_note.trim() || null,
        items: items.map((item) => ({ product_id: item.productId, quantity: item.quantity })),
      }
      const order = await createOrder(payload)
      try { sessionStorage.removeItem(CHECKOUT_KEY) } catch { /* Storage may be unavailable. */ }
      idempotencyRef.current = null
      clearCart()
      navigate(`/order-success/${order.id}`, { replace: true, state: { order, publicConfig } })
    } catch (caught) {
      const kind = caught instanceof ApiError ? caught.kind : 'server'
      if (selectedZone && caught instanceof ApiError && (kind === 'not_found' || kind === 'invalid')) {
        setSelectedZoneId('')
        void loadZones()
        setMessage(t.checkout.zoneUnavailableNow)
      } else {
        setMessage(t.errors[kind])
      }
    } finally {
      submittingRef.current = false
      setSubmitting(false)
    }
  }

  if (items.length === 0) {
    return <div className="page container empty-state"><h1>{t.checkout.emptyCart}</h1><Link className="button button-primary" to="/products">{t.common.shopNow}</Link></div>
  }

  return (
    <div className="page checkout-page container">
      <div className="page-heading">
        <p className="eyebrow">{t.checkout.eyebrow}</p>
        <h1>{t.checkout.title}</h1>
        <p>{t.checkout.intro}</p>
      </div>
      {loading ? <div className="section-state">{t.common.loading}</div> : error ? (
        <div className="empty-state"><p>{t.errors.network}</p><button type="button" className="button button-outline" onClick={retry}>{t.common.retry}</button></div>
      ) : (
        <form className="checkout-layout" onSubmit={submit}>
          <div className="checkout-fields">
            <section className="form-section">
              <div className="form-section-title"><span>01</span><h2>{t.checkout.customer}</h2></div>
              <div className="form-grid">
                <label>{t.checkout.customerName}<input autoComplete="name" required maxLength={150} value={fields.customer_name} onChange={(event) => setField('customer_name', event.target.value)} /></label>
                <label>{t.checkout.customerPhone}<input type="tel" inputMode="tel" autoComplete="tel" required maxLength={30} value={fields.customer_phone} onChange={(event) => setField('customer_phone', event.target.value)} /></label>
                <label className="wide-field">{t.checkout.customerEmail} <small>({t.common.optional})</small><input type="email" autoComplete="email" maxLength={150} value={fields.customer_email} onChange={(event) => setField('customer_email', event.target.value)} /></label>
              </div>
            </section>
            <section className="form-section">
              <div className="form-section-title"><span>02</span><h2>{t.checkout.receiver}</h2></div>
              <div className="form-grid">
                <label>{t.checkout.receiverName}<input required maxLength={150} value={fields.receiver_name} onChange={(event) => setField('receiver_name', event.target.value)} /></label>
                <label>{t.checkout.receiverPhone}<input type="tel" inputMode="tel" required maxLength={30} value={fields.receiver_phone} onChange={(event) => setField('receiver_phone', event.target.value)} /></label>
              </div>
            </section>
            <section className="form-section">
              <div className="form-section-title"><span>03</span><h2>{t.checkout.delivery}</h2></div>
              <div className="form-grid">
                <label>{t.checkout.governorate}<select required value={fields.governorate} onChange={(event) => {
                  setField('governorate', event.target.value as Fields['governorate'])
                  setSelectedZoneId('')
                }}>
                  <option value="">{t.checkout.chooseGovernorate}</option>
                  <option value="Cairo">{t.checkout.cairo}</option>
                  <option value="Giza">{t.checkout.giza}</option>
                </select></label>
                <label>{t.checkout.area}<input required maxLength={100} value={fields.delivery_area} onChange={(event) => setField('delivery_area', event.target.value)} /></label>
                <div className="wide-field delivery-zone-field"><label htmlFor="delivery-zone-select">{t.checkout.deliveryZone}</label><select id="delivery-zone-select" required disabled={zonesLoading || zonesUnavailable || availableZones.length === 0} value={selectedZoneId} onChange={(event) => {
                  const zoneId = event.target.value ? Number(event.target.value) : ''
                  setSelectedZoneId(zoneId)
                  const zone = zones.find((item) => item.id === zoneId)
                  if (zone) setField('delivery_area', deliveryZoneName(zone, language))
                }}>
                  <option value="">{zonesLoading ? t.common.loading : t.checkout.chooseDeliveryZone}</option>
                  {availableZones.map((zone) => <option key={zone.id} value={zone.id}>{deliveryZoneName(zone, language)} · {formatMoney(moneyAmount(zone.fee), language)}</option>)}
                </select>
                {zonesUnavailable ? <span className="field-hint zone-load-error"><span>{t.checkout.zonesUnavailable}</span><button type="button" className="button button-outline" onClick={() => void loadZones()} disabled={zonesLoading}>{zonesLoading ? t.common.loading : t.common.retry}</button></span> : availableZones.length === 0 && !zonesLoading ? <small className="field-hint">{t.checkout.noZones}</small> : null}</div>
                <label className="wide-field">{t.checkout.address}<textarea required rows={3} maxLength={500} value={fields.delivery_address} onChange={(event) => setField('delivery_address', event.target.value)} /></label>
                <label>{t.checkout.date}<input type="date" required min={todayLocal()} value={fields.delivery_date} onChange={(event) => setField('delivery_date', event.target.value)} /></label>
                <label>{t.checkout.slot}<select required value={fields.delivery_slot} onChange={(event) => setField('delivery_slot', event.target.value as Fields['delivery_slot'])}>
                  <option value="">{t.checkout.chooseSlot}</option>
                  <option value="morning">{t.checkout.slotOptions.morning}</option>
                  <option value="afternoon">{t.checkout.slotOptions.afternoon}</option>
                  <option value="evening">{t.checkout.slotOptions.evening}</option>
                </select><small className="field-hint">{t.checkout.slotHint}</small></label>
              </div>
            </section>
            <section className="form-section">
              <div className="form-section-title"><span>04</span><h2>{t.checkout.payment}</h2></div>
              <div className="payment-options">
                <label className="payment-option"><input required type="radio" name="payment_method" value="vodafone_cash" checked={paymentMethod === 'vodafone_cash'} onInvalid={(event) => { event.preventDefault(); setMessage(t.checkout.choosePaymentMethod) }} onChange={() => setPaymentMethod('vodafone_cash')} /><span><strong>{t.checkout.vodafoneCash}</strong><small>{t.checkout.vodafoneCashHint}</small></span></label>
                <label className="payment-option"><input type="radio" name="payment_method" value="cash_on_delivery" checked={paymentMethod === 'cash_on_delivery'} onChange={() => setPaymentMethod('cash_on_delivery')} /><span><strong>{t.checkout.cashOnDelivery}</strong><small>{t.checkout.cashOnDeliveryHint}</small></span></label>
              </div>
            </section>
            <section className="form-section">
              <div className="form-section-title"><span>05</span><h2>{t.checkout.gift}</h2></div>
              <div className="form-grid">
                <label className="wide-field">{t.checkout.cardMessage} <small>({t.common.optional})</small><textarea rows={3} maxLength={500} value={fields.card_message} onChange={(event) => setField('card_message', event.target.value)} /></label>
                <label className="wide-field">{t.checkout.senderName} <small>({t.common.optional})</small><input maxLength={150} value={fields.sender_name_on_card} onChange={(event) => setField('sender_name_on_card', event.target.value)} /></label>
              </div>
            </section>
            <section className="form-section">
              <div className="form-section-title"><span>06</span><h2>{t.checkout.notes}</h2></div>
              <label>{t.checkout.customerNote} <small>({t.common.optional})</small><textarea rows={3} maxLength={500} value={fields.customer_note} onChange={(event) => setField('customer_note', event.target.value)} /></label>
            </section>
          </div>
          <aside className="summary-card checkout-summary">
            <h2>{t.cart.summary}</h2>
            <div className="checkout-summary-lines">{lines.map((line) => (
              <div key={line.productId} className="summary-item">
                <div className="summary-item-main">{line.product?.image_url && <ProductImage product={line.product} className="summary-item-image" />}<span>{line.product ? productName(line.product, language) : `#${line.productId}`} x {line.quantity}</span></div>
                <strong>{line.product ? formatMoney(moneyAmount(line.product.price) * line.quantity, language) : '-'}</strong>
              </div>
            ))}</div>
            <div className="summary-row"><span>{t.checkout.subtotal}</span><strong>{formatMoney(subtotal, language)}</strong></div>
            <div className="summary-row"><span>{t.checkout.deliveryFee}</span><strong>{selectedZone ? formatMoney(deliveryFee, language) : '—'}</strong></div>
            <div className="summary-row summary-total"><span>{t.checkout.finalTotal}</span><strong>{total === null ? '—' : formatMoney(total, language)}</strong></div>
            <p className="summary-note">{t.checkout.backendPricing}</p>
            {hasUnavailable && <p className="inline-warning">{t.checkout.cartChanged}</p>}
            {message && <p className="form-error" role="alert">{message}</p>}
            <button className="button button-primary full-width" type="submit" disabled={submitting || hasUnavailable || zonesLoading || zonesUnavailable || !selectedZone}>{submitting ? t.checkout.submitting : t.checkout.submit}</button>
          </aside>
        </form>
      )}
    </div>
  )
}