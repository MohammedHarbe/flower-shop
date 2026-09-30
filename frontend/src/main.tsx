import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { App } from './App'
import { CartProvider } from './context/CartContext'
import { LanguageProvider } from './context/LanguageContext'
import './styles.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <LanguageProvider>
        <CartProvider>
          <App />
        </CartProvider>
      </LanguageProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
