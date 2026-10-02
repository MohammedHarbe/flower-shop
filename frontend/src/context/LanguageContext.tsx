import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { PropsWithChildren } from 'react'
import { ar } from '../i18n/ar'
import { en } from '../i18n/en'
import type { Language } from '../types'

type LanguageContextValue = {
  language: Language
  setLanguage: (language: Language) => void
  toggleLanguage: () => void
  t: typeof en
}

const LanguageContext = createContext<LanguageContextValue | null>(null)

function initialLanguage(): Language {
  try {
    return localStorage.getItem('toneflowers-language') === 'en' ? 'en' : 'ar'
  } catch {
    return 'ar'
  }
}

export function LanguageProvider({ children }: PropsWithChildren) {
  const [language, setLanguage] = useState<Language>(initialLanguage)

  useEffect(() => {
    document.documentElement.lang = language
    document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr'
    try { localStorage.setItem('toneflowers-language', language) } catch { /* Keep the in-memory choice. */ }
  }, [language])

  const value = useMemo(
    () => ({
      language,
      setLanguage,
      toggleLanguage: () => setLanguage((current) => (current === 'ar' ? 'en' : 'ar')),
      t: language === 'ar' ? ar : en,
    }),
    [language],
  )

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage(): LanguageContextValue {
  const context = useContext(LanguageContext)
  if (!context) throw new Error('useLanguage must be used inside LanguageProvider')
  return context
}
