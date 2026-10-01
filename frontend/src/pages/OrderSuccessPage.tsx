import { Link, useLocation, useParams } from 'react-router-dom'
import { useLanguage } from '../context/LanguageContext'
import type { DeliverySlot, OrderResponse } from '../types'
import { formatDate, formatMoney } from '../utils'

export function OrderSuccessPage() {
  const { id } = useParams()
  const location = useLocation()
  const { t, language } = useLanguage()
  const state = location.state as { order?: OrderResponse } | null
  const order = state?.order && String(state.order.id) === id ? state.order : null
  const statusLabels = {
    pending: t.success.pending,
    confirmed: t.success.confirmed,
    preparing: t.success.preparing,
    out_for_delivery: t.success.out_for_delivery,
    delivered: t.success.delivered,
    cancelled: t.success.cancelled,
  }

  if (!order) return <div className="page container empty-state not-found"><h1>{t.success.unavailableTitle}</h1><p>{t.success.unavailable}</p><Link className="button button-primary" to="/contact">{t.common.contactUs}</Link></div>

  const statusLabel = Object.prototype.hasOwnProperty.call(statusLabels, order.status)
    ? statusLabels[order.status as keyof typeof statusLabels]
    : t.success.statusUnavailable
  const slotLabel = Object.prototype.hasOwnProperty.call(t.checkout.slotOptions, order.delivery_slot)
    ? t.checkout.slotOptions[order.delivery_slot as DeliverySlot]
    : t.checkout.slotUnconfirmed

  return (
    <div className="page success-page container">
      <div className="success-mark" aria-hidden="true">✓</div>
      <p className="eyebrow">{t.success.eyebrow}</p>
      <h1>{t.success.title}</h1>
      <p className="success-lead">{t.success.copy}</p>
      <div className="success-card">
        <div className="success-row"><span>{t.success.orderNumber}</span><strong>#{id}</strong></div>
        <div className="success-row"><span>{t.success.status}</span><strong>{statusLabel}</strong></div>
        <div className="success-row"><span>{t.success.total}</span><strong>{formatMoney(order.total_price, language)}</strong></div>
        <div className="success-row">
          <span>{t.success.delivery}</span>
          <strong>{order.governorate === 'Cairo' ? t.checkout.cairo : t.checkout.giza} · {order.delivery_area}<br />{formatDate(order.delivery_date, language)} · {slotLabel}</strong>
        </div>
      </div>
      <Link className="button button-primary" to="/products">{t.common.continueShopping}</Link>
    </div>
  )
}
