import { useEffect, useState } from 'react'
import type { FormEvent, PropsWithChildren } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { getPublicConfig } from '../api/orders'
import { config } from '../config'
import { useCart } from '../context/CartContext'
import { useLanguage } from '../context/LanguageContext'
import type { PublicConfig } from '../types'
import { whatsappLink } from '../utils'
import { BassionyFaq } from './BassionyFaq'

function SearchIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.8" /><path d="m16 16 5 5" /></svg>
}

function CartIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M3 4h2l2 11h11l2-8H6" /><circle cx="9" cy="20" r="1" /><circle cx="18" cy="20" r="1" /></svg>
}

function MenuIcon({ open }: { open: boolean }) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">{open ? <path d="M5 5 19 19M19 5 5 19" /> : <path d="M3 6h18M3 12h18M3 18h18" />}</svg>
}

function BrandLogo() {
  return (
    <Link to="/" className="brand-logo" aria-label="ToneFlowers home">
      <span className="brand-logo-crop"><img src="/images/toneflowers-logo.jpg" alt="ToneFlowers" /></span>
    </Link>
  )
}

function Header() {
  const { t, toggleLanguage } = useLanguage()
  const { count } = useCart()
  const location = useLocation()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [search, setSearch] = useState('')

  useEffect(() => {
    setMenuOpen(false)
    setSearchOpen(false)
  }, [location.pathname, location.hash])

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    navigate(`/products?q=${encodeURIComponent(search.trim())}`)
    setSearchOpen(false)
    setMenuOpen(false)
  }

  const links = [
    { to: '/products', label: t.nav.flowers },
    { to: '/#occasions', label: t.nav.occasions },
    { to: '/#gifts', label: t.nav.gifts },
    { to: '/products?best=1', label: t.nav.bestSellers },
    { to: '/about', label: t.nav.about },
    { to: '/contact', label: t.nav.contact },
  ]

  return (
    <>
      <div className="announcement-bar"><span className="announcement-flower" aria-hidden="true">✿</span>{t.announcement}<span className="announcement-flower" aria-hidden="true">✿</span></div>
      <header className="site-header">
        <div className="header-inner container">
          <BrandLogo />
          <nav className="desktop-nav" aria-label={t.nav.menu}>
            {links.map((link) => <NavLink key={link.to} to={link.to} className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>{link.label}</NavLink>)}
          </nav>
          <div className="header-actions">
            <button className="icon-button search-toggle" type="button" onClick={() => setSearchOpen((open) => !open)} aria-label={t.nav.search} aria-expanded={searchOpen}><SearchIcon /></button>
            <button className="language-button" type="button" onClick={toggleLanguage} aria-label={t.nav.language}>{t.nav.language}</button>
            <Link className="cart-button" to="/cart" aria-label={`${t.nav.cart}: ${count}`}><CartIcon />{count > 0 && <span className="cart-count">{count}</span>}</Link>
            <button className="icon-button menu-toggle" type="button" onClick={() => setMenuOpen((open) => !open)} aria-label={menuOpen ? t.nav.closeMenu : t.nav.menu} aria-expanded={menuOpen}><MenuIcon open={menuOpen} /></button>
          </div>
        </div>
        {searchOpen && <form className="header-search container" onSubmit={submitSearch} role="search"><label htmlFor="header-search-input" className="sr-only">{t.nav.search}</label><input id="header-search-input" autoFocus value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t.products.searchPlaceholder} /><button className="button button-primary" type="submit">{t.nav.search}</button></form>}
        {menuOpen && <nav className="mobile-nav" aria-label={t.nav.menu}>{links.map((link) => <Link key={link.to} to={link.to} onClick={() => setMenuOpen(false)}>{link.label}</Link>)}<button type="button" onClick={() => { setSearchOpen(true); setMenuOpen(false) }}>{t.nav.search}</button></nav>}
      </header>
    </>
  )
}

function Footer() {
  const { t } = useLanguage()
  const [publicConfig, setPublicConfig] = useState<PublicConfig | null>(null)
  useEffect(() => {
    getPublicConfig().then(setPublicConfig).catch(() => undefined)
  }, [])
  const whatsappHref = whatsappLink(publicConfig?.whatsapp_number || '', config.whatsappUrl, t.contact.whatsappMessage)
  return (
    <footer className="site-footer">
      <div className="container footer-grid">
        <div className="footer-brand"><BrandLogo /><p>{t.footer.description}</p><span className="footer-delivery">{t.footer.delivery}</span></div>
        <div><h2>{t.footer.explore}</h2><Link to="/products">{t.nav.flowers}</Link><Link to="/#occasions">{t.nav.occasions}</Link><Link to="/about">{t.nav.about}</Link><Link to="/contact">{t.nav.contact}</Link></div>
        <div><h2>{t.footer.support}</h2>{config.phone && <a href={`tel:${config.phone}`}>{config.phone}</a>}{config.email && <a href={`mailto:${config.email}`}>{config.email}</a>}{whatsappHref && <a href={whatsappHref} target="_blank" rel="noopener noreferrer">{t.contact.whatsapp}</a>}{config.facebookUrl && <a href={config.facebookUrl} target="_blank" rel="noopener noreferrer">{t.contact.facebook}</a>}{config.instagramUrl && <a href={config.instagramUrl} target="_blank" rel="noopener noreferrer">{t.contact.instagram}</a>}</div>
      </div>
      <div className="footer-bottom container"><span>© {new Date().getFullYear()} ToneFlowers. {t.footer.rights}</span><span>{t.checkout.cairo} · {t.checkout.giza}</span></div>
    </footer>
  )
}

export function Layout({ children }: PropsWithChildren) {
  const location = useLocation()
  const { t, language } = useLanguage()
  useEffect(() => {
    const adminPage = location.pathname.startsWith('/admin')
    const pages = language === 'ar'
      ? {
        home: ['تون فلاورز | ورد يحكي حكايتك', 'اكتشف الزهور والهدايا والتوصيل داخل القاهرة والجيزة من تون فلاورز.'],
        products: ['الزهور | تون فلاورز', 'تصفح الزهور والباقات المتاحة للتوصيل داخل القاهرة والجيزة.'],
        product: ['تفاصيل الزهرة | تون فلاورز', 'اكتشف تفاصيل الزهور والباقات المتاحة من تون فلاورز.'],
        cart: ['سلة التسوق | تون فلاورز', 'راجع اختياراتك من الزهور قبل إتمام الطلب.'],
        checkout: ['إتمام الطلب | تون فلاورز', 'أكمل بيانات التوصيل والدفع لطلب الزهور داخل القاهرة والجيزة.'],
        about: ['قصتنا | تون فلاورز', 'تعرف على تون فلاورز وخدمة توصيل الزهور داخل القاهرة والجيزة.'],
        contact: ['تواصل معنا | تون فلاورز', 'تواصل مع تون فلاورز بخصوص الزهور والطلبات والتوصيل.'],
        success: ['تأكيد الطلب | تون فلاورز', 'تم استلام طلب الزهور. راجع ملخص الطلب وتعليمات الدفع.'],
      }
      : {
        home: ['ToneFlowers | Flowers that tell your story', 'Shop flowers and thoughtful gifts delivered across Cairo and Giza with ToneFlowers.'],
        products: ['Flowers | ToneFlowers', 'Browse flowers and bouquets available for delivery across Cairo and Giza.'],
        product: ['Flower details | ToneFlowers', 'Explore details for flowers and bouquets available from ToneFlowers.'],
        cart: ['Your cart | ToneFlowers', 'Review your flower selection before placing your order.'],
        checkout: ['Checkout | ToneFlowers', 'Enter delivery and payment details for flower delivery across Cairo and Giza.'],
        about: ['About | ToneFlowers', 'Learn about ToneFlowers and flower delivery across Cairo and Giza.'],
        contact: ['Contact | ToneFlowers', 'Contact ToneFlowers about flowers, orders, and delivery.'],
        success: ['Order confirmation | ToneFlowers', 'Your flower order was received. Review the order summary and payment instructions.'],
      }
    const path = location.pathname
    const page = adminPage ? ['ToneFlowers Admin', '']
      : path === '/' ? pages.home
        : path.startsWith('/products/') ? pages.product
          : path === '/products' ? pages.products
            : path === '/cart' ? pages.cart
              : path === '/checkout' ? pages.checkout
                : path.startsWith('/order-success/') ? pages.success
                  : path === '/about' ? pages.about
                    : path === '/contact' ? pages.contact
                      : [language === 'ar' ? 'الصفحة غير موجودة | تون فلاورز' : 'Page not found | ToneFlowers', '']
    document.title = page[0]
    let description = document.querySelector<HTMLMetaElement>('meta[name="description"]')
    if (!description) {
      description = document.createElement('meta')
      description.name = 'description'
      document.head.append(description)
    }
    description.content = page[1]
    let robots = document.querySelector<HTMLMetaElement>('meta[name="robots"]')
    if (!robots) {
      robots = document.createElement('meta')
      robots.name = 'robots'
      document.head.append(robots)
    }
    robots.content = adminPage ? 'noindex, nofollow, noarchive' : 'index, follow'
    let canonical = document.querySelector<HTMLLinkElement>('link[rel="canonical"]')
    if (config.siteUrl && !adminPage) {
      if (!canonical) {
        canonical = document.createElement('link')
        canonical.rel = 'canonical'
        document.head.append(canonical)
      }
      canonical.href = new URL(location.pathname, `${config.siteUrl}/`).href
    } else {
      canonical?.remove()
    }
  }, [language, location.pathname])
  useEffect(() => {
    if (location.hash) {
      window.setTimeout(() => document.getElementById(location.hash.slice(1))?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' }), 50)
    } else {
      window.scrollTo(0, 0)
    }
  }, [location.pathname, location.hash])

  if (location.pathname.startsWith('/admin')) return <>{children}</>
  return <><a className="skip-link" href="#main">{t.common.skip}</a><Header /><main id="main">{children}</main><BassionyFaq /><Footer /></>
}
