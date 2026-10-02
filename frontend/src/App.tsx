import { Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { HomePage } from './pages/HomePage'
import { ProductsPage } from './pages/ProductsPage'
import { ProductPage } from './pages/ProductPage'
import { CartPage } from './pages/CartPage'
import { CheckoutPage } from './pages/CheckoutPage'
import { OrderSuccessPage } from './pages/OrderSuccessPage'
import { AboutPage, ContactPage, NotFoundPage } from './pages/InfoPages'
import { AdminPage } from './pages/AdminPage'

export function App() {
  return <Layout><Routes>
    <Route path="/" element={<HomePage />} />
    <Route path="/products" element={<ProductsPage />} />
    <Route path="/products/:id" element={<ProductPage />} />
    <Route path="/cart" element={<CartPage />} />
    <Route path="/checkout" element={<CheckoutPage />} />
    <Route path="/order-success/:id" element={<OrderSuccessPage />} />
    <Route path="/about" element={<AboutPage />} />
    <Route path="/contact" element={<ContactPage />} />
    <Route path="/admin/login" element={<AdminPage />} />
    <Route path="/admin" element={<AdminPage />} />
    <Route path="/admin/products" element={<AdminPage />} />
    <Route path="/admin/products/new" element={<AdminPage />} />
    <Route path="/admin/products/:id/edit" element={<AdminPage />} />
    <Route path="/admin/orders" element={<AdminPage />} />
    <Route path="/admin/orders/:id" element={<AdminPage />} />
    <Route path="/admin/settings" element={<AdminPage />} />
    <Route path="*" element={<NotFoundPage />} />
  </Routes></Layout>
}
