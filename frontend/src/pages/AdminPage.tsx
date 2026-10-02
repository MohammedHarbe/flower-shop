import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useLocation } from 'react-router-dom'
import {
  adminDeliveryZones,
  adminLogin,
  adminLogout,
  adminMe,
  adminOrders,
  adminProducts,
  saveProduct,
  updateDeliveryZone,
  updateOrderStatus,
  updatePaymentStatus,
} from '../api/admin'
import { ApiError } from '../api/client'
import { useLanguage } from '../context/LanguageContext'
import type { DeliveryZone, OrderResponse, Product } from '../types'
import { formatDate, formatMoney } from '../utils'

type Tab = 'products' | 'orders' | 'delivery'
type ProductDraft = {
  id?: number
  name: string
  name_ar: string
  description: string
  description_ar: string
  price: string
  stock: string
  category: string
  occasion: string
  image_url: string
  active: boolean
  featured: boolean
  best_seller: boolean
}

const emptyProduct: ProductDraft = {
  name: '', name_ar: '', description: '', description_ar: '', price: '', stock: '0',
  category: '', occasion: '', image_url: '', active: true, featured: false, best_seller: false,
}

const copy = {
  en: {
    title: 'ToneFlowers operations', login: 'Admin sign in', email: 'Email', password: 'Password', signIn: 'Sign in',
    products: 'Products', orders: 'Orders', delivery: 'Delivery fees', signOut: 'Sign out', add: 'Add product',
    edit: 'Edit', save: 'Save changes', cancel: 'Cancel', name: 'Name (English)', nameAr: 'Name (Arabic)',
    description: 'Description (English)', descriptionAr: 'Description (Arabic)', price: 'Price (EGP)', stock: 'Stock',
    category: 'Category', occasion: 'Occasion', image: 'Image URL', active: 'Active', featured: 'Featured', bestSeller: 'Best seller',
    productSaved: 'Product saved.', noProducts: 'No products yet.', order: 'Order', customer: 'Customer', receiver: 'Receiver',
    address: 'Delivery address', items: 'Items', subtotal: 'Subtotal', fee: 'Delivery fee', total: 'Total',
    status: 'Order status', payment: 'Payment status', paymentMethod: 'Payment method', date: 'Delivery date', slot: 'Delivery slot',
    updateStatus: 'Update order', markPaid: 'Mark as paid', noOrders: 'No orders yet.', area: 'Area', enabled: 'Active zone',
    feeSaved: 'Delivery fee saved.', loading: 'Loading operations…', unavailable: 'Admin service is unavailable. Check the backend configuration.',
    invalidLogin: 'Email or password is incorrect.', genericError: 'The request could not be completed.', sessionExpired: 'Your session expired. Sign in again.',
    loginIntro: 'Private operations access', productsIntro: 'Catalog and availability', ordersIntro: 'Fulfillment and payment review',
    deliveryIntro: 'Backend-authoritative fees', noImage: 'No image', refresh: 'Refresh', giftMessage: 'Card message', sender: 'Sender', notes: 'Customer note',
    statuses: { pending: 'Pending', confirmed: 'Confirmed', preparing: 'Preparing', out_for_delivery: 'Out for delivery', delivered: 'Delivered', cancelled: 'Cancelled' },
    payments: { awaiting_payment: 'Awaiting review', unpaid: 'Unpaid', paid: 'Paid' },
    methods: { vodafone_cash: 'Vodafone Cash', cash_on_delivery: 'Cash on Delivery' },
  },
  ar: {
    title: 'إدارة تون فلاورز', login: 'دخول المسؤول', email: 'البريد الإلكتروني', password: 'كلمة المرور', signIn: 'تسجيل الدخول',
    products: 'المنتجات', orders: 'الطلبات', delivery: 'رسوم التوصيل', signOut: 'تسجيل الخروج', add: 'إضافة منتج',
    edit: 'تعديل', save: 'حفظ التغييرات', cancel: 'إلغاء', name: 'الاسم بالإنجليزية', nameAr: 'الاسم بالعربية',
    description: 'الوصف بالإنجليزية', descriptionAr: 'الوصف بالعربية', price: 'السعر (ج.م)', stock: 'المخزون',
    category: 'التصنيف', occasion: 'المناسبة', image: 'رابط الصورة', active: 'متاح', featured: 'مميز', bestSeller: 'الأكثر مبيعًا',
    productSaved: 'تم حفظ المنتج.', noProducts: 'لا توجد منتجات بعد.', order: 'الطلب', customer: 'العميل', receiver: 'المستلم',
    address: 'عنوان التوصيل', items: 'المنتجات', subtotal: 'المجموع الفرعي', fee: 'رسوم التوصيل', total: 'الإجمالي',
    status: 'حالة الطلب', payment: 'حالة الدفع', paymentMethod: 'طريقة الدفع', date: 'تاريخ التوصيل', slot: 'فترة التوصيل',
    updateStatus: 'تحديث الطلب', markPaid: 'تأكيد الدفع', noOrders: 'لا توجد طلبات بعد.', area: 'المنطقة', enabled: 'منطقة نشطة',
    feeSaved: 'تم حفظ رسوم التوصيل.', loading: 'جارٍ تحميل لوحة الإدارة…', unavailable: 'خدمة الإدارة غير متاحة. تحقق من إعدادات الخادم.',
    invalidLogin: 'البريد الإلكتروني أو كلمة المرور غير صحيحة.', genericError: 'تعذر إكمال الطلب.', sessionExpired: 'انتهت الجلسة. سجل الدخول مجددًا.',
    loginIntro: 'دخول خاص بالإدارة', productsIntro: 'الكتالوج والتوفر', ordersIntro: 'تجهيز الطلبات ومراجعة الدفع',
    deliveryIntro: 'الرسوم المعتمدة من الخادم', noImage: 'لا توجد صورة', refresh: 'تحديث', giftMessage: 'رسالة البطاقة', sender: 'المرسل', notes: 'ملاحظة العميل',
    statuses: { pending: 'قيد الانتظار', confirmed: 'تم التأكيد', preparing: 'قيد التجهيز', out_for_delivery: 'في الطريق', delivered: 'تم التوصيل', cancelled: 'ملغي' },
    payments: { awaiting_payment: 'بانتظار المراجعة', unpaid: 'غير مدفوع', paid: 'مدفوع' },
    methods: { vodafone_cash: 'فودافون كاش', cash_on_delivery: 'الدفع عند الاستلام' },
  },
} as const

const orderTransitions: Record<string, string[]> = {
  pending: ['confirmed', 'cancelled'],
  confirmed: ['preparing', 'cancelled'],
  preparing: ['out_for_delivery', 'cancelled'],
  out_for_delivery: ['delivered'],
  delivered: [],
  cancelled: [],
}

function newDraft(product?: Product): ProductDraft {
  if (!product) return { ...emptyProduct }
  return {
    id: product.id,
    name: product.name,
    name_ar: product.name_ar || '',
    description: product.description || '',
    description_ar: product.description_ar || '',
    price: String(product.price),
    stock: String(product.stock),
    category: product.category || '',
    occasion: product.occasion || '',
    image_url: product.image_url || '',
    active: product.active,
    featured: product.featured,
    best_seller: product.best_seller,
  }
}

export function AdminPage() {
  const { language } = useLanguage()
  const location = useLocation()
  const text = copy[language]
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [adminEmail, setAdminEmail] = useState('')
  const [authenticated, setAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [tab, setTab] = useState<Tab>('orders')
  const [products, setProducts] = useState<Product[]>([])
  const [orders, setOrders] = useState<OrderResponse[]>([])
  const [zones, setZones] = useState<DeliveryZone[]>([])
  const [selectedOrderId, setSelectedOrderId] = useState<number | null>(null)
  const [draft, setDraft] = useState<ProductDraft | null>(null)
  const [nextOrderStatus, setNextOrderStatus] = useState('')
  const [nextPaymentStatus, setNextPaymentStatus] = useState('')
  const [zoneDrafts, setZoneDrafts] = useState<Record<number, { fee: string; active: boolean; name_en: string; name_ar: string }>>({})
  const selectedOrder = orders.find((order) => order.id === selectedOrderId) || null

  async function loadDashboard() {
    setBusy(true)
    setError('')
    try {
      const [productList, orderList, zoneList] = await Promise.all([adminProducts(), adminOrders(), adminDeliveryZones()])
      setProducts(productList)
      setOrders(orderList)
      setZones(zoneList)
      setZoneDrafts(Object.fromEntries(zoneList.map((zone) => [zone.id, {
        fee: String(zone.fee), active: zone.active, name_en: zone.name_en, name_ar: zone.name_ar || '',
      }])))
      setSelectedOrderId((current) => current && orderList.some((order) => order.id === current) ? current : orderList[0]?.id ?? null)
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        setAuthenticated(false)
        setError(text.sessionExpired)
      } else {
        setError(caught instanceof ApiError && caught.status === 503 ? text.unavailable : text.genericError)
      }
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    let active = true
    adminMe().then((result) => {
      if (!active) return
      setAdminEmail(result.email)
      setAuthenticated(true)
    }).catch(() => {
      if (active) setAuthenticated(false)
    }).finally(() => {
      if (active) setLoading(false)
    })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (authenticated) void loadDashboard()
  }, [authenticated])

  useEffect(() => {
    if (location.pathname.startsWith('/admin/products')) {
      setTab('products')
      return
    }
    if (location.pathname.startsWith('/admin/orders')) {
      setTab('orders')
      return
    }
    if (location.pathname.startsWith('/admin/settings')) {
      setTab('delivery')
    }
  }, [location.pathname])

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const result = await adminLogin({ email: email.trim(), password })
      setAdminEmail(result.email)
      setPassword('')
      setAuthenticated(true)
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 503 ? text.unavailable : text.invalidLogin)
    } finally {
      setBusy(false)
    }
  }

  async function signOut() {
    setBusy(true)
    try { await adminLogout() } catch { /* Clear the local view even when the API is unreachable. */ }
    setAuthenticated(false)
    setAdminEmail('')
    setProducts([])
    setOrders([])
    setZones([])
    setBusy(false)
  }

  async function submitProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!draft) return
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const saved = await saveProduct({
        name: draft.name.trim(),
        name_ar: draft.name_ar.trim() || null,
        description: draft.description.trim() || null,
        description_ar: draft.description_ar.trim() || null,
        price: draft.price,
        stock: Number(draft.stock),
        active: draft.active,
        image_url: draft.image_url.trim() || null,
        category: draft.category.trim() || null,
        occasion: draft.occasion.trim() || null,
        featured: draft.featured,
        best_seller: draft.best_seller,
      }, draft.id)
      setProducts((current) => draft.id
        ? current.map((product) => product.id === saved.id ? saved : product)
        : [...current, saved].sort((left, right) => left.id - right.id))
      setDraft(null)
      setNotice(text.productSaved)
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 401 ? text.sessionExpired : text.genericError)
    } finally {
      setBusy(false)
    }
  }

  async function saveOrderChanges() {
    if (!selectedOrder) return
    setBusy(true)
    setError('')
    try {
      let updated = selectedOrder
      if (nextOrderStatus && nextOrderStatus !== selectedOrder.status) {
        updated = await updateOrderStatus(selectedOrder.id, nextOrderStatus)
        setOrders((current) => current.map((order) => order.id === updated.id ? updated : order))
      }
      if (nextPaymentStatus && nextPaymentStatus !== updated.payment_status) {
        updated = await updatePaymentStatus(updated.id, nextPaymentStatus)
      }
      setOrders((current) => current.map((order) => order.id === updated.id ? updated : order))
      setNextOrderStatus('')
      setNextPaymentStatus('')
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 409 ? text.genericError : text.genericError)
    } finally {
      setBusy(false)
    }
  }

  async function saveZone(zone: DeliveryZone) {
    const value = zoneDrafts[zone.id]
    if (!value) return
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const updated = await updateDeliveryZone(zone.id, {
        name_en: value.name_en,
        name_ar: value.name_ar || null,
        fee: value.fee,
        active: value.active,
        sort_order: zone.sort_order,
      })
      setZones((current) => current.map((item) => item.id === updated.id ? updated : item))
      setNotice(text.feeSaved)
    } catch {
      setError(text.genericError)
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <main className="admin-page" dir={language === 'ar' ? 'rtl' : 'ltr'}><p className="admin-loading">{text.loading}</p></main>

  if (!authenticated) return (
    <main className="admin-page admin-login-page" dir={language === 'ar' ? 'rtl' : 'ltr'}>
      <form className="admin-login" onSubmit={signIn}>
        <a className="admin-brand" href="/">ToneFlowers</a>
        <p className="eyebrow">{text.loginIntro}</p>
        <h1>{text.login}</h1>
        <label>{text.email}<input type="email" autoComplete="username" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
        <label>{text.password}<input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
        {error && <p className="admin-error" role="alert">{error}</p>}
        <button className="button button-primary" type="submit" disabled={busy}>{text.signIn}</button>
      </form>
    </main>
  )

  return (
    <main className="admin-page" dir={language === 'ar' ? 'rtl' : 'ltr'}>
      <header className="admin-header">
        <a className="admin-brand" href="/">ToneFlowers</a>
        <div><span>{adminEmail}</span><button type="button" className="button button-outline" onClick={signOut} disabled={busy}>{text.signOut}</button></div>
      </header>
      <div className="admin-content">
        <div className="admin-title-row"><div><p className="eyebrow">{adminEmail}</p><h1>{text.title}</h1></div></div>
        <nav className="admin-tabs" aria-label="Admin sections">
          {(['orders', 'products', 'delivery'] as Tab[]).map((value) => <button key={value} type="button" className={tab === value ? 'active' : ''} onClick={() => { setTab(value); setError(''); setNotice('') }}>{text[value]}</button>)}
        </nav>
        {error && <p className="admin-error" role="alert">{error}</p>}
        {notice && <p className="admin-notice" role="status">{notice}</p>}

        {tab === 'products' && <section className="admin-section">
          <div className="admin-section-heading"><div><p className="eyebrow">{text.productsIntro}</p><h2>{text.products} <span>{products.length}</span></h2></div><button type="button" className="button button-primary" onClick={() => setDraft(newDraft())}>{text.add}</button></div>
          <div className="admin-product-layout">
            <div className="admin-product-list">
              {products.length === 0 && <p className="admin-empty">{text.noProducts}</p>}
              {products.map((product) => <article key={product.id} className="admin-product-row">
                {product.image_url ? <img src={product.image_url} alt="" /> : <div className="admin-image-empty" aria-label={text.noImage}>✿</div>}
                <div className="admin-product-copy"><strong>{language === 'ar' ? product.name_ar || product.name : product.name}</strong><span>{formatMoney(product.price, language)} · {product.stock} {text.stock}</span><small>{product.active ? text.active : '—'} · {product.category || '—'}</small></div>
                <button className="button button-outline" type="button" onClick={() => setDraft(newDraft(product))}>{text.edit}</button>
              </article>)}
            </div>
            {draft && <form className="admin-editor" onSubmit={submitProduct}>
              <div className="admin-editor-heading"><h3>{draft.id ? text.edit : text.add}</h3><button type="button" className="admin-close" onClick={() => setDraft(null)} aria-label={text.cancel}>×</button></div>
              <div className="admin-form-grid">
                <label>{text.name}<input required maxLength={150} value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} /></label>
                <label>{text.nameAr}<input maxLength={150} value={draft.name_ar} onChange={(event) => setDraft({ ...draft, name_ar: event.target.value })} /></label>
                <label>{text.price}<input required type="number" min="0.01" step="0.01" value={draft.price} onChange={(event) => setDraft({ ...draft, price: event.target.value })} /></label>
                <label>{text.stock}<input required type="number" min="0" step="1" value={draft.stock} onChange={(event) => setDraft({ ...draft, stock: event.target.value })} /></label>
                <label>{text.category}<input maxLength={100} value={draft.category} onChange={(event) => setDraft({ ...draft, category: event.target.value })} /></label>
                <label>{text.occasion}<input maxLength={100} value={draft.occasion} onChange={(event) => setDraft({ ...draft, occasion: event.target.value })} /></label>
                <label className="admin-wide">{text.description}<textarea maxLength={500} rows={3} value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} /></label>
                <label className="admin-wide">{text.descriptionAr}<textarea maxLength={500} rows={3} value={draft.description_ar} onChange={(event) => setDraft({ ...draft, description_ar: event.target.value })} /></label>
                <label className="admin-wide">{text.image}<input type="url" maxLength={500} placeholder="https://" value={draft.image_url} onChange={(event) => setDraft({ ...draft, image_url: event.target.value })} /></label>
              </div>
              <div className="admin-checks">
                {(['active', 'featured', 'best_seller'] as const).map((field) => <label key={field}><input type="checkbox" checked={draft[field]} onChange={(event) => setDraft({ ...draft, [field]: event.target.checked })} />{text[field === 'best_seller' ? 'bestSeller' : field]}</label>)}
              </div>
              <button className="button button-primary" type="submit" disabled={busy}>{text.save}</button>
            </form>}
          </div>
        </section>}

        {tab === 'orders' && <section className="admin-section">
              <div className="admin-section-heading"><div><p className="eyebrow">{text.ordersIntro}</p><h2>{text.orders} <span>{orders.length}</span></h2></div><button className="button button-outline" type="button" onClick={() => void loadDashboard()} disabled={busy}>{text.refresh}</button></div>
          <div className="admin-order-layout">
            <div className="admin-order-list">
              {orders.length === 0 && <p className="admin-empty">{text.noOrders}</p>}
              {orders.map((order) => <button key={order.id} type="button" className={selectedOrderId === order.id ? 'admin-order-row active' : 'admin-order-row'} onClick={() => { setSelectedOrderId(order.id); setNextOrderStatus(''); setNextPaymentStatus('') }}>
                <span><strong>#{order.id}</strong><small>{order.customer_name} · {formatDate(order.delivery_date, language)}</small></span><b>{formatMoney(order.total_price, language)}</b>
              </button>)}
            </div>
            {selectedOrder && <article className="admin-order-detail">
              <div className="admin-section-heading"><div><p className="eyebrow">{text.order} #{selectedOrder.id}</p><h3>{selectedOrder.customer_name}</h3></div><strong>{formatMoney(selectedOrder.total_price, language)}</strong></div>
              <div className="admin-detail-grid">
                <div><small>{text.customer}</small><p>{selectedOrder.customer_name}<br /><a href={`tel:${selectedOrder.customer_phone}`}>{selectedOrder.customer_phone}</a>{selectedOrder.customer_email && <><br />{selectedOrder.customer_email}</>}</p></div>
                <div><small>{text.receiver}</small><p>{selectedOrder.receiver_name}<br /><a href={`tel:${selectedOrder.receiver_phone}`}>{selectedOrder.receiver_phone}</a></p></div>
                <div className="admin-wide"><small>{text.address}</small><p>{selectedOrder.governorate} · {selectedOrder.delivery_area}<br />{selectedOrder.delivery_address}</p></div>
                <div><small>{text.paymentMethod}</small><p>{text.methods[selectedOrder.payment_method]}</p></div>
                <div><small>{text.date} · {text.slot}</small><p>{formatDate(selectedOrder.delivery_date, language)} · {selectedOrder.delivery_slot}</p></div>
                {selectedOrder.sender_name_on_card && <div><small>{text.sender}</small><p>{selectedOrder.sender_name_on_card}</p></div>}
                {selectedOrder.card_message && <div className="admin-wide"><small>{text.giftMessage}</small><p>{selectedOrder.card_message}</p></div>}
                {selectedOrder.customer_note && <div className="admin-wide"><small>{text.notes}</small><p>{selectedOrder.customer_note}</p></div>}
              </div>
              <h4>{text.items}</h4>
              <ul className="admin-order-items">{selectedOrder.items.map((item) => {
                const product = products.find((entry) => entry.id === item.product_id)
                const label = product ? language === 'ar' ? product.name_ar || product.name : product.name : `#${item.product_id}`
                return <li key={item.product_id}><span>{label} × {item.quantity}</span><strong>{formatMoney(item.subtotal, language)}</strong></li>
              })}</ul>
              <div className="admin-totals"><p><span>{text.subtotal}</span><strong>{formatMoney(selectedOrder.subtotal, language)}</strong></p><p><span>{text.fee}</span><strong>{formatMoney(selectedOrder.delivery_fee, language)}</strong></p><p><span>{text.total}</span><strong>{formatMoney(selectedOrder.total_price, language)}</strong></p></div>
              <div className="admin-order-controls">
                <label>{text.status}<select value={nextOrderStatus || selectedOrder.status} onChange={(event) => setNextOrderStatus(event.target.value)}><option value={selectedOrder.status}>{text.statuses[selectedOrder.status as keyof typeof text.statuses] || selectedOrder.status}</option>{(orderTransitions[selectedOrder.status] || []).map((status) => <option key={status} value={status}>{text.statuses[status as keyof typeof text.statuses] || status}</option>)}</select></label>
                <label>{text.payment}<select value={nextPaymentStatus || selectedOrder.payment_status} onChange={(event) => setNextPaymentStatus(event.target.value)}><option value={selectedOrder.payment_status}>{text.payments[selectedOrder.payment_status]}</option>{selectedOrder.payment_status !== 'paid' && <option value="paid">{text.payments.paid}</option>}</select></label>
                <button className="button button-primary" type="button" onClick={() => void saveOrderChanges()} disabled={busy || (!nextOrderStatus && !nextPaymentStatus)}>{text.updateStatus}</button>
              </div>
            </article>}
          </div>
        </section>}

        {tab === 'delivery' && <section className="admin-section">
          <div className="admin-section-heading"><div><p className="eyebrow">{text.deliveryIntro}</p><h2>{text.delivery}</h2></div></div>
          <div className="admin-zone-list">{zones.map((zone) => {
            const value = zoneDrafts[zone.id]
            if (!value) return null
            return <article className="admin-zone-row" key={zone.id}>
              <div className="admin-zone-name"><strong>{zone.governorate === 'Cairo' ? 'Cairo · القاهرة' : 'Giza · الجيزة'}</strong><span>{text.enabled}</span></div>
              <label>{text.name}<input value={value.name_en} onChange={(event) => setZoneDrafts({ ...zoneDrafts, [zone.id]: { ...value, name_en: event.target.value } })} /></label>
              <label>{text.nameAr}<input value={value.name_ar} onChange={(event) => setZoneDrafts({ ...zoneDrafts, [zone.id]: { ...value, name_ar: event.target.value } })} /></label>
              <label>{text.fee}<input type="number" min="0" step="0.01" value={value.fee} onChange={(event) => setZoneDrafts({ ...zoneDrafts, [zone.id]: { ...value, fee: event.target.value } })} /></label>
              <label className="admin-zone-active"><input type="checkbox" checked={value.active} onChange={(event) => setZoneDrafts({ ...zoneDrafts, [zone.id]: { ...value, active: event.target.checked } })} />{text.active}</label>
              <button className="button button-primary" type="button" disabled={busy} onClick={() => void saveZone(zone)}>{text.save}</button>
            </article>
          })}</div>
        </section>}
      </div>
    </main>
  )
}