import { Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { HomePage } from './pages/HomePage'
import { ProductsPage } from './pages/ProductsPage'
import { ProductPage } from './pages/ProductPage'
import { CartPage } from './pages/CartPage'
import { CheckoutPage } from './pages/CheckoutPage'
import { OrderSuccessPage } from './pages/OrderSuccessPage'
import { AboutPage, ContactPage, NotFoundPage } from './pages/InfoPages'

export function App() {
  return <Layout><Routes><Route path="/" element={<HomePage />} /><Route path="/products" element={<ProductsPage />} /><Route path="/products/:id" element={<ProductPage />} /><Route path="/cart" element={<CartPage />} /><Route path="/checkout" element={<CheckoutPage />} /><Route path="/order-success/:id" element={<OrderSuccessPage />} /><Route path="/about" element={<AboutPage />} /><Route path="/contact" element={<ContactPage />} /><Route path="*" element={<NotFoundPage />} /></Routes></Layout>
}
