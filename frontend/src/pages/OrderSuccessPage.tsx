import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { getPublicConfig } from '../api/orders'
import { config } from '../config'
import { useLanguage } from '../context/LanguageContext'
import type { DeliverySlot, OrderConfirmation, PublicConfig } from '../types'
import { formatDate, formatMoney, whatsappLink } from '../utils'

export function OrderSuccessPage() {
  const { id } = useParams()
  const location = useLocation()
  const { t, language } = useLanguage()
  const state = location.state as { order?: OrderConfirmation; publicConfig?: PublicConfig | null } | null
  const order = state?.order && String(state.order.id) === id ? state.order : null
  const [publicConfig, setPublicConfig] = useState<PublicConfig | null>(state?.publicConfig || null)
  const [copied, setCopied] = useState(false)
  const [copyFailed, setCopyFailed] = useState(false)

  useEffect(() => {
    if (publicConfig) return
    let active = true
    getPublicConfig().then((result) => { if (active) setPublicConfig(result) }).catch(() => undefined)
    return () => { active = false }
  }, [publicConfig])

  const statusLabels = {
    pending: t.success.pending,
    confirmed: t.success.confirmed,
    preparing: t.success.preparing,
    out_for_delivery: t.success.out_for_delivery,
    delivered: t.success.delivered,
    cancelled: t.success.cancelled,
  }
  const paymentStatusLabels = {
    awaiting_payment: t.success.awaitingReview,
    unpaid: t.success.unpaid,
    paid: t.success.paid,
  }

  if (!order) return <div className="page container empty-state not-found"><h1>{t.success.unavailableTitle}</h1><p>{t.success.unavailable}</p><Link className="button button-primary" to="/contact">{t.common.contactUs}</Link></div>

  const statusLabel = Object.prototype.hasOwnProperty.call(statusLabels, order.status)
    ? statusLabels[order.status as keyof typeof statusLabels]
    : t.success.statusUnavailable
  const paymentStatusLabel = Object.prototype.hasOwnProperty.call(paymentStatusLabels, order.payment_status)
    ? paymentStatusLabels[order.payment_status as keyof typeof paymentStatusLabels]
    : t.success.paymentStatusUnavailable
  const slotLabel = Object.prototype.hasOwnProperty.call(t.checkout.slotOptions, order.delivery_slot)
    ? t.checkout.slotOptions[order.delivery_slot as DeliverySlot]
    : t.checkout.slotUnconfirmed
  const cashNumber = publicConfig?.vodafone_cash_number || ''
  const whatsappNumber = publicConfig?.whatsapp_number || ''
  const proofMessage = t.success.proofMessage.replace('{order}', String(order.id)).replace('{total}', formatMoney(order.total_price, language))
  const contactMessage = t.success.contactMessage.replace('{order}', String(order.id))
  const whatsappProofHref = whatsappLink(whatsappNumber, config.whatsappUrl, proofMessage)
  const whatsappContactHref = whatsappLink(whatsappNumber, config.whatsappUrl, contactMessage)

  async function copyCashNumber() {
    if (!cashNumber) return
    if (!navigator.clipboard) { setCopyFailed(true); return }
    try {
      await navigator.clipboard.writeText(cashNumber)
      setCopied(true)
      setCopyFailed(false)
    } catch {
      setCopyFailed(true)
      setCopied(false)
    }
  }

  return (
    <div className="page success-page container">
      <div className="success-mark" aria-hidden="true">✓</div>
      <p className="eyebrow">{t.success.eyebrow}</p>
      <h1>{t.success.title}</h1>
      <p className="success-lead">{t.success.copy}</p>
      <div className="success-card">
        <div className="success-row"><span>{t.success.orderNumber}</span><strong>#{id}</strong></div>
        <div className="success-row"><span>{t.success.status}</span><strong>{statusLabel}</strong></div>
        <div className="success-row"><span>{t.checkout.subtotal}</span><strong>{formatMoney(order.subtotal, language)}</strong></div>
        <div className="success-row"><span>{t.checkout.deliveryFee}</span><strong>{formatMoney(order.delivery_fee, language)}</strong></div>
        <div className="success-row"><span>{t.success.total}</span><strong>{formatMoney(order.total_price, language)}</strong></div>
        <div className="success-row">
          <span>{t.success.delivery}</span>
          <strong>{order.governorate === 'Cairo' ? t.checkout.cairo : t.checkout.giza} · {order.delivery_area}<br />{formatDate(order.delivery_date, language)} · {slotLabel}</strong>
        </div>
      </div>
      {order.payment_method === 'vodafone_cash' ? (
        <section className="payment-instructions" aria-live="polite">
          <h2>{t.success.vodafoneTitle}</h2>
          <p>{t.success.vodafoneCopy}</p>
          <p className="payment-status-line">{t.success.paymentStatus}: <strong>{paymentStatusLabel}</strong></p>
          <div className="cash-payment-number"><strong>{cashNumber || t.success.numberUnavailable}</strong>
            {cashNumber && <button type="button" className="button button-outline" onClick={copyCashNumber}>{copied ? t.success.copied : t.success.copyNumber}</button>}
          </div>
          {copyFailed && <p className="inline-warning">{t.success.copyFailed}</p>}
          <p className="cash-payment-total">{t.success.payExact} <strong>{formatMoney(order.total_price, language)}</strong></p>
          <p>{t.success.orderNumber}: <strong>#{order.id}</strong></p>
          {order.payment_status === 'awaiting_payment' && <p>{t.success.awaitingReviewCopy}</p>}
          {order.payment_status === 'paid' && <p>{t.success.paymentAlreadyRecorded}</p>}
          {order.payment_status !== 'paid' && <ol className="payment-steps">{t.success.transferSteps.map((step) => <li key={step}>{step}</li>)}</ol>}
          {order.payment_status !== 'paid' && whatsappProofHref && <a className="button button-primary" href={whatsappProofHref} target="_blank" rel="noreferrer">{t.success.sendProof}</a>}
        </section>
      ) : <section className="payment-instructions" role="status">
        <h2>{t.success.cashOnDeliveryTitle}</h2>
        <p>{t.checkout.payment}: <strong>{t.checkout.cashOnDelivery}</strong></p>
        <p>{order.payment_status === 'paid' ? t.success.amountPaid : t.success.amountDue}: <strong>{formatMoney(order.total_price, language)}</strong></p>
        <p>{t.success.paymentStatus}: <strong>{paymentStatusLabel}</strong></p>
        <p>{t.success.cashOnDelivery}</p>
      </section>}
      {whatsappContactHref && <p className="success-contact">{t.success.needHelp} <a href={whatsappContactHref} target="_blank" rel="noreferrer">{t.success.whatsappContact}</a></p>}
      <Link className="button button-primary" to="/products">{t.common.continueShopping}</Link>
    </div>
  )
}
