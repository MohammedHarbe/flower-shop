import { Link } from 'react-router-dom'
import { useCartProducts } from '../api/hooks'
import { ProductImage } from '../components/ProductCard'
import { useCart } from '../context/CartContext'
import { useLanguage } from '../context/LanguageContext'
import { moneyAmount } from '../types'
import { formatMoney, productName } from '../utils'

export function CartPage() {
  const { t, language } = useLanguage()
  const { items, updateQuantity, removeItem } = useCart()
  const { lines, loading, error, retry, hasUnavailable } = useCartProducts()
  const subtotal = lines.reduce((sum, line) => sum + (line.product ? moneyAmount(line.product.price) * line.quantity : 0), 0)

  if (items.length === 0) return <div className="page container empty-state cart-empty"><span className="empty-flower" aria-hidden="true">✿</span><p className="eyebrow">{t.cart.eyebrow}</p><h1>{t.cart.emptyTitle}</h1><p>{t.cart.emptyCopy}</p><Link className="button button-primary" to="/products">{t.common.shopNow}</Link></div>

  return <div className="page cart-page container"><div className="page-heading"><p className="eyebrow">{t.cart.eyebrow}</p><h1>{t.cart.title}</h1></div>{loading ? <div className="section-state"><p>{t.common.loading}</p></div> : error ? <div className="empty-state"><p>{t.errors.network}</p><button className="button button-outline" onClick={retry} type="button">{t.common.retry}</button></div> : <div className="cart-layout"><div className="cart-lines">{lines.map((line) => line.product ? <article className="cart-line" key={line.productId}><Link to={`/products/${line.productId}`} className="cart-line-image"><ProductImage product={line.product} /></Link><div className="cart-line-info"><Link to={`/products/${line.productId}`} className="cart-line-name">{productName(line.product, language)}</Link><p>{formatMoney(line.product.price, language)}</p>{line.product.stock < line.quantity && <p className="inline-warning">{t.cart.stockChanged} ({line.product.stock})</p>}<div className="cart-line-actions"><label>{t.common.quantity}<input type="number" min="1" step="1" max={Math.max(1, line.product.stock)} value={line.quantity} onChange={(event) => updateQuantity(line.productId, Math.max(1, Math.min(line.product!.stock, Math.trunc(Number(event.target.value) || 1))))} disabled={line.product.stock <= 0} /></label><button type="button" onClick={() => removeItem(line.productId)}>{t.common.remove}</button></div></div><strong>{formatMoney(moneyAmount(line.product.price) * line.quantity, language)}</strong></article> : <article className="cart-line unavailable-line" key={line.productId}><div className="cart-line-image unavailable-image" aria-hidden="true">✿</div><div className="cart-line-info"><h2>#{line.productId}</h2><p className="inline-warning">{t.cart.unavailable}</p><button type="button" onClick={() => removeItem(line.productId)}>{t.common.remove}</button></div></article>)}</div><aside className="summary-card"><h2>{t.cart.summary}</h2><div className="summary-row"><span>{t.cart.subtotal}</span><strong>{formatMoney(subtotal, language)}</strong></div><p className="summary-note">{t.cart.note}</p>{hasUnavailable ? <p className="inline-warning">{t.cart.unavailable}</p> : <Link className="button button-primary full-width" to="/checkout">{t.cart.checkout}<span aria-hidden="true">↗</span></Link>}<Link className="text-link continue-link" to="/products">{t.common.continueShopping}</Link></aside></div>}</div>
}
