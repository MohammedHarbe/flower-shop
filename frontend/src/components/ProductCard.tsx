import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useCart } from '../context/CartContext'
import { useLanguage } from '../context/LanguageContext'
import type { Product } from '../types'
import { categoryLabel, formatMoney, productName } from '../utils'

export function ProductImage({ product, className = '' }: { product: Product; className?: string }) {
  const { language, t } = useLanguage()
  const [failedUrl, setFailedUrl] = useState<string | null>(null)
  const [loadedUrl, setLoadedUrl] = useState<string | null>(null)
  const imageUrl = (() => {
    const value = product.image_url?.trim()
    if (!value) return null
    if (value.startsWith('/products/') && !value.includes('..') && /^\/products\/[a-z0-9_./-]+$/i.test(value)) return value
    try {
      const url = new URL(value)
      return ['http:', 'https:'].includes(url.protocol) && !/(^|\.)fbcdn\.net$/i.test(url.hostname) ? url.href : null
    } catch { return null }
  })()
  const name = productName(product, language)
  return (
    <div className={`product-image ${className}`}>
      {imageUrl && failedUrl !== imageUrl ? (
        <img className={loadedUrl === imageUrl ? 'is-loaded' : ''} src={imageUrl} alt={name} loading="lazy" onLoad={() => setLoadedUrl(imageUrl)} onError={() => setFailedUrl(imageUrl)} />
      ) : (
        <span className="product-image-placeholder" role="img" aria-label={`${name}: ${t.common.imageSoon}`}><span aria-hidden="true">✿</span><small>{t.common.imageSoon}</small></span>
      )}
    </div>
  )
}

export function ProductCard({ product }: { product: Product }) {
  const { language, t } = useLanguage()
  const { addItem, items } = useCart()
  const [added, setAdded] = useState(false)
  const feedbackTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const name = productName(product, language)
  const atCartLimit = product.stock > 0 && (items.find((item) => item.productId === product.id)?.quantity || 0) >= product.stock

  useEffect(() => () => { if (feedbackTimer.current) clearTimeout(feedbackTimer.current) }, [])

  function add() {
    if (!product.active || product.stock <= 0 || (items.find((item) => item.productId === product.id)?.quantity || 0) >= product.stock) return
    addItem(product, 1)
    setAdded(true)
    if (feedbackTimer.current) clearTimeout(feedbackTimer.current)
    feedbackTimer.current = setTimeout(() => setAdded(false), 1800)
  }

  return (
    <article className="product-card">
      <Link to={`/products/${product.id}`} className="product-card-photo"><ProductImage product={product} />{product.best_seller && <span className="card-badge">{t.nav.bestSellers}</span>}</Link>
      <div className="product-card-body">
        <div className="product-card-meta"><span>{product.category ? categoryLabel(product.category, language) : 'ToneFlowers'}</span><span className={product.stock > 0 ? 'stock-ok' : 'stock-out'}>{product.stock > 0 ? t.common.available : t.common.soldOut}</span></div>
        <Link to={`/products/${product.id}`} className="product-card-name">{name}</Link>
        <div className="product-card-bottom"><strong>{formatMoney(product.price, language)}</strong><button className={`card-add${added ? ' is-added' : ''}`} type="button" onClick={add} disabled={product.stock <= 0 || !product.active || atCartLimit} aria-label={`${product.stock <= 0 ? t.common.soldOut : atCartLimit ? t.product.maxInCart : added ? t.product.added : t.common.addToCart}: ${name}`}>{added ? <>{t.product.addedShort} <span aria-hidden="true">✓</span></> : product.stock <= 0 ? t.common.soldOut : atCartLimit ? t.product.inCart : t.common.addToCart}</button></div>
        <Link to={`/products/${product.id}`} className="card-view">{t.common.viewProduct}</Link>
        <span className="sr-only" role="status" aria-live="polite">{added ? t.product.added : ''}</span>
      </div>
    </article>
  )
}

export function ProductSkeleton() {
  return <div className="product-card skeleton-card" aria-hidden="true"><div className="skeleton-photo" /><div className="skeleton-line short" /><div className="skeleton-line" /><div className="skeleton-line short" /></div>
}
