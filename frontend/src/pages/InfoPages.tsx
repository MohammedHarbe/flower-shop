import { Link } from 'react-router-dom'
import { config } from '../config'
import { useLanguage } from '../context/LanguageContext'

export function AboutPage() {
  const { t } = useLanguage()
  return <div className="page info-page"><div className="info-hero"><div className="container info-hero-grid"><div><p className="eyebrow">{t.about.eyebrow}</p><h1>{t.about.title}</h1><p className="info-lead">{t.about.lead}</p><p>{t.about.body}</p><Link className="button button-primary" to="/products">{t.about.cta}<span aria-hidden="true">↗</span></Link></div><img src="/images/hero-flowers.jpg" alt={t.hero.imageAlt} /></div></div><section className="container section"><div className="why-grid"><article><span aria-hidden="true">✿</span><h2>{t.why.preparedTitle}</h2><p>{t.why.preparedCopy}</p></article><article><span aria-hidden="true">⌖</span><h2>{t.why.deliveryTitle}</h2><p>{t.why.deliveryCopy}</p></article><article><span aria-hidden="true">✉</span><h2>{t.why.cardTitle}</h2><p>{t.why.cardCopy}</p></article><article><span aria-hidden="true">♡</span><h2>{t.why.serviceTitle}</h2><p>{t.why.serviceCopy}</p></article></div></section></div>
}

export function ContactPage() {
  const { t } = useLanguage()
  const channels = [
    { label: t.contact.whatsapp, value: t.contact.whatsappAction, href: config.whatsappUrl },
    { label: t.contact.phone, value: config.phone, href: config.phone ? `tel:${config.phone}` : '' },
    { label: t.contact.email, value: config.email, href: config.email ? `mailto:${config.email}` : '' },
    { label: t.contact.facebook, value: 'ToneFlowers', href: config.facebookUrl },
    { label: t.contact.instagram, value: t.contact.instagramAction, href: config.instagramUrl },
  ].filter((channel) => channel.href)

  return <div className="page contact-page"><div className="page-banner"><div className="container"><p className="eyebrow">{t.contact.eyebrow}</p><h1>{t.contact.title}</h1><p>{t.contact.copy}</p></div></div><div className="container contact-page-content"><div className="contact-cards">{channels.map((channel) => <a className="contact-card" key={channel.label} href={channel.href} target={channel.href.startsWith('http') ? '_blank' : undefined} rel={channel.href.startsWith('http') ? 'noopener noreferrer' : undefined}><span className="contact-card-main"><span className="contact-card-kind">{channel.label}</span><strong>{channel.value}</strong></span><span className="contact-card-action" aria-hidden="true">↗</span></a>)}</div><div className="contact-side"><span aria-hidden="true">✿</span><h2>{t.contact.serviceArea}</h2>{!config.phone && !config.email && !config.whatsappUrl && <p>{t.contact.noDirect}</p>}</div></div></div>
}

export function NotFoundPage() {
  const { t } = useLanguage()
  return <div className="page container empty-state not-found"><span className="empty-flower" aria-hidden="true">✿</span><h1>{t.notFound.title}</h1><p>{t.notFound.copy}</p><Link className="button button-primary" to="/products">{t.common.shopNow}</Link></div>
}
