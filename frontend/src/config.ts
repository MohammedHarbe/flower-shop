export const config = {
  apiUrl: (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, ''),
  siteUrl: normalizeSiteUrl(import.meta.env.VITE_SITE_URL || ''),
  whatsappUrl: import.meta.env.VITE_WHATSAPP_URL || '',
  phone: import.meta.env.VITE_PHONE || '',
  email: import.meta.env.VITE_EMAIL || '',
  facebookUrl: import.meta.env.VITE_FACEBOOK_URL || '',
  instagramUrl: import.meta.env.VITE_INSTAGRAM_URL || '',
} as const

function normalizeSiteUrl(value: string): string {
  try {
    const url = new URL(value)
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password
      || url.pathname !== '/' || url.search || url.hash) return ''
    return url.origin
  } catch {
    return ''
  }
}
