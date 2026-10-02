import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useProducts } from '../api/hooks'
import { ProductCard, ProductSkeleton } from '../components/ProductCard'
import { useLanguage } from '../context/LanguageContext'
import type { Product } from '../types'
import { moneyAmount } from '../types'
import { catalogSlug, categoryLabel, occasionLabel, productName } from '../utils'

function matchesOccasion(product: Product, selected: string): boolean {
  return (product.occasion || '').split(',').some((occasion) => catalogSlug(occasion) === catalogSlug(selected))
}

export function ProductsPage() {
  const { t, language } = useLanguage()
  const { products, loading, error, retry } = useProducts()
  const [params, setParams] = useSearchParams()
  const [filterOpen, setFilterOpen] = useState(false)
  const q = params.get('q') || ''
  const category = params.get('category') || ''
  const occasion = catalogSlug(params.get('occasion') || '')
  const sort = params.get('sort') || 'name'
  const availability = params.get('availability') || 'all'
  const best = params.get('best') === '1'
  const featured = params.get('featured') === '1'

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(params)
    if (value && value !== 'all' && !(key === 'sort' && value === 'name')) next.set(key, value)
    else next.delete(key)
    setParams(next)
  }

  const categories = useMemo(() => [...new Set(products.map((product) => product.category).filter((value): value is string => Boolean(value)))].sort(), [products])
  const occasions = useMemo(() => [...new Set(products.flatMap((product) => (product.occasion || '').split(',').map((value) => value.trim()).filter(Boolean)))].sort(), [products])
  const filtered = useMemo(() => {
    const query = q.trim().toLocaleLowerCase()
    const result = products.filter((product) => {
      if (best && !product.best_seller) return false
      if (featured && !product.featured) return false
      if (category && product.category !== category) return false
      if (occasion && !matchesOccasion(product, occasion)) return false
      if (availability === 'in-stock' && product.stock <= 0) return false
      return !query || [product.name, product.name_ar, product.description, product.description_ar].some((value) => value?.toLocaleLowerCase().includes(query))
    })
    result.sort((a, b) => sort === 'price-low' ? moneyAmount(a.price) - moneyAmount(b.price) : sort === 'price-high' ? moneyAmount(b.price) - moneyAmount(a.price) : productName(a, language).localeCompare(productName(b, language), language))
    return result
  }, [products, q, best, featured, category, occasion, availability, sort, language])

  if (!loading && !error && products.length === 0) {
    return <div className="page products-page"><div className="page-banner"><div className="container"><p className="eyebrow">{t.products.eyebrow}</p><h1>{t.products.title}</h1><p>{t.products.copy}</p></div></div><div className="container empty-state"><p>{t.products.empty}</p></div></div>
  }

  return (
    <div className="page products-page"><div className="page-banner"><div className="container"><p className="eyebrow">{t.products.eyebrow}</p><h1>{t.products.title}</h1><p>{t.products.copy}</p></div></div><div className="container products-layout"><aside className={`filters${filterOpen ? " is-open" : ""}`} aria-label={t.products.filter}><button className="filters-toggle" type="button" aria-controls="catalog-filters" aria-expanded={filterOpen} onClick={() => setFilterOpen((open) => !open)}><span>{t.products.filter}</span><span aria-hidden="true">{filterOpen ? "−" : "+"}</span></button><div className="filters-panel" id="catalog-filters"><div className="filters-heading"><h2>{t.products.filter}</h2><button type="button" onClick={() => setParams({})}>{t.products.clearFilters}</button></div><label>{t.products.searchLabel}<input type="search" value={q} onChange={(event) => setFilter('q', event.target.value)} placeholder={t.products.searchPlaceholder} /></label><label>{t.products.category}<select value={category} onChange={(event) => setFilter('category', event.target.value)}><option value="">{t.products.allCategories}</option>{categories.map((value) => <option key={value} value={value}>{categoryLabel(value, language)}</option>)}</select></label><label>{t.products.occasion}<select value={occasion} onChange={(event) => setFilter('occasion', event.target.value)}><option value="">{t.products.allOccasions}</option>{occasions.map((value) => <option key={value} value={catalogSlug(value)}>{occasionLabel(value, language)}</option>)}{occasion && !occasions.some((value) => catalogSlug(value) === occasion) && <option value={occasion}>{occasionLabel(occasion, language)}</option>}</select></label><label>{t.products.availability}<select value={availability} onChange={(event) => setFilter('availability', event.target.value)}><option value="all">{t.products.allAvailability}</option><option value="in-stock">{t.products.inStock}</option></select></label><label className="filter-check"><input type="checkbox" checked={best} onChange={(event) => setFilter('best', event.target.checked ? '1' : '')} />{t.products.bestSellers}</label><label className="filter-check"><input type="checkbox" checked={featured} onChange={(event) => setFilter('featured', event.target.checked ? '1' : '')} />{t.products.featured}</label></div></aside><div className="products-results"><div className="results-top"><p>{loading ? t.common.loading : `${filtered.length} ${t.products.results}`}</p><label>{t.products.sort}<select value={sort} onChange={(event) => setFilter('sort', event.target.value)}><option value="name">{t.products.name}</option><option value="price-low">{t.products.priceLow}</option><option value="price-high">{t.products.priceHigh}</option></select></label></div>{loading ? <div className="product-grid">{Array.from({ length: 6 }, (_, index) => <ProductSkeleton key={index} />)}</div> : error ? <div className="empty-state"><p>{t.errors.network}</p><button className="button button-outline" type="button" onClick={retry}>{t.common.retry}</button></div> : filtered.length ? <div className="product-grid">{filtered.map((product) => <ProductCard key={product.id} product={product} />)}</div> : <div className="empty-state"><p>{t.products.noResults}</p><button className="button button-outline" type="button" onClick={() => setParams({})}>{t.products.clearFilters}</button></div>}</div></div></div>
  )
}
