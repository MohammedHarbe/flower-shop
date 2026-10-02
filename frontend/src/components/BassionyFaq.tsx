import { useEffect, useState } from 'react'
import { getPublicConfig } from '../api/orders'
import { config } from '../config'
import { useLanguage } from '../context/LanguageContext'
import type { PublicConfig } from '../types'
import { whatsappLink } from '../utils'

type Topic = 'areas' | 'fee' | 'payment' | 'proof'

const faq = {
  en: {
    name: 'Bassiony', title: 'How can I help?', toggle: 'Open Bassiony help', close: 'Close help',
    prompt: 'Choose a quick answer', questions: {
      areas: 'Where do you deliver?', fee: 'How much is delivery?', payment: 'Which payment methods do you accept?', proof: 'How do I send payment proof?',
    }, answers: {
      areas: 'We currently deliver to Cairo and Giza. Enter the delivery area and full address at checkout.',
      fee: 'Delivery is 50 EGP in Cairo and 50 EGP in Giza. The backend confirms the active fee at checkout.',
      payment: 'Choose Vodafone Cash or Cash on Delivery at checkout. Vodafone Cash is reviewed manually before payment is marked paid.',
      proof: 'Transfer the exact order total to the Vodafone Cash number shown after placing the order, then send the transfer screenshot through WhatsApp.',
    }, handoff: 'Ask us on WhatsApp', greeting: 'Hello ToneFlowers, I have a question about delivery or payment.',
  },
  ar: {
    name: 'بسيوني', title: 'كيف أقدر أساعدك؟', toggle: 'افتح مساعدة بسيوني', close: 'أغلق المساعدة',
    prompt: 'اختر إجابة سريعة', questions: {
      areas: 'ما مناطق التوصيل؟', fee: 'كم رسوم التوصيل؟', payment: 'ما طرق الدفع المتاحة؟', proof: 'كيف أرسل إثبات الدفع؟',
    }, answers: {
      areas: 'التوصيل متاح حاليًا داخل القاهرة والجيزة. اكتب المنطقة والعنوان بالكامل عند إتمام الطلب.',
      fee: 'رسوم التوصيل ٥٠ جنيهًا للقاهرة و٥٠ جنيهًا للجيزة. يؤكد الخادم الرسوم النشطة عند إتمام الطلب.',
      payment: 'يمكنك اختيار فودافون كاش أو الدفع عند الاستلام. تتم مراجعة تحويل فودافون كاش يدويًا قبل تسجيل الدفع.',
      proof: 'حوّل إجمالي الطلب بالضبط إلى رقم فودافون كاش الظاهر بعد الطلب، ثم أرسل صورة التحويل عبر واتساب.',
    }, handoff: 'اسألنا عبر واتساب', greeting: 'مرحبًا تون فلاورز، لدي سؤال عن التوصيل أو الدفع.',
  },
} as const

export function BassionyFaq() {
  const { language } = useLanguage()
  const text = faq[language]
  const [open, setOpen] = useState(false)
  const [topic, setTopic] = useState<Topic | null>(null)
  const [publicConfig, setPublicConfig] = useState<PublicConfig | null>(null)

  useEffect(() => {
    let active = true
    getPublicConfig().then((result) => { if (active) setPublicConfig(result) }).catch(() => undefined)
    return () => { active = false }
  }, [])

  const handoff = whatsappLink(publicConfig?.whatsapp_number || '', config.whatsappUrl, text.greeting)

  return (
    <aside className="bassiony-widget" dir={language === 'ar' ? 'rtl' : 'ltr'}>
      {open && <section className="bassiony-panel" aria-label={text.name}>
        <header><span className="bassiony-mark" aria-hidden="true">B</span><span><strong>{text.name}</strong><small>{text.title}</small></span><button type="button" onClick={() => setOpen(false)} aria-label={text.close}>×</button></header>
        <p className="bassiony-prompt">{text.prompt}</p>
        <div className="bassiony-questions">{(Object.keys(text.questions) as Topic[]).map((key) => <button key={key} type="button" className={topic === key ? 'selected' : ''} onClick={() => setTopic(key)}>{text.questions[key]}</button>)}</div>
        {topic && <p className="bassiony-answer" aria-live="polite">{text.answers[topic]}</p>}
        {handoff && <a className="bassiony-handoff" href={handoff} target="_blank" rel="noopener noreferrer">{text.handoff}<span aria-hidden="true">↗</span></a>}
      </section>}
      <button className="bassiony-toggle" type="button" aria-label={open ? text.close : text.toggle} aria-expanded={open} onClick={() => setOpen((current) => !current)}><span aria-hidden="true">{open ? '×' : 'B'}</span>{!open && <strong>{text.name}</strong>}</button>
    </aside>
  )
}