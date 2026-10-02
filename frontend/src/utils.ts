import type { Language, Product } from './types'
import { moneyAmount } from './types'
import { ar } from './i18n/ar'
import { en } from './i18n/en'

export function catalogSlug(value: string): string {
  return value.trim().toLowerCase().replace(/&/g, 'and').replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-|-$/g, '')
}

export function categoryLabel(value: string, language: Language): string {
  const labels: Record<string, string> = language === 'ar' ? ar.catalog.categories : en.catalog.categories
  return labels[catalogSlug(value)] || value
}

export function occasionLabel(value: string, language: Language): string {
  const labels: Record<string, string> = language === 'ar' ? ar.catalog.occasions : en.catalog.occasions
  return labels[catalogSlug(value)] || value
}

export function productName(product: Product, language: Language): string {
  return language === 'ar' && product.name_ar?.trim() ? product.name_ar : product.name
}

export function productDescription(product: Product, language: Language): string {
  return language === 'ar' && product.description_ar?.trim()
    ? product.description_ar
    : product.description || ''
}

export function formatMoney(value: string | number, language: Language): string {
  return new Intl.NumberFormat(language === 'ar' ? 'ar-EG' : 'en-EG', {
    style: 'currency',
    currency: 'EGP',
    maximumFractionDigits: 2,
  }).format(moneyAmount(value))
}

export function formatDate(value: string, language: Language): string {
  const date = new Date(`${value}T12:00:00`)
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat(language === 'ar' ? 'ar-EG' : 'en-EG', { dateStyle: 'long' }).format(date)
}

export function todayLocal(): string {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Africa/Cairo', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date())
  const value = (part: string) => parts.find((item) => item.type === part)?.value || ''
  return `${value('year')}-${value('month')}-${value('day')}`
}

export function normalizeDigits(value: string): string {
  return value.replace(/[٠-٩۰-۹]/g, (digit) => {
    const code = digit.charCodeAt(0)
    return String(code >= 0x06f0 ? code - 0x06f0 : code - 0x0660)
  })
}

export function normalizeEgyptianPhone(value: string): string | null {
  let compact = normalizeDigits(value.trim()).replace(/[\s().-]/g, '')
  if (compact.startsWith('0020')) compact = `+20${compact.slice(4)}`
  else if (compact.startsWith('20')) compact = `+${compact}`
  else if (compact.startsWith('0')) compact = `+20${compact.slice(1)}`
  return /^\+201[0125][0-9]{8}$/.test(compact) ? compact : null
}

export function whatsappLink(number: string, fallbackUrl: string, message: string): string {
  let digits = normalizeDigits(number).replace(/\D/g, '')
  if (digits.startsWith('00')) digits = digits.slice(2)
  if (digits.startsWith('0')) digits = `20${digits.slice(1)}`
  else if (digits && !digits.startsWith('20')) digits = `20${digits}`
  if (digits) return `https://wa.me/${digits}?text=${encodeURIComponent(message)}`
  if (!fallbackUrl) return ''
  try {
    const url = new URL(fallbackUrl)
    url.searchParams.set('text', message)
    return url.toString()
  } catch {
    return fallbackUrl
  }
}
