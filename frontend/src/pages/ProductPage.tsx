import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useProducts } from '../api/hooks'
import { getProduct } from '../api/products'
import { ProductCard, ProductImage, ProductSkeleton } from '../components/ProductCard'
import { useCart } from '../context/CartContext'
import { useLanguage } from '../context/LanguageContext'
import type { Product } from '../types'
import { categoryLabel, formatMoney, productDescription, productName } from '../utils'

export function ProductPage() {
  const { id } = useParams()
  const { language, t } = useLanguage()
  const { addItem } = useCart()
  const [product, setProduct] = useState<Product | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<'not_found' | 'network' | null>(null)
  const [version, setVersion] = useState(0)
  const [quantity, setQuantity] = useState(1)
  const [added, setAdded] = useState(false)
  const relatedState = useProducts()

  useEffect(() => {
    const numericId = Number(id)
    if (!Number.isInteger(numericId) || numericId <= 0) { setLoading(false); setError('not_found'); return }
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    setProduct(null)
    getProduct(numericId, controller.signal)
      .then((value) => { setProduct(value); setQuantity(1) })
      .catch((caught) => { if (!controller.signal.aborted) setError(caught instanceof ApiError && caught.kind === 'not_found' ? 'not_found' : 'network') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [id, version])

  const related = product ? relatedState.products.filter((item) => item.id !== product.id && ((product.category && item.category === product.category) || (product.occasion && item.occasion === product.occasion))).slice(0, 4) : []

  if (loading) return <div className="container page product-detail-loading"><div className="detail-skeleton-photo skeleton-photo" /><div><div className="skeleton-line short" /><div className="skeleton-line" /><div className="skeleton-line" /></div></div>
  if (error === 'network') return <div className="container page empty-state"><h1>{t.errors.network}</h1><button className="button button-primary" type="button" onClick={() => setVersion((value) => value + 1)}>{t.common.retry}</button></div>
  if (error || !product) return <div className="container page empty-state"><h1>{t.product.missing}</h1><Link className="button button-primary" to="/products">{t.common.backToShop}</Link></div>

  const name = productName(product, language)
  const description = productDescription(product, language)
  return (
    <div className="page product-detail-page container"><div className="breadcrumbs"><Link to="/">ToneFlowers</Link><span>/</span><Link to="/products">{t.nav.flowers}</Link><span>/</span><span>{name}</span></div><div className="product-detail-grid"><ProductImage product={product} className="detail-image" /><div className="detail-info"><p className="eyebrow">{product.category ? categoryLabel(product.category, language) : 'TONEFLOWERS'}</p><h1>{name}</h1><p className="detail-price">{formatMoney(product.price, language)}</p><p className={product.stock > 0 ? 'availability stock-ok' : 'availability stock-out'}>{product.stock > 0 ? t.common.available : t.common.soldOut}</p>{description && <p className="detail-description">{description}</p>}<div className="detail-purchase"><label htmlFor="product-quantity">{t.common.quantity}</label><div className="quantity-control"><button type="button" disabled={quantity <= 1} onClick={() => setQuantity((value) => value - 1)} aria-label={t.common.decrease}>−</button><input id="product-quantity" type="number" min="1" step="1" max={product.stock} value={quantity} disabled={product.stock <= 0} onChange={(event) => setQuantity(Math.max(1, Math.min(product.stock, Math.trunc(Number(event.target.value) || 1))))} /><button type="button" disabled={quantity >= product.stock} onClick={() => setQuantity((value) => value + 1)} aria-label={t.common.increase}>+</button></div><small>{t.product.maxStock}: {product.stock}</small><button className="button button-primary detail-add" type="button" disabled={product.stock <= 0} onClick={() => { addItem(product, quantity); setAdded(true) }}>{t.common.addToCart}</button><span role="status" aria-live="polite" className="added-message">{added ? t.product.added : ''}</span></div><div className="delivery-note"><span aria-hidden="true">⌖</span><p>{t.product.deliveryNote}</p></div></div></div>{related.length > 0 && <section className="section related-section"><div className="section-top"><h2>{t.product.related}</h2><Link className="text-link" to="/products">{t.flowers.all}<span aria-hidden="true">↗</span></Link></div><div className="product-grid">{related.map((item) => <ProductCard key={item.id} product={item} />)}</div></section>}{relatedState.loading && <div className="product-grid related-loading">{Array.from({ length: 4 }, (_, index) => <ProductSkeleton key={index} />)}</div>}</div>
  )
}
