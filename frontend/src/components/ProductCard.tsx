import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useCart } from '../context/CartContext'
import { useLanguage } from '../context/LanguageContext'
import type { Product } from '../types'
import { categoryLabel, formatMoney, productName } from '../utils'

export function ProductImage({ product, className = '' }: { product: Product; className?: string }) {
  const { language, t } = useLanguage()
  const [failed, setFailed] = useState(false)
  const imageUrl = product.image_url && /^https?:\/\//i.test(product.image_url) ? product.image_url : null
  useEffect(() => setFailed(false), [imageUrl])
  const name = productName(product, language)
  return (
    <div className={`product-image ${className}`}>
      {imageUrl && !failed ? (
        <img src={imageUrl} alt={name} loading="lazy" onError={() => setFailed(true)} />
      ) : (
        <span className="product-image-placeholder" role="img" aria-label={`${name}: ${t.common.imageSoon}`}><span aria-hidden="true">✿</span><small>{t.common.imageSoon}</small></span>
      )}
    </div>
  )
}

export function ProductCard({ product }: { product: Product }) {
  const { language, t } = useLanguage()
  const { addItem } = useCart()
  const [added, setAdded] = useState(false)
  const name = productName(product, language)

  function add() {
    addItem(product, 1)
    setAdded(true)
    window.setTimeout(() => setAdded(false), 2200)
  }

  return (
    <article className="product-card">
      <Link to={`/products/${product.id}`} className="product-card-photo"><ProductImage product={product} />{product.best_seller && <span className="card-badge">{t.nav.bestSellers}</span>}</Link>
      <div className="product-card-body">
        <div className="product-card-meta"><span>{product.category ? categoryLabel(product.category, language) : 'ToneFlowers'}</span><span className={product.stock > 0 ? 'stock-ok' : 'stock-out'}>{product.stock > 0 ? t.common.available : t.common.soldOut}</span></div>
        <Link to={`/products/${product.id}`} className="product-card-name">{name}</Link>
        <div className="product-card-bottom"><strong>{formatMoney(product.price, language)}</strong><button className="card-add" type="button" onClick={add} disabled={product.stock <= 0} aria-label={`${t.common.addToCart}: ${name}`}>+</button></div>
        <Link to={`/products/${product.id}`} className="card-view">{t.common.viewProduct}</Link>
        <span className="sr-only" role="status" aria-live="polite">{added ? t.product.added : ''}</span>
      </div>
    </article>
  )
}

export function ProductSkeleton() {
  return <div className="product-card skeleton-card" aria-hidden="true"><div className="skeleton-photo" /><div className="skeleton-line short" /><div className="skeleton-line" /><div className="skeleton-line short" /></div>
}
