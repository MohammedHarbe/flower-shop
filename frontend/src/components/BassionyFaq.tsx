import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { getPublicConfig } from '../api/orders'
import { config } from '../config'
import { useLanguage } from '../context/LanguageContext'
import type { PublicConfig } from '../types'
import { whatsappLink } from '../utils'

type Topic = 'delivery' | 'fee' | 'payments' | 'vodafone' | 'proof' | 'ordering' | 'contact'

const faq = {
  en: {
    name: 'Bassiony', title: 'Hi! How can I help?', toggle: 'Open Bassiony FAQ', close: 'Close Bassiony FAQ',
    prompt: 'Choose a topic', questions: {
      delivery: 'Delivery areas', fee: 'Delivery fee', payments: 'Payment methods', vodafone: 'Vodafone Cash',
      proof: 'Payment proof', ordering: 'How to place an order', contact: 'Contact ToneFlowers',
    }, answers: {
      delivery: 'We deliver to Cairo and Giza.',
      fee: 'Delivery is 50 EGP in Cairo and 50 EGP in Giza.',
      payments: 'Choose Vodafone Cash or Cash on Delivery when placing your order.',
      vodafone: 'Place your order first. ToneFlowers confirms flower availability, then sends the Vodafone Cash payment instructions. Do not transfer before that confirmation.',
      proof: 'After ToneFlowers confirms availability and sends payment instructions, transfer the exact amount and send the transfer screenshot through WhatsApp. The shop reviews it and marks payment as paid.',
      ordering: 'Choose products, enter the delivery information, and submit your order. ToneFlowers will confirm flower availability before fulfillment.',
      contact: 'Use the configured ToneFlowers WhatsApp contact below.',
    }, handoff: 'Contact us on WhatsApp', greeting: 'Hello ToneFlowers, I have a question about an order.',
  },
  ar: {
    name: 'بسيوني', title: 'أهلاً! أقدر أساعدك في إيه؟', toggle: 'افتح أسئلة بسيوني', close: 'أغلق أسئلة بسيوني',
    prompt: 'اختار موضوع', questions: {
      delivery: 'التوصيل', fee: 'رسوم التوصيل', payments: 'طرق الدفع', vodafone: 'فودافون كاش',
      proof: 'إثبات الدفع', ordering: 'طريقة عمل الطلب', contact: 'التواصل مع ToneFlowers',
    }, answers: {
      delivery: 'نوصل إلى القاهرة والجيزة فقط.',
      fee: 'رسوم التوصيل ٥٠ جنيهًا للقاهرة و٥٠ جنيهًا للجيزة.',
      payments: 'اختار فودافون كاش أو الدفع عند الاستلام عند إرسال الطلب.',
      vodafone: 'أرسل طلبك أولًا. يؤكد ToneFlowers توفر الزهور، وبعدها يرسل لك تعليمات الدفع بفودافون كاش. لا تحوّل أي مبلغ قبل التأكيد.',
      proof: 'بعد تأكيد توفر الزهور وإرسال تعليمات الدفع، حوّل المبلغ المحدد وأرسل صورة التحويل عبر واتساب. يراجع المتجر التحويل ثم يسجل الدفع كمدفوع.',
      ordering: 'اختار المنتجات، واكتب بيانات التوصيل، ثم أرسل طلبك. يؤكد ToneFlowers توفر الزهور قبل التجهيز.',
      contact: 'تواصل مع ToneFlowers عبر واتساب من الرابط بالأسفل.',
    }, handoff: 'تواصل معنا عبر واتساب', greeting: 'مرحبًا ToneFlowers، لدي استفسار عن طلب.',
  },
} as const

export function BassionyFaq() {
  const { language } = useLanguage()
  const location = useLocation()
  const text = faq[language]
  const [open, setOpen] = useState(false)
  const [topic, setTopic] = useState<Topic | null>(null)
  const [publicConfig, setPublicConfig] = useState<PublicConfig | null>(null)
  const toggleRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    let active = true
    getPublicConfig().then((result) => { if (active) setPublicConfig(result) }).catch(() => undefined)
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!open) return
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false)
        toggleRef.current?.focus()
      }
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [open])

  if (location.pathname.startsWith('/admin') || location.pathname === '/checkout' || location.pathname === '/cart') return null

  const handoff = whatsappLink(publicConfig?.whatsapp_number || '', config.whatsappUrl, text.greeting)
  const panelId = 'bassiony-faq-panel'

  return (
    <aside className={`bassiony-widget${/^\/products\/[^/]+$/.test(location.pathname) ? ' bassiony-widget-product' : ''}`} dir={language === 'ar' ? 'rtl' : 'ltr'}>
      {open && <section id={panelId} className="bassiony-panel" role="dialog" aria-modal="false" aria-label={text.name}>
        <header><span className="bassiony-mark" aria-hidden="true">🌿</span><span><strong>{text.name}</strong><small>{text.title}</small></span><button type="button" onClick={() => setOpen(false)} aria-label={text.close}>×</button></header>
        <p className="bassiony-prompt">{text.prompt}</p>
        <div className="bassiony-questions">{(Object.keys(text.questions) as Topic[]).map((key) => <button key={key} type="button" className={topic === key ? 'selected' : ''} aria-pressed={topic === key} onClick={() => setTopic(key)}>{text.questions[key]}</button>)}</div>
        {topic && <p className="bassiony-answer" aria-live="polite">{text.answers[topic]}</p>}
        {handoff && <a className="bassiony-handoff" href={handoff} target="_blank" rel="noopener noreferrer">{text.handoff}<span aria-hidden="true">↗</span></a>}
      </section>}
      <button ref={toggleRef} className="bassiony-toggle" type="button" aria-label={open ? text.close : text.toggle} aria-controls={panelId} aria-expanded={open} onClick={() => setOpen((current) => !current)}><span aria-hidden="true">{open ? '×' : 'B'}</span>{!open && <strong>{text.name}</strong>}</button>
    </aside>
  )
}