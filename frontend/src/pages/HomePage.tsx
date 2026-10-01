import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useProducts } from '../api/hooks'
import { ProductCard, ProductSkeleton } from '../components/ProductCard'
import { config } from '../config'
import { useLanguage } from '../context/LanguageContext'

const occasionKeys = [
  'birthday', 'anniversary', 'romance', 'congratulations', 'getWell', 'thankYou', 'justBecause',
] as const
const occasionSlugs = ['birthday', 'anniversary', 'love-and-romance', 'congratulations', 'get-well', 'thank-you', 'just-because']

export function HomePage() {
  const { t } = useLanguage()
  const { products, loading, error, retry } = useProducts()
  const bestSellers = products.filter((product) => product.best_seller).slice(0, 4)
  const collection = products.filter((product) => product.featured).concat(products.filter((product) => !product.featured)).slice(0, 4)

  useEffect(() => {
    if (typeof window.IntersectionObserver !== 'function' || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible')
          observer.unobserve(entry.target)
        }
      }
    }, { threshold: 0.12 })
    document.querySelectorAll('.home-reveal').forEach((element) => observer.observe(element))
    return () => observer.disconnect()
  }, [])

  return (
    <>
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-copy"><div className="hero-copy-inner"><p className="eyebrow light">{t.hero.eyebrow}</p><h1 id="hero-title">{t.hero.title}</h1><p>{t.hero.copy}</p><div className="hero-actions"><Link className="button button-cream" to="/products">{t.hero.primary}<span aria-hidden="true">↗</span></Link><Link className="text-link light-link" to="/#occasions">{t.hero.secondary}<span aria-hidden="true">↗</span></Link></div><div className="hero-note"><span aria-hidden="true">✿</span>{t.hero.note}</div></div></div>
        <div className="hero-image"><img src="/images/hero-flowers.jpg" alt={t.hero.imageAlt} fetchPriority="high" /><span className="hero-image-caption">{t.hero.eyebrow}</span></div>
      </section>

      <section className="section occasions-section container reveal home-reveal" id="occasions" aria-labelledby="occasions-title"><div className="section-top"><div><p className="eyebrow">{t.occasions.eyebrow}</p><h2 id="occasions-title">{t.occasions.title}</h2></div><p className="section-intro">{t.occasions.copy}</p></div><div className="occasion-grid">{occasionKeys.map((key, index) => <Link className={`occasion-card occasion-${index + 1}`} to={`/products?occasion=${occasionSlugs[index]}`} key={key}><span className="occasion-number">0{index + 1}</span><span className="occasion-bloom" aria-hidden="true">✿</span><strong>{t.occasions[key]}</strong><span className="occasion-arrow" aria-hidden="true">↗</span></Link>)}</div></section>

      <section className="section product-section section-cream" id="best-sellers" aria-labelledby="best-title"><div className="container"><div className="section-top"><div><p className="eyebrow">{t.best.eyebrow}</p><h2 id="best-title">{t.best.title}</h2></div><p className="section-intro">{t.best.copy}</p></div>{loading ? <div className="product-grid">{Array.from({ length: 4 }, (_, index) => <ProductSkeleton key={index} />)}</div> : error ? <div className="section-state"><p>{t.errors.network}</p><button className="button button-outline" type="button" onClick={retry}>{t.common.retry}</button></div> : bestSellers.length ? <div className="product-grid">{bestSellers.map((product) => <ProductCard key={product.id} product={product} />)}</div> : <p className="section-state">{t.best.empty}</p>}</div></section>

      <section className="section product-section container" aria-labelledby="flowers-title"><div className="section-top"><div><p className="eyebrow">{t.flowers.eyebrow}</p><h2 id="flowers-title">{t.flowers.title}</h2></div><Link className="text-link" to="/products">{t.flowers.all}<span aria-hidden="true">↗</span></Link></div><p className="section-description">{t.flowers.copy}</p>{loading ? <div className="product-grid">{Array.from({ length: 4 }, (_, index) => <ProductSkeleton key={index} />)}</div> : error ? <div className="section-state"><p>{t.errors.network}</p><button className="button button-outline" type="button" onClick={retry}>{t.common.retry}</button></div> : collection.length ? <div className="product-grid">{collection.map((product) => <ProductCard key={product.id} product={product} />)}</div> : <div className="section-state"><p>{t.products.noResults}</p><Link className="button button-outline" to="/contact">{t.common.contactUs}</Link></div>}</section>

      <section className="gift-section reveal home-reveal" id="gifts" aria-labelledby="gifts-title"><div className="container gift-inner"><div className="gift-decoration" aria-hidden="true"><div className="gift-card-art"><span>✿</span><i /></div></div><div className="gift-copy"><p className="eyebrow">{t.gifts.eyebrow}</p><h2 id="gifts-title">{t.gifts.title}</h2><p>{t.gifts.copy}</p><Link className="button button-primary" to="/products">{t.gifts.cta}<span aria-hidden="true">↗</span></Link></div></div></section>

      <section className="section why-section container reveal home-reveal" aria-labelledby="why-title"><div className="section-top"><div><p className="eyebrow">{t.why.eyebrow}</p><h2 id="why-title">{t.why.title}</h2></div></div><div className="why-grid"><article><span aria-hidden="true">✿</span><h3>{t.why.preparedTitle}</h3><p>{t.why.preparedCopy}</p></article><article><span aria-hidden="true">⌖</span><h3>{t.why.deliveryTitle}</h3><p>{t.why.deliveryCopy}</p></article><article><span aria-hidden="true">✉</span><h3>{t.why.cardTitle}</h3><p>{t.why.cardCopy}</p></article><article><span aria-hidden="true">♡</span><h3>{t.why.serviceTitle}</h3><p>{t.why.serviceCopy}</p></article></div></section>

      <section className="section steps-section section-cream reveal home-reveal" aria-labelledby="steps-title"><div className="container"><div className="section-top"><div><p className="eyebrow">{t.steps.eyebrow}</p><h2 id="steps-title">{t.steps.title}</h2></div></div><div className="steps-grid"><article><span>01</span><h3>{t.steps.choose}</h3><p>{t.steps.chooseCopy}</p></article><article><span>02</span><h3>{t.steps.customize}</h3><p>{t.steps.customizeCopy}</p></article><article><span>03</span><h3>{t.steps.deliver}</h3><p>{t.steps.deliverCopy}</p></article></div></div></section>

      <section className="contact-band"><div className="container contact-band-inner"><div><p className="eyebrow light">{t.contactCta.eyebrow}</p><h2>{t.contactCta.title}</h2><p>{t.contactCta.copy}</p></div><a className="button button-cream" href={config.whatsappUrl || '/contact'} target={config.whatsappUrl ? '_blank' : undefined} rel={config.whatsappUrl ? 'noopener noreferrer' : undefined}>{config.whatsappUrl ? t.contactCta.whatsapp : t.contactCta.contact}<span aria-hidden="true">↗</span></a></div></section>
    </>
  )
}
