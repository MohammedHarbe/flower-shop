export const config = {
  apiUrl: (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, ''),
  whatsappUrl: import.meta.env.VITE_WHATSAPP_URL || '',
  phone: import.meta.env.VITE_PHONE || '',
  email: import.meta.env.VITE_EMAIL || '',
  facebookUrl:
    import.meta.env.VITE_FACEBOOK_URL ||
    'https://www.facebook.com/p/Tone-Flowers-61551242462469/',
  instagramUrl: import.meta.env.VITE_INSTAGRAM_URL || '',
} as const
